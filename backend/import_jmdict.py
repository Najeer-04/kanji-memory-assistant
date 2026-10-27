
import xml.etree.ElementTree as ET
from pathlib import Path

from backend.database import get_connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
XML_PATH = PROJECT_ROOT / "data" / "raw" / "JMdict_e.xml"

BATCH_SIZE = 1000

INSERT_QUERY = """
    INSERT INTO vocabulary (
    entry_id,
    written_forms,
    readings,
    meanings,
    priority_tags
)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (entry_id) DO UPDATE SET
    written_forms = EXCLUDED.written_forms,
    readings = EXCLUDED.readings,
    meanings = EXCLUDED.meanings,
    priority_tags = EXCLUDED.priority_tags;
"""


def extract_entry(entry):
    entry_id = entry.findtext("ent_seq")

    if entry_id is None:
        return None

    written_forms = [
        element.text
        for element in entry.findall("./k_ele/keb")
        if element.text
    ]

    readings = [
        element.text
        for element in entry.findall("./r_ele/reb")
        if element.text
    ]

    meanings = [
        element.text
        for element in entry.findall("./sense/gloss")
        if element.text
        and element.get("xml:lang", "eng") == "eng"
    ]

    priority_tags = sorted({
    element.text
    for element in entry.findall(".//ke_pri")
    + entry.findall(".//re_pri")
    if element.text
    })

    return (
        int(entry_id),
        written_forms,
        readings,
        meanings,
        priority_tags,
    )


def import_vocabulary():
    batch = []
    imported_count = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for _, element in ET.iterparse(XML_PATH, events=("end",)):
                if element.tag != "entry":
                    continue

                record = extract_entry(element)

                if record is not None:
                    batch.append(record)

                element.clear()

                if len(batch) >= BATCH_SIZE:
                    cursor.executemany(INSERT_QUERY, batch)
                    imported_count += len(batch)
                    batch.clear()

            if batch:
                cursor.executemany(INSERT_QUERY, batch)
                imported_count += len(batch)

    print(f"Imported or updated {imported_count} vocabulary entries.")


if __name__ == "__main__":
    import_vocabulary()
