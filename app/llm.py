from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app import schemas

load_dotenv()

# A sobrecarga (503) no tier free varia por modelo a cada instante — testamos
# e em um mesmo momento um modelo falhava enquanto outro respondia normal.
# Por isso: cadeia de fallback entre modelos, não retry repetido no mesmo.
MODELOS_FALLBACK = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite"]

# 503 = modelo sobrecarregado (comum no tier free), 429 = rate limit — ambos
# tendem a ser passageiros, vale a pena tentar outro modelo antes de desistir
CODIGOS_TRANSITORIOS = (429, 503)

SYSTEM_PROMPT = """Você é um recomendador de anime pessoal e criterioso.

Você recebe: um resumo do gosto do usuário, uma lista de animes candidatos (que \
ele nunca assistiu) e um pedido do momento (mood/contexto). Sua tarefa é escolher, \
dentre os candidatos, os que melhor atendem o pedido — cruzando o pedido específico \
com o gosto geral do usuário quando fizer sentido, sem viajar.

Regras:
- Escolha SOMENTE entre os candidatos listados. Nunca invente um anime ou um \
anilist_id que não esteja na lista fornecida.
- Priorize atender o pedido do momento. Gosto geral é critério de desempate, não \
deve sobrepor um pedido específico (ex: se o usuário pede algo curto e o gosto geral \
é por séries longas, respeite o pedido).
- Se nenhum candidato combinar bem com o pedido, retorne uma lista menor (até vazia) \
em vez de forçar uma escolha ruim — explique isso em "observacao".
- Justificativas curtas (1-2 frases), em português, citando o que no pedido ou no \
perfil motivou aquela escolha específica."""


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def _montar_texto_candidatos(candidatos: list[dict]) -> str:
    linhas = []
    for c in candidatos:
        tags = ", ".join(c["tags_anilist"] or [])
        sinopse = (c["sinopse"] or "").replace("\n", " ")[:500]
        linhas.append(
            f"- anilist_id={c['anilist_id']} | {c['titulo']} ({c['ano']}, {c['formato']})\n"
            f"  tags: {tags}\n"
            f"  sinopse: {sinopse}"
        )
    return "\n".join(linhas)


def recomendar(
    resumo_perfil: str, candidatos: list[dict], pedido: str, top_n: int = 5
) -> schemas.RespostaRecomendacao:
    prompt = (
        f"Resumo do gosto do usuário:\n{resumo_perfil}\n\n"
        f'Pedido do momento: "{pedido}"\n\n'
        f"Candidatos disponíveis:\n{_montar_texto_candidatos(candidatos)}\n\n"
        f"Escolha até {top_n} candidatos da lista acima que melhor atendem o pedido."
    )

    # precisa manter `client` numa variável — encadear a chamada direto em
    # `_get_client().models...` deixa o objeto sem referência forte e o GC
    # pode fechar o httpx client interno (via __del__) antes da request terminar
    client = _get_client()

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_json_schema=schemas.RespostaRecomendacao.model_json_schema(),
    )

    # uma única passada pela lista, sem repetir rodada: numa cota de tier free
    # tão apertada (20 req/min pra conta nova), insistir em várias rodadas
    # consome a própria cota e piora o problema que devia resolver. Se todos
    # falharem aqui, é melhor deixar o usuário tentar de novo manualmente
    # (o botão "Enviar" já existe pra isso) do que queimar mais requisições.
    ultimo_erro: genai_errors.APIError | None = None
    for modelo in MODELOS_FALLBACK:
        try:
            response = client.models.generate_content(model=modelo, contents=prompt, config=config)
            return schemas.RespostaRecomendacao.model_validate_json(response.text)
        except genai_errors.APIError as exc:
            if exc.code not in CODIGOS_TRANSITORIOS:
                raise
            ultimo_erro = exc

    raise ultimo_erro
