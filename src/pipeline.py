"""
pipeline.py — CGPSC Single-Year Pipeline Orchestrator

Usage:
    python src/pipeline.py <year>
    python src/pipeline.py 2024
    python src/pipeline.py 2024 --skip-ocr
    python src/pipeline.py 2024 --from analyzer
    python src/pipeline.py 2024 --steps ocr parser validator

Stages (in order):
    ocr -> parser -> validator -> analyzer -> analyzer_validator -> statistics -> ingest
"""

from asyncio import log, runners
import sys
import os
import argparse
import time
import traceback
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

from config import PipelineConfig  # noqa: E402


# ── Stage registry ───────────────────────────────────────────────────────────

STAGE_ORDER = [
    "ocr",
    "parser",
    "validator",
    "analyzer",
    "analyzer_validator",
    "statistics",
    "ingest",
]


def _import_stages():
    """Lazily import all stage runners to catch missing-module errors early."""
    runners = {}

    try:
        from main import run_ocr_pipeline
        runners["ocr"] = run_ocr_pipeline
    except ImportError as e:
        runners["ocr"] = _missing("ocr", e)

    try:
        from parser import run_parser
        runners["parser"] = run_parser
    except ImportError as e:
        runners["parser"] = _missing("parser", e)

    try:
        from validator import run_validator
        runners["validator"] = run_validator
    except ImportError as e:
        runners["validator"] = _missing("validator", e)

    try:
        from analyzer import run_analyzer
        runners["analyzer"] = run_analyzer
    except ImportError as e:
        runners["analyzer"] = _missing("analyzer", e)

    try:
        from validate_analyzer import run_analyzer_validator
        runners["analyzer_validator"] = run_analyzer_validator
    except ImportError as e:
        runners["analyzer_validator"] = _missing("analyzer_validator", e)

    try:
        from statistics import run_statistics
        runners["statistics"] = run_statistics
    except ImportError as e:
        runners["statistics"] = _missing("statistics", e)

    try:
        from ingest import run_ingest
        runners["ingest"] = run_ingest
    except ImportError as e:
        runners["ingest"] = _missing("ingest", e)

    return runners


def _missing(stage_name, exc):
    """Return a stub that raises on call, so pipeline fails clearly."""
    def _stub(*args, **kwargs):
        raise ImportError(
            f"Stage '{stage_name}' could not be imported: {exc}\n"
            "Fix the import or skip this stage with --from / --steps."
        )
    return _stub


# ── Stage callers ────────────────────────────────────────────────────────────

def call_stage(stage, runner, cfg):
    """
    Map each stage name to its runner's expected signature
    using PipelineConfig paths.
    """
    if stage == "ocr":

        if cfg.ocr_output_path.exists():
            return True

        runner(
        cfg.pdf_path,
        cfg.ocr_output_path
    )

    elif stage == "parser":
        runner(cfg.ocr_output_path, cfg.questions_json_path, cfg.year)

    elif stage == "validator":
        runner(cfg.questions_json_path, cfg.validator_output_path)

    elif stage == "analyzer":
        runner(
        cfg.questions_json_path,
        cfg.analyzed_json_path,
        cfg.taxonomy_path
    )

    elif stage == "analyzer_validator":
        runner(cfg.analyzed_json_path)

    elif stage == "statistics":
        runner(cfg.analyzed_json_path, cfg.database_stats_path)

    elif stage == "ingest":
        runner(cfg.analyzed_json_path, cfg.year)

    else:
        raise ValueError(f"Unknown stage: {stage}")


# ── Pretty logging ────────────────────────────────────────────────────────────

