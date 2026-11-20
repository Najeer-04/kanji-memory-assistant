
from backend.services.hybrid_retrieval_service import search_hybrid


queries = [
    "Which kanji represents studying and learning?",
    "Which kanji means resting or taking a break?",
    "Which kanji is associated with eating food?",
    "Which kanji means bright or shining?",
    "Which kanji is associated with drinking water?"
]

for query in queries:
    print(f"\n{'=' * 70}")
    print(f"Query: {query}")
    print("=" * 70)

    results = search_hybrid(query)

    for rank, result in enumerate(results, start=1):
        metadata = result["metadata"]

        print(
            f"{rank}. {metadata['character']} | "
            f"Final: {result['final_score']:.5f} | "
            f"RRF: {result['rrf_score']:.5f} | "
            f"Priority: {result['learner_priority']:.2f} | "
            f"Dense: {result['dense_rank']} | "
            f"BM25: {result['bm25_rank']} | "
            f"Sources: {result['retrieval_sources']}"
        )
