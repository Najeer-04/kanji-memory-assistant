
from backend.services.vector_store_service import get_kanji_document


character = "休"

result = get_kanji_document(character)

if result is None:
    print("Kanji document not found.")
else:
    print("Target kanji:", character)
    print("Retrieved ID:", result["id"])
    print("Retrieval type:", result["retrieval_type"])

    print("\nContext passed to the LLM:")
    print(result["document"])
