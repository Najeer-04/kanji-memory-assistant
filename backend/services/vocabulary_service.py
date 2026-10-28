
from backend.database import get_connection


def search_vocabulary(character: str, limit: int = 20):
    candidate_limit = 1000

    query = """
        SELECT
            v.entry_id,
            v.written_forms,
            v.readings,
            v.meanings,
            v.priority_tags,
            (
                SELECT MIN(f.frequency_rank)
                FROM unnest(v.written_forms) AS forms(form)
                CROSS JOIN unnest(v.readings) AS readings(reading)
                JOIN word_frequency AS f
                    ON f.word = forms.form
                   AND f.reading = readings.reading
            ) AS frequency_rank
        FROM vocabulary AS v
        WHERE EXISTS (
            SELECT 1
            FROM unnest(v.written_forms) AS forms(form)
            WHERE strpos(forms.form, %s) > 0
              AND char_length(forms.form) > 1
        )
        ORDER BY
            frequency_rank ASC NULLS LAST,
            CASE
                WHEN 'ichi1' = ANY(v.priority_tags) THEN 0
                WHEN 'ichi2' = ANY(v.priority_tags) THEN 1
                WHEN 'news1' = ANY(v.priority_tags) THEN 2
                WHEN 'news2' = ANY(v.priority_tags) THEN 3
                ELSE 4
            END,
            v.entry_id
        LIMIT %s;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (character, candidate_limit))
            rows = cursor.fetchall()

    candidates = [
        {
            "entry_id": row[0],
            "written_forms": row[1] or [],
            "readings": row[2] or [],
            "meanings": row[3] or [],
            "priority_tags": row[4] or [],
            "frequency_rank": row[5],
        }
        for row in rows
    ]

    return candidates[:limit]
