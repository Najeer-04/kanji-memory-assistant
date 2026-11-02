
from backend.services.vector_store_service import search_kanji_documents


queries = [
    "Which kanji means resting or taking a break?",
    "Which kanji is associated with eating food?",
    "Which kanji represents studying and learning?",
    "Which kanji means bright or shining?",
    "Which kanji is associated with drinking water?",
]


for query in queries:
    print("\n" + "=" * 60)
    print("QUERY:", query)

    results = search_kanji_documents(query, limit=3)

    for index, result in enumerate(results, start=1):
        print(f"\nResult {index}")
        print("Kanji:", result["metadata"]["character"])
        print("Distance:", result["distance"])
        print("Document preview:", result["document"][:300])
