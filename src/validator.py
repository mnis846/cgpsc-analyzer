"""
Parser output validator for CGPSC questions.

Validates draft question JSON for completeness and structure.
Year-agnostic: accepts year as parameter.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

EXPECTED_QUESTION_COUNT = 100
EXPECTED_OPTION_LABELS = {"A", "B", "C", "D"}


def validate_questions(document: dict) -> dict:
    """
    Validate parser output document.
    
    Args:
        document: Parsed questions document
        
    Returns:
        Dictionary with validation results
    """
    questions = document.get("questions", [])
    numbers = [question.get("question_no") for question in questions]
    expected_numbers = set(range(1, EXPECTED_QUESTION_COUNT + 1))
    actual_numbers = {number for number in numbers if isinstance(number, int)}

    review_items = []
    for question in questions:
        issues = list(question.get("warnings", []))
        labels = set(question.get("options", {}))

        if not question.get("question", "").strip():
            issues.append("empty question text")
        if labels != EXPECTED_OPTION_LABELS:
            issues.append(f"option labels found: {', '.join(sorted(labels)) or 'none'}")
        if issues:
            review_items.append(
                {
                    "question_no": question.get("question_no"),
                    "confidence": question.get("confidence"),
                    "issues": list(dict.fromkeys(issues)),
                    "question": question.get("question", ""),
                    "raw_text": question.get("raw_text", ""),
                }
            )

    duplicate_numbers = sorted({number for number in numbers if numbers.count(number) > 1})
    return {
        "valid_question_sequence": numbers == list(range(1, EXPECTED_QUESTION_COUNT + 1)),
        "questions_found": len(questions),
        "missing_question_numbers": sorted(expected_numbers - actual_numbers),
        "duplicate_question_numbers": duplicate_numbers,
        "questions_needing_review": len(review_items),
        "review_question_numbers": [item["question_no"] for item in review_items],
        "review_items": review_items,
    }


def run_validator(input_file: str, output_file: str) -> tuple[bool, str]:
    """
    Validate parser output.
    
    Args:
        input_file: Path to parser output JSON
        output_file: Path to validation report
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        return False, f"Input file not found: {input_path}"
    
    try:
        logger.info(f"Validating parser output: {input_path}")
        with open(input_path, 'r', encoding='utf-8') as f:
            document = json.load(f)
        
        report = validate_questions(document)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Determine if validation passed
        is_valid = (
            report["valid_question_sequence"] and
            len(report["missing_question_numbers"]) == 0 and
            len(report["duplicate_question_numbers"]) == 0
        )
        
        if is_valid:
            msg = f"✓ Validation passed: {report['questions_found']} questions"
            logger.info(msg)
            return True, msg
        else:
            issues = []
            if not report["valid_question_sequence"]:
                issues.append("invalid question sequence")
            if report["missing_question_numbers"]:
                issues.append(f"missing questions: {report['missing_question_numbers']}")
            if report["duplicate_question_numbers"]:
                issues.append(f"duplicate questions: {report['duplicate_question_numbers']}")
            msg = f"⚠ Validation issues: {', '.join(issues)}"
            logger.warning(msg)
            return True, msg  # Return success but with warnings
        
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
    parser.add_argument("input", type=Path, help="Path to parser output JSON")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output report path")
    args = parser.parse_args()

    success, message = run_validator(str(args.input), str(args.output))
    print(message)
    import sys
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
