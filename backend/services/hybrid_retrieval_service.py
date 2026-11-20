
from backend.services.vector_store_service import search_kanji_documents
from backend.services.bm25_service import search_kanji_bm25


RETRIEVAL_WEIGHT = 0.80
LEARNER_PRIORITY_WEIGHT = 0.20
RRF_K = 60


def calculate_learner_priority(metadata):
    """
    Calculate a normalized learner-priority score.

    Uses the proportion of selected vocabulary entries
    tagged with NF01-NF05.
    """

    vocabulary_count = metadata.get("vocabulary_count", 0)
    top_frequency_count = metadata.get("top_frequency_count", 0)

    if vocabulary_count == 0:
        return 0.0

    return top_frequency_count / vocabulary_count


def search_hybrid(query: str, limit: int = 5, candidate_limit: int = 10):
    """
    Combine dense retrieval and BM25 using RRF,
    then rerank candidates using learner priority.
    """

    dense_results = search_kanji_documents(
        query,
        limit=candidate_limit
    )

    bm25_results = search_kanji_bm25(
        query,
        limit=candidate_limit
    )

    fused_results = {}

    def add_results(results, retrieval_source):
        for rank, result in enumerate(results, start=1):
            character = result["metadata"]["character"]

            if character not in fused_results:
                fused_results[character] = {
                    **result,
                    "rrf_score": 0.0,
                    "dense_rank": None,
                    "bm25_rank": None,
                    "retrieval_sources": []
                }

            fused = fused_results[character]

            fused["rrf_score"] += 1 / (RRF_K + rank)

            fused[f"{retrieval_source}_rank"] = rank

            if retrieval_source not in fused["retrieval_sources"]:
                fused["retrieval_sources"].append(retrieval_source)

    add_results(dense_results, "dense")
    add_results(bm25_results, "bm25")

    if not fused_results:
        return []

    # Normalize RRF scores so they fall between 0 and 1.
    max_rrf_score = max(
        result["rrf_score"]
        for result in fused_results.values()
    )

    for result in fused_results.values():
        metadata = result["metadata"]

        retrieval_score = result["rrf_score"] / max_rrf_score

        learner_priority = calculate_learner_priority(metadata)

        result["retrieval_score"] = retrieval_score
        result["learner_priority"] = learner_priority

        result["final_score"] = (
            RETRIEVAL_WEIGHT * retrieval_score
            + LEARNER_PRIORITY_WEIGHT * learner_priority
        )

    ranked_results = sorted(
        fused_results.values(),
        key=lambda item: (
            item["final_score"],
            item["rrf_score"]
        ),
        reverse=True
    )

    return ranked_results[:limit]
