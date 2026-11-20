
import json
import re
import urllib.error
import urllib.request

from backend.services.vocabulary_service import search_vocabulary
from backend.services.example_service import search_examples
from backend.services.vector_store_service import get_kanji_document


# --------------------------------------------------
# Configuration
# --------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_TIMEOUT = 120

VOCABULARY_LIMIT = 5
EXAMPLES_PER_WORD = 1

TEMPERATURE = 0.4


# --------------------------------------------------
# English text processing
# --------------------------------------------------

STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for",
    "from", "in", "into", "of", "on", "or",
    "the", "to", "with", "one", "esp",
    "especially", "someone", "something",
}


def normalize_word(word: str) -> str:
    word = word.lower().strip()

    irregular_forms = {
        "learning": "learn",
        "learned": "learn",
        "learnt": "learn",
        "studying": "study",
        "studies": "study",
        "studied": "study",
        "sciences": "science",
        "educational": "education",
    }

    if word in irregular_forms:
        return irregular_forms[word]

    if len(word) > 5 and word.endswith("ing"):
        word = word[:-3]

    elif len(word) > 4 and word.endswith("ies"):
        word = word[:-3] + "y"

    elif len(word) > 4 and word.endswith("ed"):
        word = word[:-2]

    elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]

    return word


def extract_terms(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())

    return {
        normalize_word(word)
        for word in words
        if word not in STOPWORDS and len(word) > 2
    }


# --------------------------------------------------
# PostgreSQL retrieval
# --------------------------------------------------

def retrieve_kanji_context(character: str) -> dict:
    """Retrieve vocabulary and example sentences from PostgreSQL."""

    vocabulary = search_vocabulary(
        character,
        limit=VOCABULARY_LIMIT,
    )

    retrieved_words = []

    for word in vocabulary:

        examples = search_examples(
            word["written_forms"],
            limit=EXAMPLES_PER_WORD,
        )

        retrieved_words.append({
            "written_forms": word["written_forms"],
            "readings": word["readings"],
            "meanings": word["meanings"],
            "priority_tags": word["priority_tags"],
            "frequency_rank": word["frequency_rank"],
            "examples": examples[:EXAMPLES_PER_WORD],
        })

    return {
        "vocabulary": retrieved_words,
        "vocabulary_count": len(retrieved_words),
        "example_count": sum(
            len(word["examples"])
            for word in retrieved_words
        ),
    }


# --------------------------------------------------
# Exact ChromaDB retrieval
# --------------------------------------------------

def retrieve_rag_context(character: str) -> dict | None:
    """
    Retrieve the exact knowledge document for the target kanji.

    This avoids accidentally providing documents belonging
    to other kanji during mnemonic generation.
    """

    return get_kanji_document(character)


# --------------------------------------------------
# Vocabulary anchor selection
# --------------------------------------------------

def select_vocabulary_anchor(
    vocabulary: list[dict],
    kanji_meanings: list[str],
) -> dict | None:

    if not vocabulary:
        return None

    kanji_terms = set()

    for meaning in kanji_meanings:
        kanji_terms.update(extract_terms(meaning))

    if not kanji_terms:
        return next(
            (
                word for word in vocabulary
                if word.get("meanings") and word.get("written_forms")
            ),
            None,
        )

    best_word = None
    best_score = float("-inf")

    for word in vocabulary:

        meanings = word.get("meanings", [])
        written_forms = word.get("written_forms", [])

        if not meanings or not written_forms:
            continue

        all_meaning_terms = set()

        for meaning in meanings:
            all_meaning_terms.update(extract_terms(meaning))

        overlap = kanji_terms & all_meaning_terms

        if not overlap:
            continue

        score = len(overlap) * 4.0

        first_meaning_terms = extract_terms(meanings[0])

        if kanji_terms & first_meaning_terms:
            score += 0.15

        frequency_rank = word.get("frequency_rank")

        if isinstance(frequency_rank, (int, float)) and frequency_rank > 0:
            score += 0.5 / (1.0 + frequency_rank / 1000.0)

        primary_text = " ".join(meanings[:3])
        score -= len(primary_text) * 0.0005

        if score > best_score:
            best_score = score
            best_word = word

    if best_word is None:
        return next(
            (
                word for word in vocabulary
                if word.get("meanings") and word.get("written_forms")
            ),
            None,
        )

    return best_word