class Logger:
    def __init__(self, year, log_path=None):
        self.year = year
        self.log_path = log_path
        self._lines = []

    def _emit(self, line):
        print(line, flush=True)
        self._lines.append(line)
        if self.log_path:
            with open(self.log_path, "a") as f:
                f.write(line + "\n")

    def header(self, msg):
        self._emit(f"\n{'='*60}")
        self._emit(f"  {msg}")
        self._emit(f"{'='*60}")

    def info(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self._emit(f"[{ts}] {msg}")

    def success(self, stage, elapsed):
        self._emit(f"  ok  {stage:<22} {elapsed:.1f}s")

    def fail(self, stage, elapsed, exc):
        self._emit(f"  fail  {stage:<22} {elapsed:.1f}s  — {exc}")

    def skip(self, stage, reason=""):
        self._emit(f"  ─  {stage:<22} skipped  {reason}")

    def summary(self, results):
        self._emit(f"\n{'─'*60}")
        self._emit("  PIPELINE SUMMARY")
        self._emit(f"{'─'*60}")
        ok = sum(1 for r in results.values() if r["status"] == "ok")
        fail = sum(1 for r in results.values() if r["status"] == "error")
        skip = sum(1 for r in results.values() if r["status"] == "skipped")
        total_time = sum(r.get("elapsed", 0) for r in results.values())
        self._emit(f"  Passed : {ok}")
        self._emit(f"  Failed : {fail}")
        self._emit(f"  Skipped: {skip}")
        self._emit(f"  Total  : {total_time:.1f}s")
        self._emit(f"{'─'*60}\n")


# ── Core runner ───────────────────────────────────────────────────────────────

def run_pipeline(year: int, stages_to_run=None, stop_on_error=True, log_path=None):
    """
    Run the CGPSC pipeline for a single year.

    Args:
        year:           Exam year (e.g. 2024).
        stages_to_run:  List of stage names to execute, or None for all.
        stop_on_error:  If True, abort pipeline on first failure.
        log_path:       Optional path to append log output.

    Returns:
        dict  results keyed by stage name, each with 'status', 'elapsed', 'error'.
    """
    cfg = PipelineConfig(year)
    cfg.create_directories()  # create output dirs if missing

    log = Logger(year, log_path)
    log.header(f"CGPSC Pipeline — Year {year}")
    log.info(f"PDF     : {cfg.pdf_path}")
    log.info(f"Output  : {cfg.year_data_dir}")

    # Validate PDF exists before starting
    if not Path(cfg.pdf_path).exists():
        log.info(f"ERROR: PDF not found at {cfg.pdf_path}")
        return {"ocr": {"status": "error", "elapsed": 0, "error": "PDF not found"}}

    runners = _import_stages()

    if stages_to_run is None:
        stages_to_run = STAGE_ORDER
    else:
        # Preserve canonical order even if caller passed them out of order
        stages_to_run = [s for s in STAGE_ORDER if s in stages_to_run]

    results = {}
    log.info(f"Stages  : {' -> '.join(stages_to_run)}\n")

    for stage in STAGE_ORDER:
        if stage not in stages_to_run:
            log.skip(stage, "(not selected)")
            results[stage] = {"status": "skipped", "elapsed": 0}
            continue

        log.info(f"Starting: {stage}")
        t0 = time.time()
        try:
            call_stage(stage, runners[stage], cfg)
            elapsed = time.time() - t0
            log.success(stage, elapsed)
            results[stage] = {"status": "ok", "elapsed": elapsed}
        except Exception as exc:
            elapsed = time.time() - t0
            log.fail(stage, elapsed, exc)
            results[stage] = {"status": "error", "elapsed": elapsed, "error": str(exc)}
            if stop_on_error:
                log.info("Pipeline aborted (use --no-stop to continue on errors).")
                # Fill remaining stages as skipped
                remaining = STAGE_ORDER[STAGE_ORDER.index(stage) + 1:]
                for s in remaining:
                    if s not in results:
                        results[s] = {"status": "skipped", "elapsed": 0}
                break

    log.summary(results)
    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(
        description="Run the CGPSC pipeline for a single year.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/pipeline.py 2024
  python src/pipeline.py 2024 --skip-ocr
  python src/pipeline.py 2024 --from analyzer
  python src/pipeline.py 2024 --steps ocr parser validator
  python src/pipeline.py 2024 --no-stop
        """,
    )
    p.add_argument("year", type=int, help="Exam year to process (e.g. 2024)")

    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Skip OCR (use existing ocr_output.txt)",
    )
    group.add_argument(
        "--from",
        dest="from_stage",
        choices=STAGE_ORDER,
        metavar="STAGE",
        help="Start from this stage (all earlier stages skipped)",
    )
    group.add_argument(
        "--steps",
        nargs="+",
        choices=STAGE_ORDER,
        metavar="STAGE",
        help="Run only these stages (space-separated)",
    )

    p.add_argument(
        "--no-stop",
        action="store_true",
        help="Continue pipeline even if a stage fails",
    )
    p.add_argument(
        "--log",
        metavar="FILE",
        help="Append pipeline log to this file",
    )
    return p.parse_args()


def _resolve_stages(args):
    if args.steps:
        return args.steps
    if args.skip_ocr:
        return [s for s in STAGE_ORDER if s != "ocr"]
    if args.from_stage:
        idx = STAGE_ORDER.index(args.from_stage)
        return STAGE_ORDER[idx:]
    return None  # all stages


def main():
    args = _parse_args()
    stages = _resolve_stages(args)

    results = run_pipeline(
        year=args.year,
        stages_to_run=stages,
        stop_on_error=not args.no_stop,
        log_path=args.log,
    )

    # Exit with non-zero if any stage failed
    if any(r["status"] == "error" for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
