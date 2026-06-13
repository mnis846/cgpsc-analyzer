"""
Paper ingestion workflow for CGPSC Intelligence System.

Orchestrates the pipeline:
  1. Analyzer → validated analyzed JSON
  2. Database ingestion → store in database/questions/
  3. Statistics generation → database/stats/
  4. Metadata indexing → database/index.json

Designed for repeated use across multiple exam years (2025, 2024, 2023, etc.)
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple


logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


class PaperIngestionWorkflow:
    """
    Orchestrates the paper ingestion pipeline.
    
    Workflow:
      1. Validate analyzed JSON file
      2. Ingest into database
      3. Generate statistics
      4. Report results
    """
    
    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize the workflow.
        
        Args:
            repo_root: Repository root path (auto-detected if not provided)
        """
        self.repo_root = repo_root or Path(__file__).resolve().parents[1]
        
        # Lazy imports to allow independent module usage
        self.database = None
        self.statistics = None
    
    def _import_modules(self):
        """Import database and statistics modules on first use."""
        if self.database is None:
            sys.path.insert(0, str(self.repo_root / "src"))
            try:
                from database import PaperDatabase
                from statistics import StatisticsGenerator
                self.database = PaperDatabase
                self.statistics = StatisticsGenerator
            except ImportError as e:
                logger.error(f"Failed to import modules: {e}")
                raise
    
    def validate_input_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        Validate that the input file is a valid analyzed record.
        
        Args:
            file_path: Path to analyzed JSON file
            
        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        logger.info(f"Validating input file: {file_path}")
        
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        
        if not file_path.suffix == '.json':
            return False, f"File must be JSON: {file_path}"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        
        # Check for required fields
        required_fields = ['schema_version', 'year', 'exam', 'questions']
        missing = [f for f in required_fields if f not in data]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        
        # Validate schema version
        if data.get('schema_version') != 'analyzer-record-v1':
            return False, (
                f"Invalid schema version: {data.get('schema_version')}. "
                "Expected: analyzer-record-v1"
            )
        
        # Validate question count
        question_count = len(data.get('questions', []))
        if question_count == 0:
            return False, "File contains no questions"
        
        logger.info(f"✓ Validation passed ({question_count} questions)")
        return True, f"Valid analyzer record for {data['year']} ({question_count} questions)"
    
    def ingest_paper(
        self,
        analyzed_file: Path,
        year: int,
        overwrite: bool = False
    ) -> Tuple[bool, str]:
        """
        Ingest a paper into the database.
        
        Args:
            analyzed_file: Path to analyzed JSON file
            year: Exam year
            overwrite: Whether to overwrite existing paper
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        self._import_modules()
        db = self.database()
        
        logger.info(f"Ingesting paper for year {year}")
        
        try:
            success, message = db.ingest_paper(analyzed_file, year, overwrite=overwrite)
            if success:
                logger.info(f"✓ Paper ingestion successful: {message}")
            else:
                logger.warning(f"Paper ingestion failed: {message}")
            return success, message
        except Exception as e:
            msg = f"Error during ingestion: {e}"
            logger.error(msg)
            return False, msg
    
    def generate_statistics(
        self,
        year: int,
        output_file: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Path]]:
        """
        Generate statistics for a paper in the database.
        
        Args:
            year: Exam year
            output_file: Custom output filename (default: cgpsc_{year}_stats.json)
            
        Returns:
            Tuple of (success: bool, message: str, output_path or None)
        """
        self._import_modules()
        db = self.database()
        stats_gen = self.statistics
        
        logger.info(f"Generating statistics for year {year}")
        
        try:
            # Load paper from database
            paper = db.load_paper(year)
            
            # Get database statistics output directory
            stats_dir = db.db_root / "stats"
            stats_dir.mkdir(parents=True, exist_ok=True)
            
            # Create temporary analyzer-style JSON for statistics generator
            temp_file = stats_dir / f"cgpsc_{year}_analyzed.json"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(paper, f, indent=2, ensure_ascii=False)
            
            # Generate statistics
            generator = stats_gen(
                input_file=str(temp_file),
                output_dir=str(stats_dir)
            )
            generator.load_questions()
            generator.generate_statistics()
            
            # Validate
            validation_errors = generator.validate_counts()
            if validation_errors:
                msg = f"Statistics validation failed: {validation_errors}"
                logger.error(msg)
                return False, msg, None
            
            # Save
            filename = output_file or f"cgpsc_{year}_stats.json"
            output_path = generator.save_report(filename)
            
            msg = f"Statistics generated: {output_path}"
            logger.info(f"✓ {msg}")
            return True, msg, output_path
            
        except FileNotFoundError as e:
            msg = f"Paper for {year} not found in database: {e}"
            logger.error(msg)
            return False, msg, None
        except Exception as e:
            msg = f"Error generating statistics: {e}"
            logger.error(msg)
            return False, msg, None
    
    def run_full_workflow(
        self,
        analyzed_file: Path,
        year: int,
        skip_stats: bool = False,
        overwrite: bool = False
    ) -> bool:
        """
        Run the complete ingestion workflow.
        
        Args:
            analyzed_file: Path to analyzed JSON file
            year: Exam year
            skip_stats: Skip statistics generation
            overwrite: Overwrite existing paper
            
        Returns:
            True if workflow completed successfully, False otherwise
        """
        print("\n" + "="*70)
        print("CGPSC PAPER INGESTION WORKFLOW")
        print("="*70 + "\n")
        
        # Step 1: Validate
        print("Step 1: Validating input file...")
        is_valid, validation_msg = self.validate_input_file(analyzed_file)
        print(f"  {validation_msg}\n")
        
        if not is_valid:
            print("✗ Validation failed. Workflow aborted.\n")
            print("="*70 + "\n")
            return False
        
        # Step 2: Ingest
        print("Step 2: Ingesting paper into database...")
        success, ingest_msg = self.ingest_paper(analyzed_file, year, overwrite=overwrite)
        print(f"  {ingest_msg}\n")
        
        if not success:
            print("✗ Ingestion failed. Workflow aborted.\n")
            print("="*70 + "\n")
            return False
        
        # Step 3: Generate Statistics (optional)
        if not skip_stats:
            print("Step 3: Generating statistics...")
            success, stats_msg, stats_path = self.generate_statistics(year)
            print(f"  {stats_msg}\n")
            
            if not success:
                print("⚠ Statistics generation failed (non-blocking)\n")
        
        # Step 4: Show database status
        print("Step 4: Database status...")
        self._import_modules()
        db = self.database()
        db.print_database_status()
        
        print("="*70)
        print("✓ WORKFLOW COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")
        return True
    
def run_ingest(
    analyzed_file,
    year,
    skip_stats=False,
    overwrite=False
):
    workflow = PaperIngestionWorkflow()

    return workflow.run_full_workflow(
        analyzed_file=Path(analyzed_file),
        year=year,
        skip_stats=skip_stats,
        overwrite=overwrite
    )

def main():
    """Command-line interface for paper ingestion."""
    parser = argparse.ArgumentParser(
        description='Ingest analyzed CGPSC papers into the database'
    )
    parser.add_argument(
        'analyzed_file',
        type=Path,
        help='Path to analyzed JSON file (from analyzer)'
    )
    parser.add_argument(
        'year',
        type=int,
        help='Exam year (e.g., 2025, 2024)'
    )
    parser.add_argument(
        '--skip-stats',
        action='store_true',
        help='Skip statistics generation'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing paper in database'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    setup_logging(verbose=args.verbose)
    
    workflow = PaperIngestionWorkflow()
    success = workflow.run_full_workflow(
        analyzed_file=args.analyzed_file,
        year=args.year,
        skip_stats=args.skip_stats,
        overwrite=args.overwrite
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
