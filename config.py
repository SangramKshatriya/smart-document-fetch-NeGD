from pathlib import Path


# File extensions that our application can currently process.
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".docx",
    ".xlsx",
    ".xls",
    ".txt",
}


# Default location for the local database/index.
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

DATABASE_PATH = DATA_DIR / "documents.db"