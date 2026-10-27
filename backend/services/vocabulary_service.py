
from backend.database import get_connection
from backend.services.ollama_reranker import rerank_vocabulary


def candidate_score(word: dict) -> int:
    """Score vocabulary using general JMdict priority tags."""
    tags = word["priority_tags"]
    score = 0

    if "ichi1" in tags:
        score += 100
    elif "ichi2" in tags:
        score += 70

    if "news1" in tags:
        score += 20
    elif "news2" in tags:
        score += 10

    nf_bands = [
        int(tag[2:])
        for tag in tags
        if tag.startswith("nf") and tag[2:].isdigit()
    ]

    if nf_bands:
        score += max(0, 50 - min(nf_bands))

    return score


def debug_word_stage(
    stage: str,
    character: str,
    words: list[dict],
):
    """Print a general summary of a vocabulary ranking stage."""
    print(
        f"\n[{character}] {stage}: {len(words)} entries",
        flush=True,
    )

    for position, word in enumerate(words, start=1):
        print(
            f"  {position}. score={candidate_score(word)} | "
            f"ID={word['entry_id']} | "
            f"words={word['written_forms']} | "
            f"readings={word['readings']} | "
            f"tags={word['priority_tags']}",
            flush=True,
        )


def search_vocabulary(character: str, limit: int = 20):
    candidate_limit = 1000
    shortlist_limit = 30

    query = """
        SELECT
            v.entry_id,
            v.written_forms,
            v.readings,
            v.meanings,
            v.priority_tags
        FROM vocabulary AS v
        WHERE EXISTS (
            SELECT 1
            FROM unnest(v.written_forms) AS forms(form)
            WHERE strpos(forms.form, %s) > 0
              AND char_length(forms.form) > 1
        )
        ORDER BY
            (
                SELECT MIN(substring(tags.tag FROM 3)::INTEGER)
                FROM unnest(v.priority_tags) AS tags(tag)
                WHERE tags.tag ~ '^nf[0-9]{2}$'
            ) ASC NULLS LAST,
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
        }
        for row in rows
    ]

    debug_word_stage("SQL candidates", character, candidates)

    if not candidates:
        return []

    # Rank the retrieved candidates using JMdict priority signals.
    scored_candidates = sorted(
        candidates,
        key=candidate_score,
        reverse=True,
    )

    shortlist = scored_candidates[:shortlist_limit]

    debug_word_stage("Python shortlist", character, shortlist)

    # Let Ollama rerank the shortlist.
    ranked_candidates = rerank_vocabulary(
        character,
        shortlist,
    )

    debug_word_stage("Ollama results", character, ranked_candidates)

    return ranked_candidates[:limit]
