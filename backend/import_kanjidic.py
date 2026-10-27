
import xml.etree.ElementTree as ET
from pathlib import Path

from backend.database import get_connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
XML_PATH = PROJECT_ROOT / "data" / "raw" / "kanjidic2.xml"

INSERT_QUERY = """
    INSERT INTO kanji (
        character,
        stroke_count,
        on_readings,
        kun_readings,
        meanings
    )
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (character) DO UPDATE SET
        stroke_count = EXCLUDED.stroke_count,
        on_readings = EXCLUDED.on_readings,
        kun_readings = EXCLUDED.kun_readings,
        meanings = EXCLUDED.meanings;
"""


def extract_kanji_records():
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    records = []

    for character in root.findall("character"):
        literal = character.findtext("literal")

        if literal is None:
            continue

        stroke_text = character.findtext("misc/stroke_count")
        stroke_count = int(stroke_text) if stroke_text else None

        readings = character.findall(
            "./reading_meaning/rmgroup/reading"
        )
        meanings = character.findall(
            "./reading_meaning/rmgroup/meaning"
        )

        on_readings = [
            reading.text
            for reading in readings
            if reading.get("r_type") == "ja_on" and reading.text
        ]

        kun_readings = [
            reading.text
            for reading in readings
            if reading.get("r_type") == "ja_kun" and reading.text
        ]

        english_meanings = [
            meaning.text
            for meaning in meanings
            if meaning.get("m_lang", "en") == "en" and meaning.text
        ]

        records.append(
            (
                literal,
                stroke_count,
                on_readings,
                kun_readings,
                english_meanings,
            )
        )

    return records


def import_kanji():
    records = extract_kanji_records()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(INSERT_QUERY, records)

    print(f"Imported or updated {len(records)} kanji records.")


if __name__ == "__main__":
    import_kanji()
