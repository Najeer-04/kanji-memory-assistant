
from backend.services.vocabulary_service import search_vocabulary

results = search_vocabulary("学")

print(f"Found {len(results)} vocabulary entries.")

for entry in results[:10]:
    print("\nWritten forms:", entry["written_forms"])
    print("Readings:", entry["readings"])
    print("Meanings:", entry["meanings"][:3])
