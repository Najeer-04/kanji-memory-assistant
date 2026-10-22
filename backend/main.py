
from fastapi import FastAPI, HTTPException
from backend.services.kanji_service import search_kanji

app = FastAPI()


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
