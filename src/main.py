from pathlib import Path

from clean_text import clean_text
from pdf_to_images import pdf_to_images
from ocr import image_to_text


def run_ocr_pipeline(pdf_file, output_file):
    """
    OCR pipeline.

    Args:
        pdf_file: Path to PDF
        output_file: Path to OCR text output
    """

    images_dir = Path(output_file).parent / "images"

    images = pdf_to_images(
        str(pdf_file),
        str(images_dir)
    )

    full_text = ""

    for image in images:
        print("OCR:", image)

        full_text += image_to_text(image)
        full_text += "\n\n"

    full_text = clean_text(full_text)

    output_path = Path(output_file)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(full_text)

    print("Done.")

    return True


if __name__ == "__main__":
    run_ocr_pipeline(
        "data/pdfs/2025.pdf",
        "data/raw_text/ocr_output.txt"
    )