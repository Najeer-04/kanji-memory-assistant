
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.services.kanji_service import search_kanji
from backend.services.vocabulary_service import search_vocabulary

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
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
            detail=f"Kanji '{character}' not found"
        )

    return result


@app.get("/kanji/{character}/vocabulary")
def get_kanji_vocabulary(character: str, limit: int = 20):
    if len(character) != 1:
        raise HTTPException(
            status_code=400,
            detail="Please provide exactly one character."
        )

    if not 1 <= limit <= 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100."
        )

    return search_vocabulary(character, limit)
