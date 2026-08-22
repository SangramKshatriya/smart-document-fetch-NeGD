from scanner import scan_folder
from content_extractor import extract_text
from database import get_connection, initialize_database


def index_folder(folder_path: str):
    """
    Scan a folder, extract document content,
    and store/update documents in SQLite.
    """

    files = scan_folder(folder_path)

    connection = get_connection()
    cursor = connection.cursor()

    indexed_count = 0

    for file_info in files:

        path = file_info["path"]

        print(f"Indexing: {file_info['name']}")

        content = extract_text(path)

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
                file_info["name"],
                path,
                file_info["extension"],
                file_info["size"],
                file_info["modified_time"],
                content,
            ),
        )

        indexed_count += 1

    connection.commit()
    connection.close()

    print(f"\nIndexed {indexed_count} files.")


if __name__ == "__main__":
    folder = input("Enter folder path: ").strip().strip('"')

    try:
        initialize_database()
        index_folder(folder)

    except Exception as error:
        print(f"Indexing failed: {error}")