
import re

from backend.services.kanji_service import get_all_kanji
from backend.services.vocabulary_service import get_all_vocabulary


def get_priority_score(priority_tags):
    """
    Return a sorting key based on JMdict priority tags.
    Lower sorting keys mean higher priority.
    """
    priority_order = {
        "ichi1": 0,
        "ichi2": 1,
        "news1": 2,
        "news2": 3,
    }

    best_priority = min(
        (
            priority_order[tag]
            for tag in priority_tags
            if tag in priority_order
        ),
        default=4,
    )

    nf_tags = [
        int(match.group(1))
        for tag in priority_tags
        if (match := re.fullmatch(r"nf(\d{2})", tag))
    ]

    nf_rank = min(nf_tags, default=999)

    return best_priority, nf_rank


def build_vocabulary_mapping(kanji_list, vocabulary_list):
    vocabulary_by_kanji = {
        item["character"]: {}
        for item in kanji_list
    }

    kanji_characters = set(vocabulary_by_kanji)

    for word in vocabulary_list:
        written_forms = word.get("written_forms") or []
        matched_kanji = set()

        for form in written_forms:
            for character in form:
                if character in kanji_characters:
                    matched_kanji.add(character)

        for character in matched_kanji:
            vocabulary_by_kanji[character][word["entry_id"]] = word

    return vocabulary_by_kanji


def main():
    print("Loading kanji...")
    kanji_list = get_all_kanji()

    print("Loading vocabulary...")
    vocabulary_list = get_all_vocabulary()

    print("Building vocabulary mapping...")
    vocabulary_by_kanji = build_vocabulary_mapping(
        kanji_list,
        vocabulary_list,
    )

    target = "休"

    matched_words = list(
        vocabulary_by_kanji.get(target, {}).values()
    )

    matched_words.sort(
        key=lambda word: get_priority_score(
            word.get("priority_tags") or []
        )
    )

    print("\n========== RANKING TEST ==========")
    print("Target kanji:", target)
    print("Total associated vocabulary:", len(matched_words))

    print("\nTop 10 associated words:")

    for word in matched_words[:10]:
        print({
            "written_forms": word["written_forms"],
            "readings": word["readings"],
            "meanings": word["meanings"],
            "priority_tags": word["priority_tags"],
            "ranking_key": get_priority_score(
                word.get("priority_tags") or []
            ),
        })


if __name__ == "__main__":
    main()
