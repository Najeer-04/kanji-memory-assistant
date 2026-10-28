
import fugashi

from backend.database import get_connection


tagger = fugashi.Tagger()


def to_hiragana(text: str) -> str:
    """Convert katakana characters to hiragana."""
    result = []

    for character in text:
        code = ord(character)

        if 0x30A1 <= code <= 0x30F6:
            character = chr(code - 0x60)

        result.append(character)

    return "".join(result)


def get_hiragana_reading(sentence: str) -> str:
    """Generate a hiragana reading using Japanese word analysis."""
    reading_parts = []

    for word in tagger(sentence):
        word_reading = getattr(word.feature, "kana", None)

        if not word_reading or word_reading == "*":
            word_reading = word.surface

        reading_parts.append(to_hiragana(word_reading))

    return "".join(reading_parts)


def search_examples(
    written_forms: list[str],
    limit: int = 3,
):
    if not written_forms:
        return []

    query = """
        SELECT
            examples.sentence_id,
            examples.sentence_text,
            examples.english_text,
            char_length(examples.sentence_text) AS sentence_length
        FROM (
            SELECT DISTINCT ON (s.sentence_id)
                s.sentence_id,
                s.sentence_text,
                t.english_text
            FROM example_sentences AS s
            JOIN sentence_translations AS t
                ON t.japanese_sentence_id = s.sentence_id
            WHERE EXISTS (
                SELECT 1
                FROM unnest(%s::text[]) AS form(word)
                WHERE strpos(s.sentence_text, form.word) > 0
            )
            ORDER BY
                s.sentence_id,
                char_length(t.english_text) ASC,
                t.english_text ASC
        ) AS examples
        ORDER BY
            char_length(examples.sentence_text) ASC,
            examples.sentence_id ASC
        LIMIT %s;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (written_forms, limit))
            rows = cursor.fetchall()

    results = []

    for row in rows:
        japanese = row[1]

        results.append({
            "sentence_id": row[0],
            "japanese": japanese,
            "hiragana": get_hiragana_reading(japanese),
            "english": row[2],
            "source": "Tatoeba",
        })

    return results
