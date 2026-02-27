from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Project Management MVP API")

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@app.get("/api/hello")
def hello() -> dict[str, str]:
    return {"message": "hello from fastapi"}


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
