
from backend.services.bm25_service import (
    search_kanji_bm25,
    tokenize,
)


queries = [
    "Which kanji represents studying and learning?",
    "Which kanji means resting or taking a break?",
    "Which kanji is associated with eating food?",
    "Which kanji means bright or shining?",
    "Which kanji is associated with drinking water?",
]


print("Testing BM25 tokenization:")
print(tokenize("Which kanji represents studying and learning?"))


for query in queries:

    print("\n" + "=" * 60)
    print("QUERY:", query)

    results = search_kanji_bm25(
        query=query,
        limit=5,
    )

    if not results:
        print("No matching documents found.")
        continue

    for rank, result in enumerate(results, start=1):

        print(f"\nResult {rank}")
        print("Kanji:", result["metadata"]["character"])
        print("BM25 score:", round(result["score"], 4))
        print("Document preview:")
        print(result["document"][:250])
