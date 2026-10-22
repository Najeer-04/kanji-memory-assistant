
import xml.etree.ElementTree as ET
from pathlib import Path

# Locate the XML file relative to the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
XML_PATH = PROJECT_ROOT / "data" / "raw" / "kanjidic2.xml"


def load_kanji_data():
    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    kanji_data = {}

    for character in root.findall("character"):
        literal = character.findtext("literal")

        if literal is None:
            continue

        readings = character.findall(
            "./reading_meaning/rmgroup/reading"
        )
        meanings = character.findall(
            "./reading_meaning/rmgroup/meaning"
        )

        kanji_data[literal] = {
            "character": literal,
            "stroke_count": [
                int(value.text)
                for value in character.findall("misc/stroke_count")
                if value.text
            ],
            "on_readings": [
                r.text for r in readings
                if r.get("r_type") == "ja_on" and r.text
            ],
            "kun_readings": [
                r.text for r in readings
                if r.get("r_type") == "ja_kun" and r.text
            ],
            "meanings": [
                m.text for m in meanings
                if m.get("m_lang", "en") == "en" and m.text
            ],
        }

    return kanji_data


# Load the data once when this module is imported.
KANJI_DATA = load_kanji_data()


def search_kanji(character: str):
    return KANJI_DATA.get(character)
