
import json
from pathlib import Path

from backend.services.vector_store_service import search_kanji_documents
from backend.services.bm25_service import search_kanji_bm25


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = (
    PROJECT_ROOT
    / "backend"
    / "evaluation"
    / "retrieval_queries.json"
)

RRF_K = 60
RETRIEVAL_WEIGHT = 0.80
LEARNER_PRIORITY_WEIGHT = 0.20

TOP_K = 5
CANDIDATE_LIMIT = 10


def load_queries():
    """Load evaluation queries from the JSON dataset."""

    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_character(result):
    """Extract the kanji character from a retrieval result."""

    return result["metadata"]["character"]


def calculate_rrf(dense_results, bm25_results):
    """Combine dense and BM25 results using RRF."""

    fused_results = {}

    def add_results(results, source):
        for rank, result in enumerate(results, start=1):
            character = get_character(result)

            if character not in fused_results:
                fused_results[character] = {
                    **result,
                    "rrf_score": 0.0,
                    "dense_rank": None,
                    "bm25_rank": None,
                    "retrieval_sources": [],
                }

            fused = fused_results[character]

            fused["rrf_score"] += 1 / (RRF_K + rank)
            fused[f"{source}_rank"] = rank

            if source not in fused["retrieval_sources"]:
                fused["retrieval_sources"].append(source)

    add_results(dense_results, "dense")
    add_results(bm25_results, "bm25")

    return sorted(
        fused_results.values(),
        key=lambda item: item["rrf_score"],
        reverse=True,
    )


def rerank_by_learner_priority(results):
    """Apply the learner-priority reranking formula."""

    if not results:
        return []

    max_rrf_score = max(
        result["rrf_score"]
        for result in results
    )

    for result in results:
        metadata = result["metadata"]

        vocabulary_count = metadata.get("vocabulary_count", 0)
        top_frequency_count = metadata.get("top_frequency_count", 0)

        if vocabulary_count:
            learner_priority = (
                top_frequency_count / vocabulary_count
            )
        else:
            learner_priority = 0.0

        retrieval_score = result["rrf_score"] / max_rrf_score

        result["learner_priority"] = learner_priority

        result["final_score"] = (
            RETRIEVAL_WEIGHT * retrieval_score
            + LEARNER_PRIORITY_WEIGHT * learner_priority
        )

    return sorted(
        results,
        key=lambda item: (
            item["final_score"],
            item["rrf_score"],
        ),
        reverse=True,
    )


def retrieve_all_methods(query):
    """Run a query through all four retrieval methods."""

    dense_results = search_kanji_documents(
        query,
        limit=TOP_K,
    )

    bm25_results = search_kanji_bm25(
        query,
        limit=TOP_K,
    )

    dense_candidates = search_kanji_documents(
        query,
        limit=CANDIDATE_LIMIT,
    )

    bm25_candidates = search_kanji_bm25(
        query,
        limit=CANDIDATE_LIMIT,
    )

    rrf_results = calculate_rrf(
        dense_candidates,
        bm25_candidates,
    )

    reranked_results = rerank_by_learner_priority(
        [dict(result) for result in rrf_results]
    )

    return {
        "Dense": dense_results[:TOP_K],
        "BM25": bm25_results[:TOP_K],
        "RRF": rrf_results[:TOP_K],
        "RRF + Reranking": reranked_results[:TOP_K],
    }


def evaluate_method(results_by_query, queries):
    """Calculate Top-1, Top-3 and MRR metrics."""

    top1_correct = 0
    top3_correct = 0
    reciprocal_rank_sum = 0.0

    for query, results in zip(queries, results_by_query):
        expected = set(query["expected_kanji"])

        ranked_characters = [
            get_character(result)
            for result in results
        ]

        matching_ranks = [
            rank
            for rank, character in enumerate(
                ranked_characters,
                start=1,
            )
            if character in expected
        ]

        if matching_ranks:
            best_rank = min(matching_ranks)

            reciprocal_rank_sum += 1 / best_rank

            if best_rank == 1:
                top1_correct += 1

            if best_rank <= 3:
                top3_correct += 1

    total = len(queries)

    return {
        "Top-1 Accuracy": top1_correct / total,
        "Top-3 Accuracy": top3_correct / total,
        "MRR": reciprocal_rank_sum / total,
    }


def main():
    print("Loading evaluation dataset...")

    queries = load_queries()

    print("Total evaluation queries:", len(queries))

    methods = {
        "Dense": [],
        "BM25": [],
        "RRF": [],
        "RRF + Reranking": [],
    }

    detailed_results = []

    for index, item in enumerate(queries, start=1):
        query = item["query"]
        expected = item["expected_kanji"]

        print(f"\nEvaluating {index}/{len(queries)}: {query}")

        results = retrieve_all_methods(query)

        for method, method_results in results.items():
            methods[method].append(method_results)

        detailed_results.append({
            "query": query,
            "expected": expected,
            "results": {
                method: [
                    get_character(result)
                    for result in method_results
                ]
                for method, method_results in results.items()
            },
        })

    print("\n" + "=" * 75)
    print("RETRIEVAL EVALUATION REPORT")
    print("=" * 75)

    print(
        f"{'Method':<22}"
        f"{'Top-1':>12}"
        f"{'Top-3':>12}"
        f"{'MRR':>12}"
    )

    print("-" * 58)

    for method, results in methods.items():
        metrics = evaluate_method(results, queries)

        print(
            f"{method:<22}"
            f"{metrics['Top-1 Accuracy']:>11.2%}"
            f"{metrics['Top-3 Accuracy']:>11.2%}"
            f"{metrics['MRR']:>12.4f}"
        )

    print("\n" + "=" * 75)
    print("QUERY-LEVEL RESULTS")
    print("=" * 75)

    for item in detailed_results:
        print(f"\nQuery: {item['query']}")
        print(f"Expected: {', '.join(item['expected'])}")

        for method, characters in item["results"].items():
            print(f"{method:<20}: {' '.join(characters)}")


if __name__ == "__main__":
    main()
