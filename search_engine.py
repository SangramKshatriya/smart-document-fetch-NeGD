import re
from pathlib import Path

from database import get_connection, initialize_database


STOP_WORDS = {
    "give",
    "me",
    "my",
    "the",
    "a",
    "an",
    "show",
    "find",
    "get",
    "please",
    "document",
    "file",
    "of",
    "for",
    "to",
    "is",
    "where",
}


def normalize_text(text: str) -> str:
    """
    Convert text to lowercase and remove unnecessary
    special characters.
    """

    text = text.lower()

    text = re.sub(r"[^a-z0-9\s]", " ", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_search_terms(query: str):
    """
    Convert a natural-language query into useful
    search terms.
    """

    normalized = normalize_text(query)

    words = normalized.split()

    terms = [
        word
        for word in words
        if word not in STOP_WORDS and len(word) > 1
    ]

    return terms


def calculate_score(name, content, terms):
    """
    Calculate a simple relevance score.

    Filename matches receive a higher score than
    content matches.
    """

    name_text = normalize_text(name)
    content_text = normalize_text(content)

    score = 0

    for term in terms:

        # Strong match in filename
        if term in name_text:
            score += 10

        # Match inside document content
        if term in content_text:
            score += 3

    return score


def search_documents(query: str, limit: int = 10):
    """
    Search indexed documents and return the most
    relevant results.
    """

    terms = extract_search_terms(query)

    if not terms:
        return []

    initialize_database()

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            path,
            extension,
            size,
            modified_time,
            content
        FROM documents
        """
    )

    documents = cursor.fetchall()

    connection.close()

    results = []

    for document in documents:

        (
            document_id,
            name,
            path,
            extension,
            size,
            modified_time,
            content,
        ) = document

        score = calculate_score(
            name,
            content or "",
            terms,
        )

        if score > 0:

            results.append(
                {
                    "id": document_id,
                    "name": name,
                    "path": path,
                    "extension": extension,
                    "size": size,
                    "modified_time": modified_time,
                    "score": score,
                }
            )

    # Highest score first
    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:limit]


if __name__ == "__main__":

    query = input("What document are you looking for? ")

    results = search_documents(query)

    print("\n" + "=" * 70)
    print("SEARCH RESULTS")
    print("=" * 70)

    if not results:

        print("No matching documents found.")

    else:

        for index, result in enumerate(results, start=1):

            print(f"\n{index}. {result['name']}")
            print(f"   Score : {result['score']}")
            print(f"   Type  : {result['extension']}")
            print(f"   Path  : {result['path']}")