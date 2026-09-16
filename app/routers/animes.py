from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import anilist, crud, schemas
from app.database import get_db

router = APIRouter(prefix="/animes", tags=["animes"])


@router.post("/search", response_model=list[schemas.AnimeSearchResult])
def search_animes(payload: schemas.AnimeSearchRequest):
    try:
        return anilist.search_anime(payload.query)
    except anilist.AniListError as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao consultar AniList: {exc}")


@router.post("", response_model=schemas.AnimePerfilOut, status_code=201)
def criar_anime(payload: schemas.AnimeCreate, db: Session = Depends(get_db)):
    if crud.get_anime_by_anilist_id(db, payload.anilist_id):
        raise HTTPException(status_code=409, detail="Anime já cadastrado")

    try:
        detalhe = anilist.get_anime_detail(payload.anilist_id)
    except anilist.AniListError as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao consultar AniList: {exc}")

    anime_criado = crud.create_anime(
        db,
        payload,
        titulo=detalhe["titulo"],
        tags_anilist=detalhe["tags_anilist"],
        sinopse=detalhe["descricao"],
    )
    crud.remover_do_catalogo_se_existir(db, payload.anilist_id)
    return anime_criado


@router.get("", response_model=list[schemas.AnimePerfilOut])
def listar_animes(db: Session = Depends(get_db)):
    return crud.get_animes(db)


@router.get("/{anime_id}", response_model=schemas.AnimePerfilOut)
def obter_anime(anime_id: int, db: Session = Depends(get_db)):
    db_anime = crud.get_anime(db, anime_id)
    if not db_anime:
        raise HTTPException(status_code=404, detail="Anime não encontrado")
    return db_anime


@router.patch("/{anime_id}", response_model=schemas.AnimePerfilOut)
def atualizar_anime(
    anime_id: int, payload: schemas.AnimeUpdate, db: Session = Depends(get_db)
):
    db_anime = crud.get_anime(db, anime_id)
    if not db_anime:
        raise HTTPException(status_code=404, detail="Anime não encontrado")
    return crud.update_anime(db, db_anime, payload)


@router.delete("/{anime_id}", status_code=204)
def deletar_anime(anime_id: int, db: Session = Depends(get_db)):
    db_anime = crud.get_anime(db, anime_id)
    if not db_anime:
        raise HTTPException(status_code=404, detail="Anime não encontrado")
    crud.delete_anime(db, db_anime)
