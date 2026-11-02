
import csv
import re
from pathlib import Path

from backend.database import get_connection

index_path = Path("data/processed/tatoeba/jpn_indices.csv")
annotation_pattern = re.compile(r"#(\d+)")

annotation_ids = set()
total_annotations = 0

with index_path.open(encoding="utf-8", newline="") as file:
    for row in csv.reader(file, delimiter="\t"):
        if len(row) < 3:
            continue

        ids = annotation_pattern.findall(row[2])
        total_annotations += len(ids)
        annotation_ids.update(map(int, ids))

with get_connection() as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM vocabulary")
        vocabulary_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(DISTINCT entry_id)
            FROM vocabulary
            WHERE entry_id = ANY(%s)
            """,
            (list(annotation_ids),),
        )
        matched_count = cursor.fetchone()[0]

print(f"Vocabulary entries in database: {vocabulary_count:,}")
print(f"Total annotation occurrences: {total_annotations:,}")
print(f"Unique annotation IDs: {len(annotation_ids):,}")
print(f"Matching vocabulary entries: {matched_count:,}")

