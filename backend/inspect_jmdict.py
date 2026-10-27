
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
XML_PATH = PROJECT_ROOT / "data" / "raw" / "JMdict_e.xml"

tree = ET.parse(XML_PATH)
root = tree.getroot()

print("Root tag:", root.tag)
print("Total entries:", len(root.findall("entry")))

for entry in root.findall("entry"):
    kanji_elements = entry.findall("./k_ele/keb")
    reading_elements = entry.findall("./r_ele/reb")
    meaning_elements = entry.findall("./sense/gloss")

    kanji_forms = [element.text for element in kanji_elements]
    readings = [element.text for element in reading_elements]
    meanings = [element.text for element in meaning_elements]

    if "学校" in kanji_forms or "学生" in kanji_forms:
        print("\nEntry ID:", entry.findtext("ent_seq"))
        print("Written forms:", kanji_forms)
        print("Readings:", readings)
        print("Meanings:", meanings[:5])


from collections import Counter

frequency_tags = Counter()
entries_with_frequency = 0
examples = []

for entry in root.findall("entry"):
    entry_tags = []

    for element in entry.findall("./k_ele/ke_pri"):
        if element.text:
            entry_tags.append(element.text)

    for element in entry.findall("./r_ele/re_pri"):
        if element.text:
            entry_tags.append(element.text)

    if entry_tags:
        entries_with_frequency += 1
        frequency_tags.update(entry_tags)

        if len(examples) < 15:
            written_forms = [
                e.text for e in entry.findall("./k_ele/keb") if e.text
            ]
            readings = [
                e.text for e in entry.findall("./r_ele/reb") if e.text
            ]

            examples.append(
                (written_forms, readings, sorted(set(entry_tags)))
            )

print("\nEntries with frequency/priority tags:", entries_with_frequency)
print("\nMost common tags:")
for tag, count in frequency_tags.most_common():
    print(f"{tag}: {count}")

print("\nExamples:")
for written, readings, tags in examples:
    print(written, readings, tags)
