import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import anilist, crud, schemas
from app.database import get_db

router = APIRouter(prefix="/catalogo", tags=["catalogo"])


@router.post("/sync", response_model=schemas.SyncResultOut)
def sincronizar_catalogo(db: Session = Depends(get_db)):
    top_generos, top_tags = crud.calcular_generos_e_tags_favoritos(db)
    if not top_generos and not top_tags:
        raise HTTPException(
            status_code=400,
            detail="Cadastre alguns animes no perfil antes de sincronizar o catálogo",
        )

    excluir_ids = crud.get_ids_perfil(db) + crud.get_ids_catalogo(db)
    valores = [("genero", g) for g in top_generos] + [("tag", t) for t in top_tags]

    candidatos = []
    try:
        for i, (tipo, valor) in enumerate(valores):
            if i:
                time.sleep(1.3)
            if tipo == "genero":
                candidatos += anilist.buscar_candidatos(genero=valor, tag=None, excluir_ids=excluir_ids)
            else:
                candidatos += anilist.buscar_candidatos(genero=None, tag=valor, excluir_ids=excluir_ids)
    except anilist.AniListError as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao consultar AniList: {exc}")

    vistos: set[int] = set()
    novos = atualizados = 0
    for candidato in candidatos:
        if candidato["anilist_id"] in vistos:
            continue
        vistos.add(candidato["anilist_id"])
        _, criado = crud.upsert_catalogo(db, candidato)
        novos += int(criado)
        atualizados += int(not criado)

    return schemas.SyncResultOut(
        generos_usados=top_generos,
        tags_usadas=top_tags,
        candidatos_novos=novos,
        candidatos_atualizados=atualizados,
        total_no_catalogo=crud.count_catalogo(db),
    )


@router.get("", response_model=list[schemas.CatalogoOut])
def listar_catalogo(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    return crud.get_catalogo(db, limit=limit, offset=offset)


@router.get("/{item_id}", response_model=schemas.CatalogoOut)
def obter_item_catalogo(item_id: int, db: Session = Depends(get_db)):
    item = crud.get_catalogo_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado no catálogo")
    return item


@router.delete("/{item_id}", status_code=204)
def remover_item_catalogo(item_id: int, db: Session = Depends(get_db)):
    item = crud.get_catalogo_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado no catálogo")
    crud.delete_catalogo_item(db, item)
