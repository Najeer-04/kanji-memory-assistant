
from backend.database import get_connection


def search_kanji(character: str):
    query = """
        SELECT
            character,
            stroke_count,
            on_readings,
            kun_readings,
            meanings
        FROM kanji
        WHERE character = %s;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (character,))
            row = cursor.fetchone()

    if row is None:
        return None

    return {
        "character": row[0],
        "stroke_count": row[1],
        "on_readings": row[2] or [],
        "kun_readings": row[3] or [],
        "meanings": row[4] or [],
    }
