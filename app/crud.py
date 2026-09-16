from collections import Counter

from sqlalchemy.orm import Session

from app import anilist, models, schemas


def get_animes(db: Session):
    return db.query(models.AnimePerfil).all()


def get_anime(db: Session, anime_id: int):
    return db.query(models.AnimePerfil).filter(models.AnimePerfil.id == anime_id).first()


def get_anime_by_anilist_id(db: Session, anilist_id: int):
    return (
        db.query(models.AnimePerfil)
        .filter(models.AnimePerfil.anilist_id == anilist_id)
        .first()
    )


def create_anime(
    db: Session, anime: schemas.AnimeCreate, titulo: str, tags_anilist: list[str], sinopse: str | None = None
) -> models.AnimePerfil:
    db_anime = models.AnimePerfil(
        anilist_id=anime.anilist_id,
        titulo=titulo,
        status=anime.status,
        nota=anime.nota,
        tags_anilist=tags_anilist,
        tags_proprias=anime.tags_proprias,
        sinopse=sinopse,
    )
    db.add(db_anime)
    db.commit()
    db.refresh(db_anime)
    return db_anime


def update_anime(
    db: Session, db_anime: models.AnimePerfil, updates: schemas.AnimeUpdate
) -> models.AnimePerfil:
    for campo, valor in updates.model_dump(exclude_unset=True).items():
        setattr(db_anime, campo, valor)
    db.commit()
    db.refresh(db_anime)
    return db_anime


def delete_anime(db: Session, db_anime: models.AnimePerfil) -> None:
    db.delete(db_anime)
    db.commit()


def remover_do_catalogo_se_existir(db: Session, anilist_id: int) -> None:
    item = db.query(models.AnimeCatalogo).filter_by(anilist_id=anilist_id).first()
    if item:
        db.delete(item)
        db.commit()


STATUS_COM_OPINIAO_FORMADA = ("assistido", "assistindo")


def peso_por_nota(nota: int | None) -> float:
    """Nota 10 pesa 4x, nota 7 ou menos (ou sem nota — ex: assistindo) pesa 1x.
    Único critério de peso do projeto — reusado tanto no top de gêneros/tags
    quanto no vetor de gosto da Fase 3, pra não ter dois critérios divergentes."""
    return 1 + max(0, (nota or 7) - 7)


def calcular_generos_e_tags_favoritos(db: Session, top_n: int = 8) -> tuple[list[str], list[str]]:
    """Pondera cada gênero/tag pela nota dos animes do perfil que o carregam
    e retorna os top_n de cada categoria — é isso que direciona a busca de
    candidatos na AniList. Só considera animes com opinião formada: 'dropado'
    não deve puxar o gosto pra um sentido que você na verdade rejeitou, e
    'quero_assistir' ainda não tem opinião nenhuma."""
    generos_contador: Counter[str] = Counter()
    tags_contador: Counter[str] = Counter()

    animes_relevantes = (
        db.query(models.AnimePerfil)
        .filter(models.AnimePerfil.status.in_(STATUS_COM_OPINIAO_FORMADA))
        .all()
    )
    for anime in animes_relevantes:
        peso = peso_por_nota(anime.nota)
        for tag in anime.tags_anilist or []:
            if tag in anilist.GENEROS_ANILIST:
                generos_contador[tag] += peso
            else:
                tags_contador[tag] += peso

    top_generos = [g for g, _ in generos_contador.most_common(top_n)]
    top_tags = [t for t, _ in tags_contador.most_common(top_n)]
    return top_generos, top_tags


def get_ids_perfil(db: Session) -> list[int]:
    return [row.anilist_id for row in db.query(models.AnimePerfil.anilist_id).all()]


def get_ids_catalogo(db: Session) -> list[int]:
    return [row.anilist_id for row in db.query(models.AnimeCatalogo.anilist_id).all()]


def upsert_catalogo(db: Session, candidato: dict) -> tuple[models.AnimeCatalogo, bool]:
    existente = db.query(models.AnimeCatalogo).filter_by(anilist_id=candidato["anilist_id"]).first()
    if existente:
        for campo in ("titulo", "sinopse", "tags_anilist", "popularidade", "nota_media", "formato", "ano"):
            setattr(existente, campo, candidato[campo])
        existente.embedding = None  # metadados mudaram, embedding antigo ficou obsoleto
        db.commit()
        db.refresh(existente)
        return existente, False

    novo = models.AnimeCatalogo(**candidato)
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo, True


def get_catalogo(db: Session, limit: int = 50, offset: int = 0):
    return (
        db.query(models.AnimeCatalogo)
        .order_by(models.AnimeCatalogo.popularidade.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_catalogo_item(db: Session, item_id: int):
    return db.query(models.AnimeCatalogo).filter(models.AnimeCatalogo.id == item_id).first()


def delete_catalogo_item(db: Session, item: models.AnimeCatalogo) -> None:
    db.delete(item)
    db.commit()


def count_catalogo(db: Session) -> int:
    return db.query(models.AnimeCatalogo).count()


def montar_resumo_perfil(db: Session, top_n_favoritos: int = 8) -> str:
    """Texto curto pra dar contexto ao LLM na Fase 4: não manda o perfil
    inteiro (100+ animes), só o suficiente pra ele calibrar a escolha."""
    top_generos, top_tags = calcular_generos_e_tags_favoritos(db)

    favoritos = (
        db.query(models.AnimePerfil)
        .filter(models.AnimePerfil.status.in_(STATUS_COM_OPINIAO_FORMADA))
        .filter(models.AnimePerfil.nota.isnot(None))
        .order_by(models.AnimePerfil.nota.desc())
        .limit(top_n_favoritos)
        .all()
    )
    lista_favoritos = ", ".join(f"{a.titulo} (nota {a.nota})" for a in favoritos)

    return (
        f"Gêneros favoritos: {', '.join(top_generos)}.\n"
        f"Tags recorrentes no gosto do usuário: {', '.join(top_tags)}.\n"
        f"Alguns dos animes mais bem avaliados pelo usuário: {lista_favoritos}."
    )
