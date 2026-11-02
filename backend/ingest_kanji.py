
import argparse
import re

from backend.services.kanji_service import get_all_kanji
from backend.services.vocabulary_service import get_all_vocabulary
from backend.services.vector_store_service import (
    collection,
    embedding_model,
)


BATCH_SIZE = 128
MAX_VOCABULARY_PER_KANJI = 10


def get_priority_score(priority_tags):
    """Rank vocabulary using JMdict priority tags."""

    priority_order = {
        "ichi1": 0,
        "ichi2": 1,
        "news1": 2,
        "news2": 3,
    }

    best_priority = min(
        (
            priority_order[tag]
            for tag in priority_tags
            if tag in priority_order
        ),
        default=4,
    )

    nf_tags = [
        int(match.group(1))
        for tag in priority_tags
        if (match := re.fullmatch(r"nf(\d{2})", tag))
    ]

    nf_rank = min(nf_tags, default=999)

    return best_priority, nf_rank


def build_vocabulary_mapping(kanji_list, vocabulary_list):
    """Associate vocabulary entries with kanji in their written forms."""

    vocabulary_by_kanji = {
        item["character"]: []
        for item in kanji_list
    }

    kanji_characters = set(vocabulary_by_kanji)

    for word in vocabulary_list:
        written_forms = word.get("written_forms") or []
        matched_kanji = set()

        for form in written_forms:
            for character in form:
                if character in kanji_characters:
                    matched_kanji.add(character)

        for character in matched_kanji:
            vocabulary_by_kanji[character].append(word)

    # Rank and limit vocabulary for each kanji.
    for character, words in vocabulary_by_kanji.items():
        words.sort(
            key=lambda word: (
                get_priority_score(
                    word.get("priority_tags") or []
                ),
                word["entry_id"],
            )
        )

        vocabulary_by_kanji[character] = words[
            :MAX_VOCABULARY_PER_KANJI
        ]

    return vocabulary_by_kanji


def build_document(kanji, vocabulary):
    """Create a text document for one kanji."""

    lines = [
        f"Kanji: {kanji['character']}",
        f"Meanings: {', '.join(kanji.get('meanings') or [])}",
        f"Stroke count: {kanji.get('stroke_count')}",
        f"On'yomi readings: {', '.join(kanji.get('on_readings') or [])}",
        f"Kun'yomi readings: {', '.join(kanji.get('kun_readings') or [])}",
        "",
        "Related vocabulary:",
    ]

    if not vocabulary:
        lines.append("No related vocabulary found.")

    for word in vocabulary:
        written_forms = word.get("written_forms") or []
        readings = word.get("readings") or []
        meanings = word.get("meanings") or []
        priority_tags = word.get("priority_tags") or []

        lines.extend([
            f"Word: {', '.join(written_forms)}",
            f"Reading: {', '.join(readings)}",
            f"Meanings: {', '.join(meanings)}",
            f"Priority tags: {', '.join(priority_tags)}",
            "",
        ])

    return "\n".join(lines)


def preview_kanji(target, kanji_list, vocabulary_mapping):
    """Preview a document without storing it in ChromaDB."""

    kanji = next(
        (item for item in kanji_list if item["character"] == target),
        None,
    )

    if kanji is None:
        print(f"Kanji not found: {target}")
        return

    vocabulary = vocabulary_mapping.get(target, [])
    document = build_document(kanji, vocabulary)

    print("\n========== DOCUMENT PREVIEW ==========")
    print(document)
    print("\nVocabulary entries:", len(vocabulary))
    print("\nNo data has been inserted into ChromaDB.")


def ingest_documents(kanji_list, vocabulary_mapping):
    """Generate embeddings and upsert documents in batches."""

    total = len(kanji_list)
    stored = 0

    print("\nStarting ChromaDB ingestion...")
    print("Total documents:", total)
    print("Batch size:", BATCH_SIZE)

    for start in range(0, total, BATCH_SIZE):
        batch_kanji = kanji_list[start:start + BATCH_SIZE]

        documents = []
        ids = []
        metadatas = []

        for kanji in batch_kanji:
            character = kanji["character"]
            vocabulary = vocabulary_mapping.get(character, [])

            document = build_document(kanji, vocabulary)

            documents.append(document)
            ids.append(f"kanji_{character}")

            metadatas.append({
                "character": character,
                "type": "kanji",
                "vocabulary_count": len(vocabulary),
            })

        # Generate embeddings for the entire batch.
        embeddings = embedding_model.encode(
            documents,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        # Insert or update the documents in ChromaDB.
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )

        stored += len(batch_kanji)

        print(f"Processed {stored}/{total} documents")

    print("\n========== INGESTION COMPLETE ==========")
    print("Documents processed:", stored)
    print("ChromaDB collection count:", collection.count())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preview",
        metavar="KANJI",
        help="Preview a kanji document without inserting it",
    )

    args = parser.parse_args()

    print("Loading kanji...")
    kanji_list = get_all_kanji()

    print("Loading vocabulary...")
    vocabulary_list = get_all_vocabulary()

    print("Building vocabulary mapping...")
    vocabulary_mapping = build_vocabulary_mapping(
        kanji_list,
        vocabulary_list,
    )

    print("\nKanji loaded:", len(kanji_list))
    print("Vocabulary loaded:", len(vocabulary_list))

    if args.preview:
        preview_kanji(
            args.preview,
            kanji_list,
            vocabulary_mapping,
        )
        return

    ingest_documents(kanji_list, vocabulary_mapping)


if __name__ == "__main__":
    main()
