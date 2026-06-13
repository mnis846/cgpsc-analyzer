"""
process_all.py — CGPSC Batch Multi-Year Processor

Usage:
    python src/process_all.py                     # process all unprocessed years
    python src/process_all.py --force             # reprocess all years
    python src/process_all.py --years 2018 2019   # specific years only
    python src/process_all.py --from-year 2010    # 2010 onwards
    python src/process_all.py --dry-run           # show what would run
    python src/process_all.py --skip-ocr          # pass --skip-ocr to each year

Scans data/pdfs/ for files named YYYY.pdf and processes each year
through the full pipeline. Skips already-processed years unless --force.
"""

import sys
import os
import argparse
import time
import json
from pathlib import Path
from datetime import datetime
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ── Project root on sys.path ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import PipelineConfig          # noqa: E402
from pipeline import run_pipeline, STAGE_ORDER  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def discover_years(pdfs_dir: Path) -> list[int]:
    """Return sorted list of years found in data/pdfs/ as YYYY.pdf files."""
    years = []
    for f in sorted(pdfs_dir.glob("*.pdf")):
        stem = f.stem
        if stem.isdigit() and len(stem) == 4:
            year = int(stem)
            if 2000 <= year <= 2100:
                years.append(year)
    return sorted(years)


def is_processed(year: int) -> bool:
    """
    A year is considered already processed if its analyzed JSON exists
    AND the database ingest marker exists.
    Adjust this logic to match your actual completion criteria.
    """
    cfg = PipelineConfig(year)
    analyzed_exists = Path(cfg.analyzed_json_path).exists()
    stats_exists = cfg.database_stats_path.exists()
    return analyzed_exists and stats_exists


