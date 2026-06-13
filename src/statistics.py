"""
CGPSC Intelligence System - Statistics Module

Generates comprehensive statistics from analyzed CGPSC questions.
Designed to be modular and composable for multi-year trend analysis.

Year-agnostic: accepts input/output paths as parameters.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StatisticsReport:
    """Data class for statistics report."""
    total_questions: int
    subjects: Dict[str, int]
    topics: Dict[str, int]
    subtopics: Dict[str, int]
    difficulty: Dict[str, int]
    question_types: Dict[str, int]
    generated_at: str = ""
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding internal metadata."""
        return asdict(self)


class StatisticsGenerator:
    """
    Generates statistics from analyzed CGPSC questions.
    
    This class is modular and designed for aggregation across multiple years.
    Reads from the aggregation dict (normalized keys) in analyzer output.
    """
    
    def __init__(self, input_file: str, output_dir: str):
        """
        Initialize the statistics generator.
        
        Args:
            input_file: Path to input analyzed JSON file
            output_dir: Directory to save output
        """
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.questions: List[Dict[str, Any]] = []
        self.report: Optional[StatisticsReport] = None
    
    def load_questions(self) -> List[Dict[str, Any]]:
        """
        Load questions from analyzed JSON file.
        
        Returns:
            List of question dictionaries
            
        Raises:
            FileNotFoundError: If input file doesn't exist
            json.JSONDecodeError: If JSON is invalid
        """
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        logger.info(f"Loading questions from {self.input_file}")
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both direct list and nested structure
        if isinstance(data, list):
            self.questions = data
        elif isinstance(data, dict) and 'questions' in data:
            self.questions = data['questions']
        else:
            raise ValueError("Input JSON must be a list of questions or contain 'questions' key")
        
        logger.info(f"Loaded {len(self.questions)} questions")
        return self.questions
    
    def _count_field(self, aggregation_key: str) -> Dict[str, int]:
        """
        Count occurrences of a field from aggregation dict across all questions.
        
        Args:
            aggregation_key: Key name in the aggregation dict
            
        Returns:
            Dictionary with sorted counts (descending)
        """
        values = []
        for q in self.questions:
            aggregation = q.get('aggregation', {})
            value = aggregation.get(aggregation_key)
            if value:
                values.append(value)
        
        counter = Counter(values)
        return dict(sorted(counter.items(), key=lambda x: x[1], reverse=True))
    
    def generate_statistics(self) -> StatisticsReport:
        """
        Generate comprehensive statistics report.
        
        Returns:
            StatisticsReport object with all counts
        """
        if not self.questions:
            raise ValueError("No questions loaded. Call load_questions() first.")
        
        logger.info("Generating statistics...")
        
        self.report = StatisticsReport(
            total_questions=len(self.questions),
            subjects=self._count_field('subject_id'),
            topics=self._count_field('topic_id'),
            subtopics=self._count_field('subtopic_id'),
            difficulty=self._count_field('difficulty'),
            question_types=self._count_field('question_type')
        )
        
        logger.info(f"Statistics generated: {self.report.total_questions} questions processed")
        return self.report
    
    def validate_counts(self) -> list[str]:
        """
        Validate that all dimension counts sum to total questions.
        
        Returns:
            List of validation errors (empty if valid)
        """
        if not self.report:
            raise ValueError("Report not generated. Call generate_statistics() first.")
        
        errors = []
        total = self.report.total_questions
        
        subject_sum = sum(self.report.subjects.values())
        if subject_sum != total:
            errors.append(f"Subject counts sum to {subject_sum}, expected {total}")
        
        topic_sum = sum(self.report.topics.values())
        if topic_sum != total:
            errors.append(f"Topic counts sum to {topic_sum}, expected {total}")
        
        subtopic_sum = sum(self.report.subtopics.values())
        if subtopic_sum != total:
            errors.append(f"Subtopic counts sum to {subtopic_sum}, expected {total}")
        
        difficulty_sum = sum(self.report.difficulty.values())
        if difficulty_sum != total:
            errors.append(f"Difficulty counts sum to {difficulty_sum}, expected {total}")
        
        question_type_sum = sum(self.report.question_types.values())
        if question_type_sum != total:
            errors.append(f"Question type counts sum to {question_type_sum}, expected {total}")
        
        return errors
    
    def save_report(self, output_file: str) -> Path:
        """
        Save statistics report to JSON file.
        
        Args:
            output_file: Output filename
            
        Returns:
            Path to saved file
            
        Raises:
            ValueError: If report hasn't been generated yet
        """
        if not self.report:
            raise ValueError("Report not generated. Call generate_statistics() first.")
        
        output_path = self.output_dir / output_file
        
        logger.info(f"Saving report to {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.report.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report saved successfully")
        return output_path
    
    def print_summary(self) -> None:
        """Print formatted summary to console."""
        if not self.report:
            raise ValueError("Report not generated. Call generate_statistics() first.")
        
        print("\n" + "="*60)
        print("CGPSC STATISTICS SUMMARY")
        print("="*60)
        
        print(f"\nTotal Questions: {self.report.total_questions}\n")
        
        self._print_section("SUBJECTS", self.report.subjects)
        self._print_section("TOPICS", self.report.topics)
        self._print_section("SUBTOPICS", self.report.subtopics)
        self._print_section("DIFFICULTY LEVELS", self.report.difficulty)
        self._print_section("QUESTION TYPES", self.report.question_types)
        
        print("="*60 + "\n")
    
    @staticmethod
    def _print_section(title: str, data: Dict[str, int], max_items: Optional[int] = None) -> None:
        """
        Print a formatted section of statistics.
        
        Args:
            title: Section title
            data: Dictionary of items and counts
            max_items: Maximum items to display (None = all)
        """
        print(f"=== {title} ===")
        
        items = list(data.items())[:max_items] if max_items else data.items()
        
        if not items:
            print("(No data)\n")
            return
        
        # Calculate column widths for alignment
        max_name_len = max(len(str(k)) for k, _ in items)
        max_count_len = max(len(str(v)) for _, v in items)
        
        for name, count in items:
            print(f"  {name:<{max_name_len}}  {count:>{max_count_len}}")
        
        print()
    
    def get_report_dict(self) -> Dict[str, Any]:
        """
        Get report as dictionary (useful for aggregation).
        
        Returns:
            Dictionary representation of the report
        """
        if not self.report:
            raise ValueError("Report not generated. Call generate_statistics() first.")
        
        return self.report.to_dict()
    
    def aggregate_reports(self, *other_reports: Dict[str, Any]) -> StatisticsReport:
        """
        Aggregate this report with other reports (for multi-year analysis).
        
        Args:
            *other_reports: Other StatisticsReport dictionaries to aggregate
            
        Returns:
            Aggregated StatisticsReport
            
        Raises:
            ValueError: If current report not generated or invalid reports passed
        """
        if not self.report:
            raise ValueError("Report not generated. Call generate_statistics() first.")
        
        if not other_reports:
            logger.warning("No reports provided for aggregation")
            return self.report
        
        logger.info(f"Aggregating {len(other_reports)} reports...")
        
        # Start with current report
        aggregated = {
            'total_questions': self.report.total_questions,
            'subjects': Counter(self.report.subjects),
            'topics': Counter(self.report.topics),
            'subtopics': Counter(self.report.subtopics),
            'difficulty': Counter(self.report.difficulty),
            'question_types': Counter(self.report.question_types)
        }
        
        # Add other reports
        for report_dict in other_reports:
            if not isinstance(report_dict, dict):
                raise ValueError("Each report must be a dictionary")
            
            aggregated['total_questions'] += report_dict.get('total_questions', 0)
            aggregated['subjects'].update(report_dict.get('subjects', {}))
            aggregated['topics'].update(report_dict.get('topics', {}))
            aggregated['subtopics'].update(report_dict.get('subtopics', {}))
            aggregated['difficulty'].update(report_dict.get('difficulty', {}))
            aggregated['question_types'].update(report_dict.get('question_types', {}))
        
        # Convert Counters back to sorted dicts
        aggregated_report = StatisticsReport(
            total_questions=aggregated['total_questions'],
            subjects=dict(sorted(aggregated['subjects'].items(), key=lambda x: x[1], reverse=True)),
            topics=dict(sorted(aggregated['topics'].items(), key=lambda x: x[1], reverse=True)),
            subtopics=dict(sorted(aggregated['subtopics'].items(), key=lambda x: x[1], reverse=True)),
            difficulty=dict(sorted(aggregated['difficulty'].items(), key=lambda x: x[1], reverse=True)),
            question_types=dict(sorted(aggregated['question_types'].items(), key=lambda x: x[1], reverse=True))
        )
        
        logger.info(f"Aggregation complete: {aggregated_report.total_questions} total questions")
        return aggregated_report


def run_statistics(input_file: str, output_file: str) -> tuple[bool, str]:
    """
    Generate statistics from analyzer output.
    
    Args:
        input_file: Path to analyzer output JSON
        output_file: Path to save statistics JSON
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        output_dir = Path(output_file).parent
        output_filename = Path(output_file).name
        
        generator = StatisticsGenerator(input_file, str(output_dir))
        generator.load_questions()
        generator.generate_statistics()
        
        # Validate
        validation_errors = generator.validate_counts()
        if validation_errors:
            msg = f"Statistics validation failed: {validation_errors}"
            logger.error(msg)
            return False, msg
        
        generator.save_report(output_filename)
        msg = f"✓ Statistics generated: {generator.report.total_questions} questions"
        logger.info(msg)
        return True, msg
        
    except Exception as e:
        msg = f"Statistics generation failed: {str(e)}"
        logger.error(msg)
        return False, msg


def main():
    """Main entry point for statistics generation (legacy CLI)."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Path to analyzer output JSON")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output statistics JSON file")
    args = parser.parse_args()

    success, message = run_statistics(str(args.input), str(args.output))
    print(message)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
