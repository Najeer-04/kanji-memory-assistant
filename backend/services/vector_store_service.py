
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from backend.services.knowledge_document_service import build_kanji_document


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_PATH = PROJECT_ROOT / "backend" / "data" / "chroma"

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


# --------------------------------------------------
# Initialize embedding model and ChromaDB
# --------------------------------------------------

embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

client = chromadb.PersistentClient(
    path=str(CHROMA_PATH)
)

collection = client.get_or_create_collection(
    name="kanji_documents",
    metadata={"hnsw:space": "cosine"}
)


# --------------------------------------------------
# Ingestion
# --------------------------------------------------

def store_kanji_document(kanji: dict, vocabulary: list[dict]):
    """Build, embed, and store a kanji knowledge document."""

    character = kanji["character"]

    document = build_kanji_document(kanji, vocabulary)

    embedding = embedding_model.encode(document).tolist()

    collection.upsert(
        ids=[f"kanji_{character}"],
        documents=[document],
        embeddings=[embedding],
        metadatas=[
            {
                "character": character,
                "type": "kanji",
            }
        ],
    )

    return {
        "character": character,
        "document": document,
        "collection_count": collection.count(),
    }


# --------------------------------------------------
# Exact retrieval
# --------------------------------------------------

def get_kanji_document(character: str) -> dict | None:
    """
    Retrieve the exact document for a kanji using its ChromaDB ID.

    Unlike semantic search, this does not calculate embedding similarity.
    """

    document_id = f"kanji_{character}"

    result = collection.get(
        ids=[document_id],
        include=[
            "documents",
            "metadatas",
        ],
    )

    if not result["ids"]:
        return None

    return {
        "document": result["documents"][0],
        "metadata": result["metadatas"][0],
        "id": result["ids"][0],
        "retrieval_type": "exact",
    }


# --------------------------------------------------
# Semantic retrieval
# --------------------------------------------------

def search_kanji_documents(
    query: str,
    limit: int = 3,
) -> list[dict]:
    """Retrieve semantically relevant documents from ChromaDB."""

    total_documents = collection.count()

    if total_documents == 0:
        return []

    query_embedding = embedding_model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(limit, total_documents),
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    retrieved_documents = []

    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        retrieved_documents.append({
            "document": document,
            "metadata": metadata,
            "distance": distance,
            "retrieval_type": "semantic",
        })

    return retrieved_documents
