from backend.services.vocabulary_service import get_all_vocabulary

vocabulary = get_all_vocabulary()

print("Total vocabulary:", len(vocabulary))

for word in vocabulary[:3]:
    print(word)