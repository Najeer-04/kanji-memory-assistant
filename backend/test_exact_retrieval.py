from backend.services.vector_store_service import get_kanji_document


test_kanji = ["休", "学", "食", "水", "輝"]

for character in test_kanji:

    print("\n" + "=" * 50)
    print("Testing kanji:", character)

    result = get_kanji_document(character)

    if result is None:
        print("Document not found!")
        continue

    print("Document ID:", result["id"])
    print("Metadata:", result["metadata"])
    print("Retrieval type:", result["retrieval_type"])
    print("\nDocument:")
    print(result["document"][:500])
