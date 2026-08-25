import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import SUPPORTED_EXTENSIONS
from content_extractor import extract_text
from database import get_connection, initialize_database


class DocumentFileHandler(FileSystemEventHandler):
    """
    Handles filesystem changes for supported documents.
    """

    def __init__(self):
        super().__init__()

    # =========================================================
    # FILE CREATED
    # =========================================================

    def on_created(self, event):
        """
        Called when a new file is created.
        """

        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if not self.is_supported_file(file_path):
            return

        print(f"\nNew file detected: {file_path}")

        self.index_file(file_path)

    # =========================================================
    # FILE MODIFIED
    # =========================================================

    def on_modified(self, event):
        """
        Called when a supported file is modified.
        """

        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if not self.is_supported_file(file_path):
            return

        print(f"\nFile modified: {file_path}")

        self.index_file(file_path)

    # =========================================================
    # FILE DELETED
    # =========================================================

    def on_deleted(self, event):
        """
        Called when a file is deleted.
        """

        if event.is_directory:
            return

        file_path = Path(event.src_path)

        print(f"\nFile deleted: {file_path}")

        self.remove_file(file_path)

    # =========================================================
    # FILE MOVED / RENAMED
    # =========================================================

    def on_moved(self, event):
        """
        Called when a file is renamed or moved.
        """

        if event.is_directory:
            return

        old_path = Path(event.src_path)
        new_path = Path(event.dest_path)

        print(
            f"\nFile moved/renamed:\n"
            f"Old: {old_path}\n"
            f"New: {new_path}"
        )

        # Remove old database entry.
        self.remove_file(old_path)

        # Add the file at its new location.
        if self.is_supported_file(new_path):
            self.index_file(new_path)

    # =========================================================
    # CHECK SUPPORTED EXTENSION
    # =========================================================

    @staticmethod
    def is_supported_file(file_path: Path) -> bool:
        """
        Check whether the file has a supported extension.
        """

        return (
            file_path.is_file()
            and file_path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        )

    # =========================================================
    # INDEX FILE
    # =========================================================

    def index_file(self, file_path: Path):
        """
        Extract metadata/content and insert or update
        the file in SQLite.
        """

        # Some applications create a file before finishing
        # writing it. Give the OS a moment to finish.
        time.sleep(0.5)

        if not file_path.exists():
            return

        try:
            stat = file_path.stat()

            content = extract_text(
                str(file_path)
            )

            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO documents
                (
                    name,
                    path,
                    extension,
                    size,
                    modified_time,
                    content
                )
                VALUES (?, ?, ?, ?, ?, ?)

                ON CONFLICT(path)
                DO UPDATE SET
                    name = excluded.name,
                    extension = excluded.extension,
                    size = excluded.size,
                    modified_time = excluded.modified_time,
                    content = excluded.content
                """,
                (
                    file_path.name,
                    str(file_path.resolve()),
                    file_path.suffix.lower(),
                    stat.st_size,
                    stat.st_mtime,
                    content,
                ),
            )

            connection.commit()
            connection.close()

            print(
                f"Indexed successfully: "
                f"{file_path.name}"
            )

        except PermissionError:
            print(
                f"Permission denied: {file_path}"
            )

        except Exception as error:
            print(
                f"Could not index {file_path}\n"
                f"Reason: {error}"
            )

    # =========================================================
    # REMOVE FILE
    # =========================================================

    def remove_file(self, file_path: Path):
        """
        Remove a file from the SQLite index.
        """

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                DELETE FROM documents
                WHERE path = ?
                """,
                (
                    str(file_path.resolve()),
                ),
            )

            connection.commit()
            connection.close()

            print(
                f"Removed from index: "
                f"{file_path.name}"
            )

        except Exception as error:
            print(
                f"Could not remove {file_path} "
                f"from index.\nReason: {error}"
            )


# =============================================================
# START WATCHER
# =============================================================

def start_file_watcher(folder_path: str):
    """
    Start watching the selected folder recursively.
    """

    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(
            f"Folder does not exist: {folder}"
        )

    if not folder.is_dir():
        raise NotADirectoryError(
            f"Not a directory: {folder}"
        )

    # Ensure database/table exists.
    initialize_database()

    event_handler = DocumentFileHandler()

    observer = Observer()

    observer.schedule(
        event_handler,
        str(folder),
        recursive=True,
    )

    observer.start()

    print("=" * 60)
    print("FILE WATCHER STARTED")
    print("=" * 60)
    print(f"Watching: {folder}")
    print("Monitoring subfolders: Yes")
    print("\nWatching for:")
    print("  + New files")
    print("  ~ Modified files")
    print("  - Deleted files")
    print("  ↔ Renamed/moved files")
    print("\nPress Ctrl+C to stop.")
    print("=" * 60)

    try:

        while True:
            time.sleep(1)

    except KeyboardInterrupt:

        print("\nStopping file watcher...")

        observer.stop()

    observer.join()

    print("File watcher stopped.")


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    folder = input(
        "Enter folder to watch: "
    ).strip().strip('"')

    try:

        start_file_watcher(folder)

    except Exception as error:

        print(
            f"Watcher failed: {error}"
        )
