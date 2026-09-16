import time

import httpx

ANILIST_URL = "https://graphql.anilist.co"

SEARCH_QUERY = """
query ($search: String) {
  Page(perPage: 10) {
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      id
      title {
        romaji
        english
      }
      startDate {
        year
      }
      format
    }
  }
}
"""

DETAIL_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title {
      romaji
      english
    }
    description(asHtml: false)
    genres
    tags {
      name
      rank
    }
  }
}
"""

CANDIDATOS_QUERY = """
query ($generos: [String], $tags: [String], $excluidos: [Int], $perPage: Int, $pagina: Int) {
  Page(page: $pagina, perPage: $perPage) {
    media(
      genre_in: $generos
      tag_in: $tags
      id_not_in: $excluidos
      type: ANIME
      sort: POPULARITY_DESC
      isAdult: false
    ) {
      id
      title {
        romaji
        english
      }
      description(asHtml: false)
      genres
      tags {
        name
        rank
      }
      averageScore
      popularity
      format
      startDate {
        year
      }
    }
  }
}
"""

# Enum oficial de gêneros da AniList — usado pra separar "gênero" de "tag" livre
# dentro de tags_anilist (que guarda os dois juntos).
GENEROS_ANILIST = {
    "Action", "Adventure", "Comedy", "Drama", "Ecchi", "Fantasy", "Hentai",
    "Horror", "Mahou Shoujo", "Mecha", "Music", "Mystery", "Psychological",
    "Romance", "Sci-Fi", "Slice of Life", "Sports", "Supernatural", "Thriller",
}


class AniListError(Exception):
    pass


def _request(query: str, variables: dict, tentativas: int = 3) -> dict:
    for tentativa in range(tentativas):
        try:
            response = httpx.post(
                ANILIST_URL,
                json={"query": query, "variables": variables},
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise AniListError(str(exc)) from exc

        if response.status_code == 429 and tentativa < tentativas - 1:
            time.sleep(int(response.headers.get("retry-after", "10")) + 1)
            continue

        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AniListError(str(exc)) from exc

        payload = response.json()
        if "errors" in payload:
            raise AniListError(payload["errors"])
        return payload["data"]

    raise AniListError("Rate limit da AniList excedido após múltiplas tentativas")


def _melhor_titulo(title: dict) -> str:
    return title["english"] or title["romaji"]


def _tags_relevantes(genres: list[str], tags: list[dict], rank_minimo: int = 60, top_n: int = 15) -> list[str]:
    """Gêneros + as tags mais relevantes (por rank da própria AniList), não
    todas as tags cru — um anime pode ter 70+ tags, e jogar tudo isso sem peso
    no texto do embedding afoga o sinal da sinopse."""
    relevantes = sorted(
        (t for t in tags if (t.get("rank") or 0) >= rank_minimo),
        key=lambda t: t["rank"],
        reverse=True,
    )[:top_n]
    return genres + [t["name"] for t in relevantes]


def search_anime(titulo: str) -> list[dict]:
    data = _request(SEARCH_QUERY, {"search": titulo})
    return [
        {
            "anilist_id": media["id"],
            "titulo": _melhor_titulo(media["title"]),
            "ano": media["startDate"]["year"],
            "formato": media["format"],
        }
        for media in data["Page"]["media"]
    ]


def get_anime_detail(anilist_id: int) -> dict:
    data = _request(DETAIL_QUERY, {"id": anilist_id})
    media = data["Media"]
    return {
        "anilist_id": media["id"],
        "titulo": _melhor_titulo(media["title"]),
        "descricao": media["description"],
        "tags_anilist": _tags_relevantes(media["genres"], media["tags"]),
    }


def buscar_candidatos(
    genero: str | None,
    tag: str | None,
    excluir_ids: list[int],
    per_page: int = 50,
    paginas: int = 2,
) -> list[dict]:
    """Busca candidatos por UM gênero OU UMA tag por vez (nunca os dois, e
    nunca listas com mais de um valor): genre_in/tag_in na AniList aplicam AND
    entre os elementos da lista (o anime precisaria ter TODOS os gêneros
    simultaneamente), então uma lista com vários gêneros favoritos praticamente
    não bate com nada. Pra cobrir vários gêneros/tags, o chamador faz uma
    chamada por valor e junta os resultados (união, não interseção).
    """
    resultados = []
    for pagina in range(1, paginas + 1):
        # a AniList responde 500 se genre_in/tag_in/id_not_in vierem como
        # `null` explícito — a chave precisa ser omitida quando vazia.
        variaveis = {"perPage": per_page, "pagina": pagina}
        if genero:
            variaveis["generos"] = [genero]
        if tag:
            variaveis["tags"] = [tag]
        if excluir_ids:
            variaveis["excluidos"] = excluir_ids

        data = _request(CANDIDATOS_QUERY, variaveis)
        media_lista = data["Page"]["media"]
        resultados.extend(
            {
                "anilist_id": media["id"],
                "titulo": _melhor_titulo(media["title"]),
                "sinopse": media["description"],
                "tags_anilist": _tags_relevantes(media["genres"], media["tags"]),
                "popularidade": media["popularity"],
                "nota_media": media["averageScore"],
                "formato": media["format"],
                "ano": media["startDate"]["year"],
            }
            for media in media_lista
        )
        if len(media_lista) < per_page:
            break  # acabaram os resultados dessa categoria
        if pagina < paginas:
            time.sleep(1.5)
    return resultados
