import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import anilist, embeddings, models, schemas
from app.database import get_db

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("/recalcular", response_model=schemas.RecalculoEmbeddingsOut)
def recalcular_embeddings(
    force: bool = Query(False, description="Recalcula mesmo quem já tem embedding"),
    db: Session = Depends(get_db),
):
    perfil_atualizados = 0
    perfil_refeitos_da_anilist = 0

    for anime in db.query(models.AnimePerfil).all():
        if anime.sinopse is None:
            # registro antigo, de antes da sinopse ser salva — precisa buscar de novo
            try:
                detalhe = anilist.get_anime_detail(anime.anilist_id)
            except anilist.AniListError:
                continue
            anime.tags_anilist = detalhe["tags_anilist"]
            anime.sinopse = detalhe["descricao"]
            perfil_refeitos_da_anilist += 1
            time.sleep(1.2)
        elif not force and anime.embedding is not None:
            continue

        texto = embeddings.montar_texto(anime.sinopse, anime.tags_anilist)
        anime.embedding = embeddings.calcular_embedding(texto)
        perfil_atualizados += 1
        db.commit()

    catalogo_atualizados = 0
    for item in db.query(models.AnimeCatalogo).all():
        if not force and item.embedding is not None:
            continue
        texto = embeddings.montar_texto(item.sinopse, item.tags_anilist)
        item.embedding = embeddings.calcular_embedding(texto)
        catalogo_atualizados += 1
    db.commit()

    return schemas.RecalculoEmbeddingsOut(
        perfil_atualizados=perfil_atualizados,
        perfil_refeitos_da_anilist=perfil_refeitos_da_anilist,
        catalogo_atualizados=catalogo_atualizados,
    )
