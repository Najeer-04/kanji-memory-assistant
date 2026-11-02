
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.services.kanji_service import search_kanji
from backend.services.vocabulary_service import search_vocabulary
from backend.services.example_service import search_examples
from backend.services.mnemonic_service import generate_mnemonic

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Kanji Memory Assistant API is running!"}


@app.get("/kanji/{character}")
def get_kanji(character: str):
    result = search_kanji(character)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Kanji '{character}' not found",
        )

    return result


@app.get("/kanji/{character}/vocabulary")
def get_kanji_vocabulary(character: str, limit: int = 20):
    if len(character) != 1:
        raise HTTPException(
            status_code=400,
            detail="Please provide exactly one character.",
        )

    if not 1 <= limit <= 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100.",
        )

    vocabulary = search_vocabulary(character, limit)

    for word in vocabulary:
        word["examples"] = search_examples(
            word["written_forms"],
            limit=2,
        )

    return vocabulary


@app.post("/kanji/{character}/mnemonic")
def get_kanji_mnemonic(character: str):
    if len(character) != 1:
        raise HTTPException(
            status_code=400,
            detail="Please provide exactly one kanji character.",
        )

    kanji = search_kanji(character)

    if kanji is None:
        raise HTTPException(
            status_code=404,
            detail=f"Kanji '{character}' not found",
        )

    try:
        return generate_mnemonic(
            character=kanji["character"],
            meanings=kanji["meanings"],
            on_readings=kanji["on_readings"],
            kun_readings=kanji["kun_readings"],
        )
    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error
