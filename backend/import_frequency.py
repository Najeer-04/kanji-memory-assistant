
import csv
from pathlib import Path

from backend.database import get_connection


CSV_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "frequency_list_global.csv"
)

BATCH_SIZE = 5000


def create_frequency_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS word_frequency (
            word TEXT NOT NULL,
            reading TEXT NOT NULL,
            frequency_rank INTEGER NOT NULL,
            PRIMARY KEY (word, reading)
        );
        """
    )


def import_frequency_data():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Frequency CSV not found: {CSV_PATH}"
        )

    total_rows = 0
    processed_rows = 0
    batch = []

    with get_connection() as connection:
        with connection.cursor() as cursor:
            create_frequency_table(cursor)

            with CSV_PATH.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as csv_file:
                reader = csv.DictReader(csv_file)

                required_columns = {"Word", "Form", "Rank"}

                if not required_columns.issubset(
                    reader.fieldnames or []
                ):
                    raise ValueError(
                        "CSV must contain Word, Form, and Rank columns."
                    )

                for row in reader:
                    word = row["Word"].strip()
                    reading = row["Form"].strip()
                    rank = int(row["Rank"])

                    if not word or not reading or rank < 1:
                        continue

                    batch.append((word, reading, rank))
                    total_rows += 1

                    if len(batch) >= BATCH_SIZE:
                        processed_rows += save_batch(
                            cursor,
                            batch,
                        )
                        batch.clear()

                if batch:
                    processed_rows += save_batch(
                        cursor,
                        batch,
                    )

    print("Frequency import completed.")
    print(f"CSV rows processed: {total_rows}")
    print(f"Rows submitted to database: {processed_rows}")


def save_batch(cursor, batch):
    cursor.executemany(
        """
        INSERT INTO word_frequency (
            word,
            reading,
            frequency_rank
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (word, reading)
        DO UPDATE SET
            frequency_rank = LEAST(
                word_frequency.frequency_rank,
                EXCLUDED.frequency_rank
            );
        """,
        batch,
    )

    return len(batch)


if __name__ == "__main__":
    import_frequency_data()
