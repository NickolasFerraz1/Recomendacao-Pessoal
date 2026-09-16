from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AnimeSearchRequest(BaseModel):
    query: str


class AnimeSearchResult(BaseModel):
    anilist_id: int
    titulo: str
    ano: Optional[int] = None
    formato: Optional[str] = None


class AnimeCreate(BaseModel):
    anilist_id: int
    status: str
    nota: Optional[int] = None
    tags_proprias: Optional[list[str]] = None


class AnimeUpdate(BaseModel):
    status: Optional[str] = None
    nota: Optional[int] = None
    tags_proprias: Optional[list[str]] = None


class AnimePerfilOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    anilist_id: int
    titulo: str
    status: str
    nota: Optional[int] = None
    tags_anilist: Optional[list[str]] = None
    tags_proprias: Optional[list[str]] = None
    data_registro: datetime


class CatalogoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    anilist_id: int
    titulo: str
    sinopse: Optional[str] = None
    tags_anilist: Optional[list[str]] = None
    popularidade: Optional[int] = None
    nota_media: Optional[float] = None
    formato: Optional[str] = None
    ano: Optional[int] = None
    data_adicionado: datetime


class SyncResultOut(BaseModel):
    generos_usados: list[str]
    tags_usadas: list[str]
    candidatos_novos: int
    candidatos_atualizados: int
    total_no_catalogo: int


class RecalculoEmbeddingsOut(BaseModel):
    perfil_atualizados: int
    perfil_refeitos_da_anilist: int
    catalogo_atualizados: int


class CandidatoOut(BaseModel):
    id: int
    anilist_id: int
    titulo: str
    sinopse: Optional[str] = None
    tags_anilist: Optional[list[str]] = None
    popularidade: Optional[int] = None
    nota_media: Optional[float] = None
    formato: Optional[str] = None
    ano: Optional[int] = None
    similaridade: float


class PedidoRecomendacao(BaseModel):
    mensagem: str
    top_n: int = 5


class ItemRecomendado(BaseModel):
    anilist_id: int
    titulo: str
    justificativa: str


class RespostaRecomendacao(BaseModel):
    itens: list[ItemRecomendado]
    observacao: Optional[str] = None
