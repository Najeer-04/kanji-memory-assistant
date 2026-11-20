
import re

from rank_bm25 import BM25Okapi

from backend.services.vector_store_service import collection


# --------------------------------------------------
# Configuration
# --------------------------------------------------

STOPWORDS = {
    "a", "an", "and", "are", "as", "at",
    "be", "by", "for", "from", "how",
    "in", "into", "is", "it", "of", "on",
    "or", "the", "this", "to", "what",
    "which", "with",
}

IRREGULAR_FORMS = {
    "studying": "study",
    "studies": "study",
    "studied": "study",
    "learning": "learn",
    "learned": "learn",
    "learnt": "learn",
    "eating": "eat",
    "drinking": "drink",
}


# --------------------------------------------------
# Tokenization
# --------------------------------------------------

def normalize_token(token: str) -> str:
    """Normalize basic English word variations."""

    token = token.lower()

    if token in IRREGULAR_FORMS:
        return IRREGULAR_FORMS[token]

    if len(token) > 5 and token.endswith("ing"):
        token = token[:-3]

    elif len(token) > 4 and token.endswith("ies"):
        token = token[:-3] + "y"

    elif len(token) > 4 and token.endswith("ed"):
        token = token[:-2]

    elif len(token) > 3 and token.endswith("s"):
        if not token.endswith("ss"):
            token = token[:-1]

    return token


def tokenize(text: str) -> list[str]:
    """
    Split English and Japanese text into searchable tokens.

    English words are normalized.
    Japanese character sequences are preserved.
    """

    tokens = re.findall(
        r"[a-zA-Z]+|[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]+",
        text.lower(),
    )

    processed_tokens = []

    for token in tokens:

        # Normalize English words.
        if re.fullmatch(r"[a-z]+", token):
            token = normalize_token(token)

            if token in STOPWORDS or len(token) <= 1:
                continue

        processed_tokens.append(token)

    return processed_tokens


# --------------------------------------------------
# BM25 index
# --------------------------------------------------

_bm25_index = None
_indexed_documents = []
_indexed_metadatas = []
_indexed_ids = []


def build_bm25_index():
    """
    Load all ChromaDB documents and build a BM25 index.

    This happens once when the index is first needed.
    """

    global _bm25_index
    global _indexed_documents
    global _indexed_metadatas
    global _indexed_ids

    print("Loading documents from ChromaDB for BM25...")

    result = collection.get(
        include=[
            "documents",
            "metadatas",
        ]
    )

    documents = result["documents"] or []
    metadatas = result["metadatas"] or []
    ids = result["ids"] or []

    if not documents:
        print("No documents available for BM25.")
        return

    tokenized_documents = [
        tokenize(document)
        for document in documents
    ]

    _bm25_index = BM25Okapi(tokenized_documents)

    _indexed_documents = documents
    _indexed_metadatas = metadatas
    _indexed_ids = ids

    print("BM25 index created successfully.")
    print("Indexed documents:", len(documents))


# --------------------------------------------------
# BM25 retrieval
# --------------------------------------------------

def search_kanji_bm25(
    query: str,
    limit: int = 5,
) -> list[dict]:
    """
    Retrieve kanji documents using BM25 keyword relevance.
    """

    global _bm25_index

    if _bm25_index is None:
        build_bm25_index()

    if _bm25_index is None:
        return []

    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    scores = _bm25_index.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )

    results = []

    for index in ranked_indices:

        score = float(scores[index])

        # Ignore documents with no keyword relevance.
        if score <= 0:
            continue

        results.append({
            "id": _indexed_ids[index],
            "document": _indexed_documents[index],
            "metadata": _indexed_metadatas[index],
            "score": score,
            "retrieval_type": "bm25",
        })

        if len(results) >= limit:
            break

    return results


# --------------------------------------------------
# Index refresh
# --------------------------------------------------

def refresh_bm25_index():
    """
    Rebuild the BM25 index after ChromaDB documents change.
    """

    global _bm25_index

    _bm25_index = None

    build_bm25_index()
