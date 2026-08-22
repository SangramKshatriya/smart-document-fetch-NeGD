from pathlib import Path
from typing import Optional

import pymupdf
from docx import Document
from openpyxl import load_workbook


from ocr_engine import extract_ocr_text


def extract_pdf_text(file_path: str) -> str:
    """Extract text from every page of a PDF."""

    text_parts = []

    try:
        with pymupdf.open(file_path) as pdf:
            for page in pdf:
                page_text = page.get_text("text")

                if page_text:
                    text_parts.append(page_text)

    except Exception as error:
        print(f"Could not read PDF: {file_path}")
        print(f"Reason: {error}")

    return "\n".join(text_parts).strip()


def extract_docx_text(file_path: str) -> str:
    """Extract text from paragraphs and tables in a DOCX file."""

    text_parts = []

    try:
        document = Document(file_path)

        # Extract paragraphs
        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        # Extract tables
        for table in document.tables:
            for row in table.rows:
                row_values = []

                for cell in row.cells:
                    cell_text = cell.text.strip()

                    if cell_text:
                        row_values.append(cell_text)

                if row_values:
                    text_parts.append(" | ".join(row_values))

    except Exception as error:
        print(f"Could not read DOCX: {file_path}")
        print(f"Reason: {error}")

    return "\n".join(text_parts).strip()


def extract_xlsx_text(file_path: str) -> str:
    """Extract values from all worksheets in an XLSX file."""

    text_parts = []

    try:
        workbook = load_workbook(
            filename=file_path,
            read_only=True,
            data_only=True
        )

        for worksheet in workbook.worksheets:

            # Include sheet name because it can be useful during search.
            text_parts.append(f"[Sheet: {worksheet.title}]")

            for row in worksheet.iter_rows(values_only=True):

                values = []

                for value in row:
                    if value is not None:
                        values.append(str(value).strip())

                if values:
                    text_parts.append(" | ".join(values))

        workbook.close()

    except Exception as error:
        print(f"Could not read XLSX: {file_path}")
        print(f"Reason: {error}")

    return "\n".join(text_parts).strip()


def extract_txt_text(file_path: str) -> str:
    """Read a plain text file."""

    try:
        return Path(file_path).read_text(
            encoding="utf-8",
            errors="ignore"
        ).strip()

    except Exception as error:
        print(f"Could not read TXT: {file_path}")
        print(f"Reason: {error}")
        return ""


def extract_text(file_path: str) -> str:
    """
    Extract searchable text from supported files.

    PDF:
        Try normal text extraction first.
        If no text exists, use OCR.

    DOCX:
        Extract paragraphs and tables.

    XLSX:
        Extract cell values.

    TXT:
        Read plain text.

    JPG/PNG:
        Use OCR.
    """

    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        text = extract_pdf_text(file_path)

        if text.strip():
            return text

        print(f"No embedded text found. Using OCR: {file_path}")

        return extract_ocr_text(file_path)

    if extension == ".docx":
        return extract_docx_text(file_path)

    if extension == ".xlsx":
        return extract_xlsx_text(file_path)

    if extension == ".txt":
        return extract_txt_text(file_path)

    if extension in {".jpg", ".jpeg", ".png"}:
        return extract_ocr_text(file_path)

    return ""


if __name__ == "__main__":
    file_path = input("Enter document path: ").strip().strip('"')

    path = Path(file_path)

    if not path.exists():
        print("File does not exist.")
    elif not path.is_file():
        print("The provided path is not a file.")
    else:
        text = extract_text(str(path))

        print("\n" + "=" * 60)
        print("EXTRACTED CONTENT")
        print("=" * 60)

        if text:
            print(text)
        else:
            print("No text could be extracted.")