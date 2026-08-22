from pathlib import Path

import cv2
import numpy as np
import pymupdf
import pytesseract

from PIL import Image


TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def preprocess_for_ocr(pil_image: Image.Image) -> Image.Image:
    """
    Convert a document image into a cleaner image for OCR.
    """

    # PIL -> NumPy
    image = np.array(pil_image)

    # Convert RGB to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    # Remove small noise while preserving edges
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Adaptive thresholding handles uneven lighting/backgrounds
    threshold = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )

    # Upscale
    threshold = cv2.resize(
        threshold,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC,
    )

    return Image.fromarray(threshold)


def run_ocr(image: Image.Image) -> str:
    """
    Run OCR using several configurations and return the best output.
    """

    configs = [
        "--oem 3 --psm 6",
        "--oem 3 --psm 11",
    ]

    outputs = []

    for config in configs:
        print(f"Running OCR: {config}")

        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config=config,
        )

        if text.strip():
            outputs.append(text.strip())

    # Remove duplicate OCR results
    unique_outputs = []

    for text in outputs:
        if text not in unique_outputs:
            unique_outputs.append(text)

    return "\n\n".join(unique_outputs)


def extract_image_text(file_path: str) -> str:
    """
    OCR a JPG/PNG image.
    """

    try:
        image = Image.open(file_path).convert("RGB")

        processed = preprocess_for_ocr(image)

        return run_ocr(processed)

    except Exception as error:
        print(f"OCR failed for image: {file_path}")
        print(f"Reason: {error}")
        return ""


def extract_scanned_pdf_text(file_path: str) -> str:
    """
    Render each PDF page and run OCR.
    """

    text_parts = []

    try:
        document = pymupdf.open(file_path)

        for page_number, page in enumerate(document, start=1):

            print(f"OCR processing page {page_number}...")

            # High-resolution rendering
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(4, 4),
                alpha=False,
            )

            image = Image.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples,
            )

            # Save the original rendered page for debugging
            debug_path = Path(
                f"debug_page_{page_number}.png"
            )
            image.save(debug_path)

            processed = preprocess_for_ocr(image)

            # Save preprocessed version too
            processed_path = Path(
                f"debug_processed_{page_number}.png"
            )
            processed.save(processed_path)

            print(
                f"Rendered page: {debug_path}"
            )
            print(
                f"Processed page: {processed_path}"
            )

            text = run_ocr(processed)

            if text:
                text_parts.append(
                    f"[Page {page_number}]\n{text}"
                )
            else:
                print(
                    f"No OCR text detected on page {page_number}."
                )

        document.close()

    except Exception as error:
        print(f"OCR failed for PDF: {file_path}")
        print(f"Reason: {error}")

    return "\n\n".join(text_parts).strip()


def extract_ocr_text(file_path: str) -> str:
    """
    OCR images and scanned PDFs.
    """

    extension = Path(file_path).suffix.lower()

    if extension in {".jpg", ".jpeg", ".png"}:
        return extract_image_text(file_path)

    if extension == ".pdf":
        return extract_scanned_pdf_text(file_path)

    return ""


if __name__ == "__main__":

    file_path = input(
        "Enter image/PDF path: "
    ).strip().strip('"')

    path = Path(file_path)

    if not path.exists():
        print("File does not exist.")

    elif not path.is_file():
        print("The provided path is not a file.")

    else:
        text = extract_ocr_text(str(path))

        print("\n" + "=" * 60)
        print("OCR RESULT")
        print("=" * 60)

        if text:
            print(text)
        else:
            print("No text detected.")