# --------------------------------------------------
# Relevant definition selection
# --------------------------------------------------

def select_relevant_definition(
    kanji_meanings: list[str],
    vocabulary_meanings: list[str],
) -> str | None:

    if not kanji_meanings or not vocabulary_meanings:
        return None

    weighted_kanji_terms = {}

    for index, meaning in enumerate(kanji_meanings):

        terms = extract_terms(meaning)

        if not terms:
            continue

        weight = max(1, 5 - index)
        term_weight = weight / len(terms)

        for term in terms:
            weighted_kanji_terms[term] = max(
                weighted_kanji_terms.get(term, 0),
                term_weight,
            )

    if not weighted_kanji_terms:
        return vocabulary_meanings[0]

    best_definition = None
    best_score = float("-inf")

    for definition in vocabulary_meanings:

        definition_terms = extract_terms(definition)

        overlap = set(weighted_kanji_terms) & definition_terms

        if not overlap:
            continue

        score = sum(
            weighted_kanji_terms[term]
            for term in overlap
        )

        score -= len(definition) * 0.001

        if score > best_score:
            best_score = score
            best_definition = definition

    return best_definition or vocabulary_meanings[0]


# --------------------------------------------------
# Ollama API
# --------------------------------------------------

def call_ollama(prompt: str, schema: dict) -> dict:

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a concise Japanese learning assistant. "
                    "Create simple, memorable visual mnemonics. "
                    "Follow verified facts. Never invent historical "
                    "origins or meanings. Avoid unnecessary details. "
                    "Return all requested JSON fields."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "format": schema,
        "options": {
            "temperature": TEMPERATURE,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=OLLAMA_TIMEOUT,
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    content = result["message"]["content"]

    print("Ollama raw response:", repr(content))

    parsed = json.loads(content)

    if not isinstance(parsed, dict):
        raise ValueError(
            "Ollama did not return a JSON object."
        )

    return parsed


# --------------------------------------------------
# Prompt construction
# --------------------------------------------------

def build_prompt(
    character: str,
    meanings: list[str],
    retrieved_context: dict,
) -> str:

    context_text = retrieved_context["document"]

    return f"""
Create a memorable visual mnemonic for a Japanese kanji.

VERIFIED INFORMATION FROM KANJIDIC2

Kanji: {character}
Meanings: {json.dumps(meanings, ensure_ascii=False)}

EXACT RETRIEVED KNOWLEDGE FROM CHROMADB

{context_text}

TASK: VISUAL MNEMONIC

Create ONE simple visual scene that helps the learner
remember the kanji's primary meaning.

The retrieved document belongs to the exact target kanji.
Use its readings and vocabulary as supporting context.

RULES:

1. Choose the most important verified meaning.
2. Use no more than TWO main objects or characters.
3. Give the main subject ONE clear action.
4. Connect the action directly to the meaning.
5. Prefer familiar everyday objects, people, or animals.
6. Use visible kanji components when they genuinely help.
7. Make the scene easy to picture and remember.
8. Use only 1-2 sentences.
9. Avoid complicated fantasy stories.
10. Never invent historical explanations or etymology.
11. Do not invent component meanings that are not supported
    by the retrieved knowledge.

IMPORTANT:

Do not add unrelated objects, signs, decorations,
or random jokes just to make the scene entertaining.

Every element in the scene must help the learner
remember the kanji's meaning.

A simple, meaningful visual scene is better
than an elaborate story.

OUTPUT FORMAT:

Return valid JSON containing exactly this field:

- mnemonic

Use simple English.
"""


# --------------------------------------------------
# Validation
# --------------------------------------------------

def validate_mnemonic(mnemonic: str) -> str:

    if not isinstance(mnemonic, str) or not mnemonic.strip():
        raise ValueError(
            "The model failed to generate a valid mnemonic."
        )

    return mnemonic.strip()


# --------------------------------------------------
# Vocabulary connection
# --------------------------------------------------

def build_vocabulary_connection(
    character: str,
    kanji_meanings: list[str],
    anchor: dict | None,
) -> str:

    if not anchor:
        return (
            "No suitable vocabulary anchor was found "
            "in the retrieved records."
        )

    written_forms = anchor.get("written_forms", [])
    readings = anchor.get("readings", [])
    anchor_meanings = anchor.get("meanings", [])

    if not written_forms or not readings or not anchor_meanings:
        return (
            "A vocabulary entry was retrieved, but it does not "
            "contain enough information to build an explanation."
        )

    anchor_word = written_forms[0]
    anchor_reading = readings[0]

    relevant_definition = select_relevant_definition(
        kanji_meanings,
        anchor_meanings,
    )

    if not relevant_definition:
        relevant_definition = anchor_meanings[0]

    return (
        f"{anchor_word} ({anchor_reading}) means "
        f"'{relevant_definition}'. This word contains {character} "
        f"and reinforces its meaning: {', '.join(kanji_meanings)}."
    )


# --------------------------------------------------
# Main mnemonic generation function
# --------------------------------------------------

def generate_mnemonic(
    character: str,
    meanings: list[str],
    on_readings: list[str],
    kun_readings: list[str],
) -> dict:

    # 1. Retrieve vocabulary and examples from PostgreSQL.
    context = retrieve_kanji_context(character)
    vocabulary = context["vocabulary"]

    # 2. Retrieve the exact target document from ChromaDB.
    rag_context = retrieve_rag_context(character)

    if rag_context is None:
        raise RuntimeError(
            f"No ChromaDB knowledge document found for {character}. "
            "Run the kanji ingestion script first."
        )

    # 3. Select a verified reading.
    valid_readings = on_readings + kun_readings

    if not valid_readings:
        raise RuntimeError(
            f"No verified readings are available for {character}."
        )

    selected_reading = (
        on_readings[0] if on_readings else kun_readings[0]
    )

    # 4. Select vocabulary anchor.
    anchor = select_vocabulary_anchor(
        vocabulary,
        meanings,
    )

    # 5. Build prompt using exact retrieved context.
    prompt = build_prompt(
        character=character,
        meanings=meanings,
        retrieved_context=rag_context,
    )

    schema = {
        "type": "object",
        "properties": {
            "mnemonic": {
                "type": "string",
            },
        },
        "required": ["mnemonic"],
    }

    try:

        # 6. Generate mnemonic using retrieved context.
        generated = call_ollama(
            prompt,
            schema,
        )

        # 7. Validate mnemonic.
        mnemonic = validate_mnemonic(
            generated.get("mnemonic")
        )

        # 8. Build vocabulary connection.
        vocabulary_connection = build_vocabulary_connection(
            character=character,
            kanji_meanings=meanings,
            anchor=anchor,
        )

        # 9. Return final response.
        return {
            "character": character,
            "mnemonic": mnemonic,
            "reading_used": selected_reading,
            "vocabulary_connection": vocabulary_connection,
            "vocabulary_anchor": anchor,
            "retrieval": {
                "vocabulary_count": context["vocabulary_count"],
                "example_count": context["example_count"],
                "vocabulary": vocabulary,
            },
            "rag_retrieval": {
                "document_count": 1,
                "documents": [rag_context],
                "retrieval_type": "exact",
            },
            "model": OLLAMA_MODEL,
        }

    except (
        urllib.error.URLError,
        TimeoutError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:

        raise RuntimeError(
            f"Could not generate a mnemonic with Ollama: {error}"
        ) from error
