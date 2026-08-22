from pathlib import Path


def get_preview_type(file_path: str) -> str:
    """
    Determine how a file should be previewed.
    """

    extension = Path(file_path).suffix.lower()

    if extension in {
        ".jpg",
        ".jpeg",
        ".png",
    }:
        return "image"

    if extension == ".pdf":
        return "pdf"

    if extension == ".docx":
        return "docx"

    if extension in {
        ".xlsx",
        ".xls",
    }:
        return "spreadsheet"

    if extension == ".txt":
        return "text"

    return "unsupported"