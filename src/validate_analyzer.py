"""
Analyzer output validator for CGPSC questions.

Validates that analyzer output is ready for database ingestion.
Year-agnostic: accepts file path as parameter instead of hardcoding.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_analyzer_output(document: dict) -> list[str]:
    """
    Validate analyzer output for database ingestion.
    
    Args:
        document: Analyzer output document
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    questions = document.get("questions", [])
    record_ids = [question.get("record_id") for question in questions]
    
    if len(record_ids) != len(set(record_ids)):
        errors.append("record_id values are not unique")

    required_classification = {"subject_id", "topic_id", "subtopic_id"}
    for question in questions:
        number = question.get("question_no")
        if not question.get("record_id"):
            errors.append(f"question {number}: missing record_id")
        
        primary = question.get("classification", {}).get("primary", {})
        missing = required_classification - set(primary)
        if missing:
            errors.append(f"question {number}: missing classification fields {sorted(missing)}")
        
        aggregation = question.get("aggregation", {})
        for field in ("exam_year", "subject_id", "topic_id", "subtopic_id", "question_type", "difficulty"):
            if not aggregation.get(field):
                errors.append(f"question {number}: missing aggregation.{field}")
    
    return errors


def run_analyzer_validator(input_file: str) -> tuple[bool, str]:
    """
    Validate analyzer output.
    
    Args:
        input_file: Path to analyzer output JSON
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        return False, f"Input file not found: {input_path}"
    
    try:
        logger.info(f"Validating analyzer output: {input_path}")
        with open(input_path, 'r', encoding='utf-8') as f:
            document = json.load(f)
        
        errors = validate_analyzer_output(document)
        
        if errors:
            error_msg = "\n  ".join(errors)
            msg = f"✗ Validation failed:\n  {error_msg}"
            logger.error(msg)
            return False, msg
        
        question_count = len(document.get("questions", []))
        msg = f"✓ Validation passed: {question_count} questions"
        logger.info(msg)
        return True, msg
        
    except json.JSONDecodeError as e:
        msg = f"Failed to parse JSON: {str(e)}"
        logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"Validation failed: {str(e)}"
        logger.error(msg)
        return False, msg


def main() -> None:
    """Command-line interface."""
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Path to analyzer output JSON")
    args = parser.parse_args()

    success, message = run_analyzer_validator(str(args.input))
    print(message)
    import sys
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
