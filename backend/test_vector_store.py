
from backend.services.kanji_service import search_kanji
from backend.services.vocabulary_service import search_vocabulary
from backend.services.vector_store_service import store_kanji_document

character = "休"

# Retrieve data from PostgreSQL
kanji = search_kanji(character)
vocabulary = search_vocabulary(character, limit=5)

# Store in ChromaDB
result = store_kanji_document(kanji, vocabulary)

print("Successfully stored:", result["character"])
print("Total documents:", result["collection_count"])
