from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import animes, catalogo, embeddings, recomendacao

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Recomendação Pessoal")

app.include_router(animes.router)
app.include_router(catalogo.router)
app.include_router(embeddings.router)
app.include_router(recomendacao.router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def frontend():
    return FileResponse(STATIC_DIR / "index.html")
