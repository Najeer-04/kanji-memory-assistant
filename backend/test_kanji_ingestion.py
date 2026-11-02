
from backend.services.kanji_service import get_all_kanji

kanji_list = get_all_kanji()

print("Total kanji:", len(kanji_list))

print("\nFirst 3 records:")

for kanji in kanji_list[:3]:
    print(kanji)
