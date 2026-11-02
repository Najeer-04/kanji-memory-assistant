
import chromadb
from sentence_transformers import SentenceTransformer

# 1. Load the embedding model
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# 2. Create a persistent ChromaDB client
client = chromadb.PersistentClient(
    path="backend/data/chroma"
)

# 3. Create or retrieve the collection
collection = client.get_or_create_collection(
    name="kanji_knowledge",
    metadata={"hnsw:space": "cosine"}
)

# 4. Prepare sample documents
documents = [
    "休 means rest. Related vocabulary: 休む (to rest), 休日 (holiday).",
    "明 means bright or clear. Related vocabulary: 明るい (bright).",
    "食 means eat or food. Related vocabulary: 食べる (to eat), 食事 (meal).",
]

ids = ["kanji_休", "kanji_明", "kanji_食"]

# 5. Generate embeddings
embeddings = model.encode(documents).tolist()

# 6. Insert or update documents
collection.upsert(
    ids=ids,
    documents=documents,
    embeddings=embeddings
)

# 7. Search
query = "休むことや休憩について"
query_embedding = model.encode([query]).tolist()

results = collection.query(
    query_embeddings=query_embedding,
    n_results=2
)

# 8. Display results
for document, distance in zip(
    results["documents"][0],
    results["distances"][0]
):
    print(f"Document: {document}")
    print(f"Distance: {distance:.4f}")
    print("-" * 50)

print(f"Total documents in collection: {collection.count()}")
