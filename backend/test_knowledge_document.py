
from backend.services.kanji_service import search_kanji
from backend.services.vocabulary_service import search_vocabulary
from backend.services.knowledge_document_service import build_kanji_document

character = "休"

kanji = search_kanji(character)
vocabulary = search_vocabulary(character, limit=5)

document = build_kanji_document(kanji, vocabulary)

print(document)
