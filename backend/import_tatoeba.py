
import csv
import hashlib
from pathlib import Path

from backend.database import get_connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "tatoeba"

SENTENCES_PATH = DATA_DIR / "sentences.csv"
LINKS_PATH = DATA_DIR / "links.csv"

BATCH_SIZE = 2000


def setup_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS example_sentences (
            sentence_id BIGINT PRIMARY KEY,
            sentence_text TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'Tatoeba'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sentence_translations (
            id BIGSERIAL PRIMARY KEY,
            japanese_sentence_id BIGINT NOT NULL
                REFERENCES example_sentences(sentence_id)
                ON DELETE CASCADE,
            english_sentence_id BIGINT NOT NULL,
            english_text TEXT NOT NULL,
            english_hash TEXT,
            source TEXT NOT NULL DEFAULT 'Tatoeba'
        )
    """)

    # Remove the old constraint that indexed the entire translation.
    cursor.execute("""
        ALTER TABLE sentence_translations
        DROP CONSTRAINT IF EXISTS
            sentence_translations_japanese_sentence_id_english_text_key
    """)

    # Add the hash column to an existing table if necessary.
    cursor.execute("""
        ALTER TABLE sentence_translations
        ADD COLUMN IF NOT EXISTS english_hash TEXT
    """)

    # Backfill existing translations before enforcing the constraint.
    cursor.execute("""
        UPDATE sentence_translations
        SET english_hash = md5(english_text)
        WHERE english_hash IS NULL
    """)

    cursor.execute("""
        ALTER TABLE sentence_translations
        ALTER COLUMN english_hash SET NOT NULL
    """)

    # Remove any duplicates that may predate this migration.
    cursor.execute("""
        DELETE FROM sentence_translations AS t
        USING sentence_translations AS earlier
        WHERE t.japanese_sentence_id = earlier.japanese_sentence_id
          AND t.english_hash = earlier.english_hash
          AND t.id > earlier.id
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
            idx_sentence_translations_japanese_hash
        ON sentence_translations (
            japanese_sentence_id,
            english_hash
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sentence_translations_japanese
        ON sentence_translations(japanese_sentence_id)
    """)


def read_japanese_ids():
    japanese_ids = set()

    with SENTENCES_PATH.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        for row in csv.reader(file, delimiter="\t"):
            if len(row) < 3 or row[1] != "jpn":
                continue

            try:
                japanese_ids.add(int(row[0]))
            except ValueError:
                continue

    return japanese_ids


def read_links(japanese_ids):
    links_by_japanese = {}
    english_candidate_ids = set()

    with LINKS_PATH.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        for row in csv.reader(file, delimiter="\t"):
            if len(row) < 2:
                continue

            try:
                first_id = int(row[0])
                second_id = int(row[1])
            except ValueError:
                continue

            if first_id in japanese_ids and first_id != second_id:
                links_by_japanese.setdefault(first_id, set()).add(second_id)

            if second_id in japanese_ids and first_id != second_id:
                links_by_japanese.setdefault(second_id, set()).add(first_id)

    for linked_ids in links_by_japanese.values():
        english_candidate_ids.update(linked_ids)

    return links_by_japanese, english_candidate_ids


def import_sentences_and_translations():
    for path in (SENTENCES_PATH, LINKS_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Dataset not found: {path}")

    print("Reading Japanese sentence IDs...")
    japanese_ids = read_japanese_ids()

    print("Finding linked sentence IDs...")
    links_by_japanese, english_candidate_ids = read_links(japanese_ids)

    imported_sentences = 0
    imported_translations = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            setup_tables(cursor)

            english_by_id = {}
            sentence_batch = []

            print("Importing Japanese sentences...")

            with SENTENCES_PATH.open(
                "r", encoding="utf-8-sig", newline=""
            ) as file:
                for row in csv.reader(file, delimiter="\t"):
                    if len(row) < 3:
                        continue

                    try:
                        sentence_id = int(row[0])
                    except ValueError:
                        continue

                    language = row[1]
                    sentence_text = row[2].strip()

                    if not sentence_text:
                        continue

                    if language == "jpn":
                        sentence_batch.append(
                            (sentence_id, sentence_text, "Tatoeba")
                        )

                        if len(sentence_batch) >= BATCH_SIZE:
                            cursor.executemany("""
                                INSERT INTO example_sentences (
                                    sentence_id, sentence_text, source
                                )
                                VALUES (%s, %s, %s)
                                ON CONFLICT (sentence_id)
                                DO UPDATE SET
                                    sentence_text = EXCLUDED.sentence_text,
                                    source = EXCLUDED.source
                            """, sentence_batch)

                            imported_sentences += len(sentence_batch)
                            sentence_batch.clear()

                    elif (
                        language == "eng"
                        and sentence_id in english_candidate_ids
                    ):
                        english_by_id[sentence_id] = sentence_text

            if sentence_batch:
                cursor.executemany("""
                    INSERT INTO example_sentences (
                        sentence_id, sentence_text, source
                    )
                    VALUES (%s, %s, %s)
                    ON CONFLICT (sentence_id)
                    DO UPDATE SET
                        sentence_text = EXCLUDED.sentence_text,
                        source = EXCLUDED.source
                """, sentence_batch)

                imported_sentences += len(sentence_batch)

            print("Importing English translations...")

            translation_batch = []

            for japanese_id, linked_ids in links_by_japanese.items():
                for english_id in linked_ids:
                    english_text = english_by_id.get(english_id)

                    if english_text is None:
                        continue

                    english_hash = hashlib.md5(
                        english_text.encode("utf-8")
                    ).hexdigest()

                    translation_batch.append((
                        japanese_id,
                        english_id,
                        english_text,
                        english_hash,
                        "Tatoeba",
                    ))

                    if len(translation_batch) >= BATCH_SIZE:
                        cursor.executemany("""
                            INSERT INTO sentence_translations (
                                japanese_sentence_id,
                                english_sentence_id,
                                english_text,
                                english_hash,
                                source
                            )
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (
                                japanese_sentence_id,
                                english_hash
                            ) DO NOTHING
                        """, translation_batch)

                        imported_translations += len(translation_batch)
                        translation_batch.clear()

            if translation_batch:
                cursor.executemany("""
                    INSERT INTO sentence_translations (
                        japanese_sentence_id,
                        english_sentence_id,
                        english_text,
                        english_hash,
                        source
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (
                        japanese_sentence_id,
                        english_hash
                    ) DO NOTHING
                """, translation_batch)

                imported_translations += len(translation_batch)

    print("Tatoeba import finished.")
    print(f"Japanese sentences processed: {imported_sentences:,}")
    print(f"Translation records attempted: {imported_translations:,}")


if __name__ == "__main__":
    import_sentences_and_translations()
