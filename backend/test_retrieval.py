
from backend.services.vector_store_service import (
    collection,
    embedding_model
)

# Natural-language query
query = "Which kanji is associated with resting and taking breaks?"

# Convert query into an embedding
query_embedding = embedding_model.encode(query).tolist()

# Search ChromaDB
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=1
)

# Display retrieved information
for document, metadata, distance in zip(
    results["documents"][0],
    results["metadatas"][0],
    results["distances"][0]
):
    print("Retrieved kanji:", metadata["character"])
    print("Distance:", round(distance, 4))
    print("\nRetrieved document:\n")
    print(document)
