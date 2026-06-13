"""
Pipeline configuration management for CGPSC Intelligence System.

Handles all path resolution, making the pipeline year-agnostic.
All file paths are computed dynamically based on year parameter.
"""

from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
DATABASE_ROOT = PROJECT_ROOT / "database"
TAXONOMY_ROOT = DATA_ROOT / "taxonomy"


class PipelineConfig:
    """
    Configuration for processing a single exam year.
    
    All paths are computed dynamically from the year parameter.
    No hardcoded filenames or directories.
    """
    
    def __init__(self, year: int, repo_root: Optional[Path] = None):
        """
        Initialize pipeline configuration for a given year.
        
        Args:
            year: Exam year (e.g., 2025, 2024, 2002)
            repo_root: Repository root (defaults to PROJECT_ROOT)
        """
        self.year = year
        self.repo_root = repo_root or PROJECT_ROOT
        self.data_root = self.repo_root / "data"
        self.database_root = self.repo_root / "database"
        self.taxonomy_root = self.data_root / "taxonomy"
    
    # ===== INPUT PATHS =====
    
    @property
    def pdf_path(self) -> Path:
        """Path to input PDF file."""
        return self.data_root / "pdfs" / f"{self.year}.pdf"
    
    @property
    def pdf_exists(self) -> bool:
        """Check if PDF exists."""
        return self.pdf_path.exists()
    
    # ===== INTERMEDIATE OUTPUT PATHS =====
    
    @property
    def year_data_dir(self) -> Path:
        """Directory for year-specific intermediate data."""
        return self.data_root / "years" / str(self.year)
    
    @property
    def images_dir(self) -> Path:
        """Directory for PDF pages converted to images."""
        return self.year_data_dir / "images"
    
    @property
    def ocr_output_path(self) -> Path:
        """Path to OCR text output."""
        return self.year_data_dir / "ocr_output.txt"
    
    @property
    def raw_text_dir(self) -> Path:
        """Legacy path for raw text (backward compatibility)."""
        return self.data_root / "raw_text"
    
    @property
    def raw_text_legacy_path(self) -> Path:
        """Legacy single raw_text file path (for backward compatibility)."""
        return self.raw_text_dir / "ocr_output.txt"
    
    @property
    def json_dir(self) -> Path:
        """Directory for parsed question JSON."""
        return self.data_root / "json"
    
    @property
    def questions_json_path(self) -> Path:
        """Path to parsed questions JSON."""
        return self.json_dir / f"questions_{self.year}.json"
    
    @property
    def analyzed_dir(self) -> Path:
        """Directory for analyzed questions."""
        return self.data_root / "analyzed"
    
    @property
    def analyzed_json_path(self) -> Path:
        """Path to analyzed questions JSON."""
        return self.analyzed_dir / f"cgpsc_{self.year}_analyzed.json"
    
    @property
    def validation_dir(self) -> Path:
        """Directory for validation reports."""
        return self.data_root / "validation"


    @property
    def validator_output_path(self) -> Path:
        """Path to validation report."""
        return self.validation_dir / f"cgpsc_{self.year}_validation.json"
    
    # ===== DATABASE PATHS =====
    
    @property
    def database_questions_dir(self) -> Path:
        """Directory for ingested questions."""
        return self.database_root / "questions"
    
    @property
    def database_paper_path(self) -> Path:
        """Path to paper in database."""
        return self.database_questions_dir / f"{self.year}.json"
    
    @property
    def database_metadata_dir(self) -> Path:
        """Directory for metadata."""
        return self.database_root / "metadata"
    
    @property
    def database_metadata_path(self) -> Path:
        """Path to paper metadata in database."""
        return self.database_metadata_dir / f"{self.year}_metadata.json"
    
    @property
    def database_stats_dir(self) -> Path:
        """Directory for statistics."""
        return self.database_root / "stats"
    
    @property
    def database_stats_path(self) -> Path:
        """Path to statistics file in database."""
        return self.database_stats_dir / f"cgpsc_{self.year}_stats.json"
    
    @property
    def database_index_path(self) -> Path:
        """Path to database index."""
        return self.database_root / "index.json"
    
    # ===== TAXONOMY PATHS =====
    
    @property
    def taxonomy_path(self) -> Path:
        """Path to taxonomy file."""
        return self.taxonomy_root / "cgpsc_taxonomy_v1.json"
    
    @property
    def taxonomy_exists(self) -> bool:
        """Check if taxonomy file exists."""
        return self.taxonomy_path.exists()
    
    # ===== UTILITY METHODS =====
    
    def create_directories(self) -> None:
        """Create all necessary directories for this year's processing."""
        self.year_data_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self.analyzed_dir.mkdir(parents=True, exist_ok=True)
        self.validation_dir.mkdir(parents=True, exist_ok=True)
        self.raw_text_dir.mkdir(parents=True, exist_ok=True)
        self.database_questions_dir.mkdir(parents=True, exist_ok=True)
        self.database_metadata_dir.mkdir(parents=True, exist_ok=True)
        self.database_stats_dir.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate that all required inputs/configurations exist.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not self.pdf_exists:
            errors.append(f"PDF not found: {self.pdf_path}")
        
        if not self.taxonomy_exists:
            errors.append(f"Taxonomy not found: {self.taxonomy_path}")
        
        return len(errors) == 0, errors
    
    def __repr__(self) -> str:
        """String representation."""
        return f"PipelineConfig(year={self.year}, repo={self.repo_root})"
    
    def summary(self) -> dict:
        """Get summary of configuration."""
        return {
            "year": self.year,
            "pdf_path": str(self.pdf_path),
            "ocr_output": str(self.ocr_output_path),
            "questions_json": str(self.questions_json_path),
            "analyzed_json": str(self.analyzed_json_path),
            "database_paper": str(self.database_paper_path),
            "database_stats": str(self.database_stats_path),
        }
