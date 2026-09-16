import numpy as np
from sentence_transformers import SentenceTransformer

MODELO_NOME = "all-MiniLM-L6-v2"

_modelo: SentenceTransformer | None = None


def _get_modelo() -> SentenceTransformer:
    global _modelo
    if _modelo is None:
        _modelo = SentenceTransformer(MODELO_NOME)
    return _modelo


def montar_texto(sinopse: str | None, tags_anilist: list[str] | None) -> str:
    partes = []
    if sinopse:
        partes.append(sinopse)
    if tags_anilist:
        partes.append(", ".join(tags_anilist))
    return " ".join(partes)


def calcular_embedding(texto: str) -> list[float]:
    vetor = _get_modelo().encode(texto, normalize_embeddings=True)
    return vetor.tolist()


def similaridade_cosseno(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denominador = np.linalg.norm(va) * np.linalg.norm(vb)
    if denominador == 0:
        return 0.0
    return float(np.dot(va, vb) / denominador)


def vetor_de_gosto(pares_embedding_peso: list[tuple[list[float], float]]) -> list[float]:
    """Média ponderada de embeddings — o peso de cada anime (ex: pela nota)
    é decidido pelo chamador, esse módulo só faz a álgebra."""
    vetores = np.array([e for e, _ in pares_embedding_peso])
    pesos = np.array([p for _, p in pares_embedding_peso])
    return np.average(vetores, axis=0, weights=pesos).tolist()
