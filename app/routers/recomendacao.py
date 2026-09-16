from fastapi import APIRouter, Depends, HTTPException
from google.genai import errors as genai_errors
from sqlalchemy.orm import Session

from app import crud, embeddings, llm, models, schemas
from app.database import get_db
from app.crud import STATUS_COM_OPINIAO_FORMADA

router = APIRouter(prefix="/recomendacao", tags=["recomendacao"])


def _perfil_com_embedding(db: Session) -> list[models.AnimePerfil]:
    perfil = (
        db.query(models.AnimePerfil)
        .filter(models.AnimePerfil.status.in_(STATUS_COM_OPINIAO_FORMADA))
        .filter(models.AnimePerfil.embedding.isnot(None))
        .all()
    )
    if not perfil:
        raise HTTPException(
            status_code=400,
            detail="Nenhum embedding calculado no perfil ainda — rode POST /embeddings/recalcular primeiro",
        )
    return perfil


def _catalogo_com_embedding(db: Session) -> list[models.AnimeCatalogo]:
    catalogo = db.query(models.AnimeCatalogo).filter(models.AnimeCatalogo.embedding.isnot(None)).all()
    if not catalogo:
        raise HTTPException(
            status_code=400,
            detail="Catálogo sem embeddings ainda — rode POST /embeddings/recalcular primeiro",
        )
    return catalogo


def _vetor_de_gosto(perfil: list[models.AnimePerfil]) -> list[float]:
    return embeddings.vetor_de_gosto([(anime.embedding, crud.peso_por_nota(anime.nota)) for anime in perfil])


@router.get("/candidatos", response_model=list[schemas.CandidatoOut])
def candidatos_recomendados(top_n: int = 20, db: Session = Depends(get_db)):
    perfil = _perfil_com_embedding(db)
    vetor_gosto = _vetor_de_gosto(perfil)
    catalogo = _catalogo_com_embedding(db)

    ranqueados = sorted(
        (
            (item, embeddings.similaridade_cosseno(vetor_gosto, item.embedding))
            for item in catalogo
        ),
        key=lambda par: par[1],
        reverse=True,
    )[:top_n]

    return [
        schemas.CandidatoOut(
            id=item.id,
            anilist_id=item.anilist_id,
            titulo=item.titulo,
            sinopse=item.sinopse,
            tags_anilist=item.tags_anilist,
            popularidade=item.popularidade,
            nota_media=item.nota_media,
            formato=item.formato,
            ano=item.ano,
            similaridade=round(similaridade, 4),
        )
        for item, similaridade in ranqueados
    ]


@router.post("/pedido", response_model=schemas.RespostaRecomendacao)
def pedido_recomendacao(
    payload: schemas.PedidoRecomendacao,
    pool_afinidade: int = 1000,
    pool_llm: int = 20,
    db: Session = Depends(get_db),
):
    """Fase 4 — filtro em dois estágios + rerank contextual via LLM:
    1) restringe o catálogo aos `pool_afinidade` mais próximos do gosto geral do usuário
       (default bem folgado — hoje o catálogo tem ~350 itens, então isso não corta nada
       de fato; cosine similarity local é barato, então não custa manter o pool grande
       e deixar o corte real acontecer só no estágio 2, pela relevância ao pedido);
    2) dentro desse pool, reordena pela relevância semântica ao pedido específico;
    3) manda os `pool_llm` melhores pro LLM escolher e justificar, com o gosto geral como contexto.
    """
    perfil = _perfil_com_embedding(db)
    vetor_gosto = _vetor_de_gosto(perfil)
    catalogo = _catalogo_com_embedding(db)

    por_afinidade = sorted(
        catalogo,
        key=lambda item: embeddings.similaridade_cosseno(vetor_gosto, item.embedding),
        reverse=True,
    )[:pool_afinidade]

    embedding_pedido = embeddings.calcular_embedding(payload.mensagem)
    candidatos_llm = sorted(
        por_afinidade,
        key=lambda item: embeddings.similaridade_cosseno(embedding_pedido, item.embedding),
        reverse=True,
    )[:pool_llm]

    resumo_perfil = crud.montar_resumo_perfil(db)
    candidatos_dict = [
        {
            "anilist_id": item.anilist_id,
            "titulo": item.titulo,
            "sinopse": item.sinopse,
            "tags_anilist": item.tags_anilist,
            "ano": item.ano,
            "formato": item.formato,
        }
        for item in candidatos_llm
    ]

    try:
        resposta = llm.recomendar(resumo_perfil, candidatos_dict, payload.mensagem, top_n=payload.top_n)
    except genai_errors.APIError as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao consultar o modelo: {exc.message}")

    # defesa contra alucinação: descarta qualquer item que o LLM tenha
    # inventado fora da lista de candidatos que ele recebeu
    ids_validos = {item.anilist_id for item in candidatos_llm}
    resposta.itens = [item for item in resposta.itens if item.anilist_id in ids_validos]
    return resposta
