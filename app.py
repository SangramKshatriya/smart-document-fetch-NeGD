import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from PySide6.QtWidgets import QApplication

from config import APP_VERSION
from ui.main_window import MainWindow
from ui.styles import APP_STYLE


def resolve_folder(folder_arg: str | None) -> str:
    """Resolve the document folder from CLI argument, environment, or terminal prompt."""
    import os

    folder = (folder_arg or os.getenv("DOCUMENT_FOLDER", "")).strip().strip('"')

    while True:
        if not folder:
            print("\nSmart Document Finder")
            print("Enter the folder containing the documents you want to search.")
            print(r'Example: C:\Users\YourName\Documents')
            try:
                folder = input("\nDocument folder: ").strip().strip('"')
            except EOFError as exc:
                raise RuntimeError(
                    "No document folder was provided. Run `python app.py \"C:\\path\\to\\documents\"` "
                    "or run it from an interactive terminal."
                ) from exc

        path = Path(folder).expanduser()
        if path.is_dir():
            return str(path.resolve())

        print(f"Folder not found: {path}")
        folder = ""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Search your documents from a simple desktop interface."
    )
    parser.add_argument(
        "folder", nargs="?",
        help="Document folder. If omitted, the terminal will ask for it."
    )
    parser.add_argument(
        "--reindex", action="store_true",
        help="Force a full reindex when the application starts."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    folder = resolve_folder(args.folder)

    print(f"\nDocument folder: {folder}")
    print("Starting Smart Document Finder…")
    print("You can search from the application window now.\n")

    app = QApplication(sys.argv)
    app.setApplicationName("Smart Document Finder")
    app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(APP_STYLE)
    window = MainWindow(folder, force_index=args.reindex)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
