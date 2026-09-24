from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "documents.db"

SUPPORTED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx", ".xls", ".txt"
}

DEFAULT_SEARCH_RESULT_LIMIT = 5
RECURSIVE_SCAN = True

# OCR: can be overridden with environment variables.
TESSERACT_DEFAULT_PATH = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)
OCR_LANGUAGES = os.getenv(
    "OCR_LANGUAGES",
    "eng+hin+mar+guj+tam+tel+kan+mal+ben+pan+ori+asm",
)
OCR_DPI = int(os.getenv("OCR_DPI", "220"))

APP_VERSION = "3.2.2-voice-diagnostics"
DEFAULT_UI_LANGUAGE = os.getenv("DEFAULT_UI_LANGUAGE", "en-IN")
LANGUAGE_PROVIDER = os.getenv("LANGUAGE_PROVIDER", "sarvam")
