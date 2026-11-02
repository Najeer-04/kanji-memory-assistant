
def build_kanji_document(kanji: dict, vocabulary: list[dict]) -> str:
    """
    Convert kanji information and related vocabulary
    into a text document for semantic retrieval.
    """

    character = kanji["character"]

    lines = [
        f"Kanji: {character}",
        f"Meanings: {', '.join(kanji['meanings'])}",
        f"Stroke count: {kanji['stroke_count']}",
        f"On'yomi readings: {', '.join(kanji['on_readings'])}",
        f"Kun'yomi readings: {', '.join(kanji['kun_readings'])}",
        "",
        "Related vocabulary:",
    ]

    if not vocabulary:
        lines.append("No related vocabulary found.")

    for word in vocabulary:
        written_forms = ", ".join(word["written_forms"])
        readings = ", ".join(word["readings"])
        meanings = ", ".join(word["meanings"])

        lines.extend([
            f"Word: {written_forms}",
            f"Reading: {readings}",
            f"Meanings: {meanings}",
            f"Frequency rank: {word['frequency_rank']}",
            f"Priority tags: {', '.join(word['priority_tags'])}",
            "",
        ])

    return "\n".join(lines)
