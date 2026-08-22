from pathlib import Path
from typing import List, Dict

from config import SUPPORTED_EXTENSIONS


def scan_folder(folder_path: str) -> List[Dict]:
    """
    Recursively scan a folder and return information
    about all supported files.
    """

    root = Path(folder_path)

    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")

    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder_path}")

    files = []

    for file_path in root.rglob("*"):

        # Ignore folders
        if not file_path.is_file():
            continue

        # Get extension
        extension = file_path.suffix.lower()

        # Ignore unsupported file types
        if extension not in SUPPORTED_EXTENSIONS:
            continue

        try:
            stat = file_path.stat()

            file_info = {
                "name": file_path.name,
                "path": str(file_path.resolve()),
                "extension": extension,
                "size": stat.st_size,
                "modified_time": stat.st_mtime,
            }

            files.append(file_info)

        except (PermissionError, OSError) as error:
            print(f"Could not access: {file_path}")
            print(f"Reason: {error}")

    return files


if __name__ == "__main__":
    folder = input("Enter folder path: ").strip()

    try:
        results = scan_folder(folder)

        print(f"\nFound {len(results)} supported files:\n")

        for index, file_info in enumerate(results, start=1):
            print(f"{index}. {file_info['name']}")
            print(f"   Type : {file_info['extension']}")
            print(f"   Path : {file_info['path']}")
            print()

    except Exception as error:
        print(f"Error: {error}")