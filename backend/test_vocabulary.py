from backend.services.vocabulary_service import search_vocabulary

results = search_vocabulary("休", limit=5)

for word in results:
    print(word)