def load_batch_log(log_path: Path) -> dict:
    """Load persistent batch processing log (year → result summary)."""
    if log_path.exists():
        try:
            with open(log_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_batch_log(log_path: Path, batch_log: dict):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as f:
        json.dump(batch_log, f, indent=2)


# ── Display helpers ───────────────────────────────────────────────────────────

SEP = "─" * 62

def print_header(total, to_process, to_skip):
    print(f"\n{'='*62}")
    print(f"  CGPSC Batch Processor")
    print(f"{'='*62}")
    print(f"  PDFs found      : {total}")
    print(f"  To process      : {to_process}")
    print(f"  Already done    : {to_skip}")
    print(f"  Started at      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*62}\n")


def print_year_header(year, idx, total):
    print(f"\n{SEP}")
    print(f"  [{idx}/{total}]  Processing year: {year}")
    print(SEP)


def print_final_summary(batch_results, wall_time):
    ok_years    = [y for y, r in batch_results.items() if r["status"] == "ok"]
    fail_years  = [y for y, r in batch_results.items() if r["status"] == "error"]
    skip_years  = [y for y, r in batch_results.items() if r["status"] == "skipped"]

    print(f"\n{'='*62}")
    print("  BATCH SUMMARY")
    print(f"{'='*62}")
    print(f"  Succeeded : {len(ok_years)}")
    if ok_years:
        print(f"              {ok_years}")
    print(f"  Failed    : {len(fail_years)}")
    if fail_years:
        print(f"              {fail_years}")
    print(f"  Skipped   : {len(skip_years)}")
    if skip_years:
        print(f"              {skip_years}")
    print(f"  Wall time : {wall_time:.1f}s  ({wall_time/60:.1f} min)")
    print(f"{'='*62}\n")


# ── Core batch runner ─────────────────────────────────────────────────────────

def run_all(
    years: list[int],
    force: bool = False,
    dry_run: bool = False,
    pipeline_kwargs: dict = None,
    batch_log_path: Path = None,
) -> dict:
    """
    Process a list of years through the full pipeline.

    Args:
        years:            Years to attempt (already filtered to those with PDFs).
        force:            Reprocess even if already marked complete.
        dry_run:          Print plan without executing.
        pipeline_kwargs:  Extra kwargs forwarded to run_pipeline() per year.
        batch_log_path:   Path for persistent batch log JSON.

    Returns:
        dict  { year: { status, elapsed, stage_results } }
    """
    if pipeline_kwargs is None:
        pipeline_kwargs = {}

    if batch_log_path is None:
        batch_log_path = PROJECT_ROOT / "data" / "batch_log.json"

    batch_log = load_batch_log(batch_log_path)

    # Decide which years to actually run
    to_run = []
    to_skip_already = []
    for y in years:
        if not force and is_processed(y):
            to_skip_already.append(y)
        else:
            to_run.append(y)

    print_header(len(years), len(to_run), len(to_skip_already))

    batch_results = {}
    for y in to_skip_already:
        batch_results[y] = {"status": "skipped", "elapsed": 0, "reason": "already processed"}

    if dry_run:
        print("DRY RUN — no processing will occur.\n")
        print(f"Would skip  : {to_skip_already}")
        print(f"Would process: {to_run}")
        return batch_results

    total = len(to_run)
    wall_start = time.time()

    for idx, year in enumerate(to_run, start=1):
        print_year_header(year, idx, total)
        t0 = time.time()

        # Build a per-year log file path
        cfg = PipelineConfig(year)
        year_log = Path(cfg.year_data_dir) / "pipeline.log"

        try:
            stage_results = run_pipeline(
                year=year,
                log_path=str(year_log),
                **pipeline_kwargs,
            )
            elapsed = time.time() - t0
            any_error = any(r["status"] == "error" for r in stage_results.values())
            status = "error" if any_error else "ok"

        except Exception as exc:
            elapsed = time.time() - t0
            status = "error"
            stage_results = {"__exception__": {"status": "error", "error": str(exc), "elapsed": elapsed}}
            print(f"\n  UNHANDLED EXCEPTION for year {year}:\n  {exc}\n")

        batch_results[year] = {
            "status": status,
            "elapsed": round(elapsed, 1),
            "stage_results": stage_results,
            "processed_at": datetime.now().isoformat(),
        }

        # Persist after each year so partial runs are recoverable
        batch_log[str(year)] = batch_results[year]
        save_batch_log(batch_log_path, batch_log)

    wall_time = time.time() - wall_start
    print_final_summary(batch_results, wall_time)
    return batch_results


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(
        description="Batch-process multiple CGPSC exam years.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/process_all.py
  python src/process_all.py --force
  python src/process_all.py --years 2018 2019 2020
  python src/process_all.py --from-year 2015
  python src/process_all.py --to-year 2020
  python src/process_all.py --from-year 2010 --to-year 2020
  python src/process_all.py --dry-run
  python src/process_all.py --skip-ocr
  python src/process_all.py --from-stage analyzer
  python src/process_all.py --no-stop
        """,
    )

    # Year selection
    year_group = p.add_argument_group("year selection")
    year_group.add_argument(
        "--years",
        nargs="+",
        type=int,
        metavar="YEAR",
        help="Process only these specific years",
    )
    year_group.add_argument(
        "--from-year",
        type=int,
        metavar="YEAR",
        help="Process years >= YEAR",
    )
    year_group.add_argument(
        "--to-year",
        type=int,
        metavar="YEAR",
        help="Process years <= YEAR",
    )

    # Behaviour flags
    p.add_argument("--force", action="store_true", help="Reprocess already-completed years")
    p.add_argument("--dry-run", action="store_true", help="Show what would be processed without running")
    p.add_argument("--no-stop", action="store_true", help="Don't abort a year's pipeline on stage error")

    # Stage control (forwarded to pipeline.py)
    stage_group = p.add_mutually_exclusive_group()
    stage_group.add_argument("--skip-ocr", action="store_true", help="Skip OCR stage for every year")
    stage_group.add_argument(
        "--from-stage",
        dest="from_stage",
        choices=STAGE_ORDER,
        metavar="STAGE",
        help="Start each year from this stage",
    )
    stage_group.add_argument(
        "--steps",
        nargs="+",
        choices=STAGE_ORDER,
        metavar="STAGE",
        help="Run only these stages for every year",
    )

    p.add_argument(
        "--pdfs-dir",
        default=None,
        metavar="DIR",
        help="Override default data/pdfs/ directory",
    )
    p.add_argument(
        "--batch-log",
        default=None,
        metavar="FILE",
        help="Override default data/batch_log.json path",
    )

    return p.parse_args()


def _resolve_pipeline_kwargs(args) -> dict:
    """Translate process_all CLI flags into run_pipeline kwargs."""
    kwargs = {"stop_on_error": not args.no_stop}

    if args.skip_ocr:
        kwargs["stages_to_run"] = [s for s in STAGE_ORDER if s != "ocr"]
    elif args.from_stage:
        idx = STAGE_ORDER.index(args.from_stage)
        kwargs["stages_to_run"] = STAGE_ORDER[idx:]
    elif args.steps:
        kwargs["stages_to_run"] = args.steps

    return kwargs


def main():
    args = _parse_args()

    # ── Discover PDFs ─────────────────────────────────────────────────────────
    pdfs_dir = Path(args.pdfs_dir) if args.pdfs_dir else PROJECT_ROOT / "data" / "pdfs"
    if not pdfs_dir.exists():
        print(f"ERROR: PDFs directory not found: {pdfs_dir}")
        sys.exit(1)

    all_years = discover_years(pdfs_dir)
    if not all_years:
        print(f"No YYYY.pdf files found in {pdfs_dir}")
        sys.exit(1)

    # ── Apply year filters ────────────────────────────────────────────────────
    if args.years:
        years = [y for y in args.years if y in all_years]
        missing = [y for y in args.years if y not in all_years]
        if missing:
            print(f"WARNING: No PDFs found for years: {missing}")
    else:
        years = all_years
        if args.from_year:
            years = [y for y in years if y >= args.from_year]
        if args.to_year:
            years = [y for y in years if y <= args.to_year]

    if not years:
        print("No years to process after applying filters.")
        sys.exit(0)

    pipeline_kwargs = _resolve_pipeline_kwargs(args)
    batch_log_path = Path(args.batch_log) if args.batch_log else None

    results = run_all(
        years=years,
        force=args.force,
        dry_run=args.dry_run,
        pipeline_kwargs=pipeline_kwargs,
        batch_log_path=batch_log_path,
    )

    # Exit non-zero if any year failed
    if any(r["status"] == "error" for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
