
import xml.etree.ElementTree as ET
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
xml_path = project_root / "data" / "raw" / "kanjidic2.xml"

tree = ET.parse(xml_path)
root = tree.getroot()

# Find the entry for 愛
for character in root.findall("character"):
    literal = character.findtext("literal")

    if literal == "愛":
        readings = character.findall(
            ".//reading_meaning/rmgroup/reading"
        )
        meanings = character.findall(
            ".//reading_meaning/rmgroup/meaning"
        )
        stroke_count = character.findtext(
            "misc/stroke_count"
        )

        print("Character:", literal)
        print("Stroke count:", stroke_count)

        print("On'yomi:", [
            r.text for r in readings
            if r.get("r_type") == "ja_on"
        ])

        print("Kun'yomi:", [
            r.text for r in readings
            if r.get("r_type") == "ja_kun"
        ])

        print("English meanings:", [
            m.text for m in meanings
            if m.get("m_lang", "en") == "en"
        ])

        break
