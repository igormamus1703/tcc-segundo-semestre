"""F6 — Recorte do índice por macro-seção do acórdão.

Este módulo existe por causa de um descompasso medido na F5: a fundamentação
(o voto) ocupa 22,8% do texto do acórdão e concentra **72,0%** do conteúdo
julgado relevante, mas 65–74% dos chunks que vencem a agregação vêm do
**relatório**, que tem 69,9% do texto e só 25,7% da relevância. Os dois
retrievers acham o termo onde há *mais texto*, não onde há *mais informação*
(ver `docs/docsleo/branches/leo-f4-indexacao-e-docs/03-analise-do-dominio.md`).

Daí as duas intervenções implementadas aqui:

- **corte binário** (`--secoes`): só indexa os chunks das seções pedidas;
- **ponderação** (`--pesos`): indexa tudo, mas multiplica o score do chunk
  pelo peso da sua seção antes da agregação chunk -> documento. Preserva o
  recall, que o corte binário sacrifica.

O ponto metodológico que torna isso publicável: a seção de um chunk é
resolvida **pelo offset**, não pelo rótulo. Chunks `fixed` e `recursive`
carregam `section=None`, mas carregam `(start, end)` — e a sobreposição com os
spans do documento diz de onde vieram. Assim o recorte por seção vale para as
cinco estratégias, e não só para as duas estruturais.

Os spans podem vir de duas fontes, e a diferença é a ablação central do
trabalho: `gold` (as colunas do CSV do TCU, que só existem porque o TCU publica
assim) e `pred` (o segmentador de regras, 92,2% de acurácia). Uma conclusão que
só valesse com `gold` não seria aplicável a nenhum acervo real.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .analysis import section_of_span
from .chunkers.base import Chunk

SECOES_VALIDAS: tuple[str, ...] = ("ementa", "relatorio", "fundamentacao", "dispositivo")

# Nome curto por seção, para o rótulo do run. Sem isto, um run de duas seções
# viraria `structural_gold__dense-bge_m3__sec-fundamentacao+ementa`, e o nome do
# arquivo passa dos 120 caracteres com três seções.
_ABREV = {"ementa": "em", "relatorio": "rel", "fundamentacao": "fund", "dispositivo": "disp"}


def parse_secoes(texto: str) -> set[str]:
    """`"ementa,fundamentacao"` -> `{"ementa", "fundamentacao"}`.

    Aceita também a forma negativa, que é como a intervenção é descrita no
    texto do trabalho ("descartar o relatório") e evita ter de listar as outras
    três sem errar nenhuma. Duas grafias, de propósito:

    - `"-relatorio"` é a natural, mas na linha de comando o argparse a lê como
      uma opção e aborta com "expected one argument" — só funciona colada,
      `--secoes=-relatorio`;
    - `"sem:relatorio"` não começa com hífen e funciona em qualquer shell.

    Manter as duas evita que alguém perca dez minutos com um erro de parsing
    numa rodada de madrugada.
    """
    itens = [p.strip().lower() for p in texto.split(",") if p.strip()]
    if not itens:
        raise ValueError("lista de secoes vazia")

    def negativo(i: str) -> bool:
        return i.startswith("-") or i.startswith("sem:")

    negativos = {i.lstrip("-").removeprefix("sem:") for i in itens if negativo(i)}
    positivos = {i for i in itens if not negativo(i)}
    if negativos and positivos:
        raise ValueError(
            "misturar secoes positivas e negativas e ambiguo: "
            f"use ou {sorted(positivos)} ou {['-' + n for n in sorted(negativos)]}"
        )

    pedidas = negativos or positivos
    desconhecidas = pedidas - set(SECOES_VALIDAS)
    if desconhecidas:
        raise ValueError(
            f"secao desconhecida: {sorted(desconhecidas)} (validas: {list(SECOES_VALIDAS)})"
        )
    return set(SECOES_VALIDAS) - negativos if negativos else positivos


def parse_pesos(texto: str) -> dict[str, float]:
    """`"relatorio=0.5,fundamentacao=1.5"` -> `{...}`.

    Seção omitida vale 1.0 — o default é "não mexe", para que um peso escrito
    errado degrade só a seção citada, e não o run inteiro.
    """
    pesos: dict[str, float] = {}
    for par in texto.split(","):
        par = par.strip()
        if not par:
            continue
        if "=" not in par:
            raise ValueError(f"peso sem '=': {par!r} (formato: secao=valor)")
        secao, valor = par.split("=", 1)
        secao = secao.strip().lower()
        if secao not in SECOES_VALIDAS:
            raise ValueError(f"secao desconhecida: {secao!r} (validas: {list(SECOES_VALIDAS)})")
        try:
            peso = float(valor)
        except ValueError:
            raise ValueError(f"peso nao numerico em {par!r}") from None
        if peso < 0:
            raise ValueError(f"peso negativo em {par!r}: inverteria a ordem do ranking")
        pesos[secao] = peso
    if not pesos:
        raise ValueError("nenhum peso informado")
    return pesos


def rotulo_secoes(secoes: Iterable[str]) -> str:
    """Rótulo curto e estável do recorte, para o nome do run.

    Complemento de uma seção só vira `sem_relatorio` — que é como o resultado é
    descrito no texto, e é o recorte que mais usamos.
    """
    conjunto = set(secoes)
    faltando = set(SECOES_VALIDAS) - conjunto
    if len(faltando) == 1:
        return f"sem_{next(iter(faltando))}"
    if not faltando:
        return "completo"
    return "+".join(_ABREV[s] for s in SECOES_VALIDAS if s in conjunto)


def rotulo_pesos(pesos: dict[str, float]) -> str:
    """`{"relatorio": 0.5}` -> `rel0.5`. Ordem canônica, não a de digitação:
    dois runs com os mesmos pesos precisam ter o mesmo nome."""
    return "-".join(f"{_ABREV[s]}{pesos[s]:g}" for s in SECOES_VALIDAS if s in pesos)


def secao_do_chunk(chunk: Chunk, spans: Sequence[dict] | None) -> str | None:
    """Seção de um chunk: o rótulo quando existe, senão o offset.

    O rótulo tem precedência porque, nas estratégias estruturais, ele **é** a
    definição do chunk — o chunk foi criado a partir daquele span. Resolver
    pelo offset nesse caso daria o mesmo resultado no caso normal e um
    resultado pior na borda (um chunk estrutural que encoste no span vizinho
    por um caractere seria reatribuído).
    """
    if chunk.section:
        return chunk.section
    if not spans:
        return None
    return section_of_span(chunk.start, chunk.end, spans)


def rotular(chunks: Sequence[Chunk], spans_por_doc: dict[str, list[dict]]) -> list[str | None]:
    """Seção de cada chunk, na MESMA ordem da entrada.

    A ordem é contrato: quem chama usa a lista para filtrar linhas da matriz de
    embeddings, onde a linha `i` é o chunk `i`. Devolver um dicionário
    convidaria a reordenar, e um embedding fora de ordem produz um resultado
    errado sem levantar nenhum erro.
    """
    return [secao_do_chunk(c, spans_por_doc.get(c.doc_id)) for c in chunks]


def filtrar(
    chunks: Sequence[Chunk],
    secoes: Iterable[str],
    spans_por_doc: dict[str, list[dict]],
) -> tuple[list[Chunk], dict[str, int]]:
    """Mantém só os chunks cuja seção está em `secoes`.

    Devolve também a contagem por seção (incluindo `indefinido`), que vai para
    o manifesto da rodada: "o índice encolheu de 286.689 para 95.300 chunks" é
    parte do resultado, não detalhe de execução.

    Chunk sem seção resolvível é **descartado** quando há filtro ativo. É a
    escolha conservadora: mantê-lo faria o índice "sem relatório" conter
    trechos de relatório de documentos cujo span falhou, e o efeito medido
    seria menor do que o real por contaminação — um erro que puxa o resultado
    na direção de um falso negativo, não de um falso positivo.
    """
    pedidas = set(secoes)
    contagem: dict[str, int] = {}
    mantidos: list[Chunk] = []
    for chunk, secao in zip(chunks, rotular(chunks, spans_por_doc)):
        chave = secao or "indefinido"
        contagem[chave] = contagem.get(chave, 0) + 1
        if secao in pedidas:
            mantidos.append(chunk)
    return mantidos, contagem


def amostra_aleatoria(
    chunks: Sequence[Chunk], fracao: float, seed: int = 42
) -> list[Chunk]:
    """CONTROLE do recorte por seção: mantém uma fração aleatória dos chunks.

    Existe para responder à primeira pergunta que a banca vai fazer diante de
    "descartar o relatório melhora o nDCG@10 em 16%": *isso é sobre o
    relatório, ou qualquer índice menor teria melhorado?*

    Um índice com um terço dos chunks é um índice com menos concorrência por
    vaga no top-k; se um recorte **aleatório** do mesmo tamanho melhorasse
    tanto quanto o recorte por seção, o achado não seria sobre a estrutura do
    acórdão, seria sobre o tamanho do índice — e a contribuição do trabalho
    desapareceria.

    A amostra é uniforme sobre os chunks, não sobre os documentos, de
    propósito: é o que iguala as duas condições em número de chunks. Todos os
    documentos continuam alcançáveis nas duas, já que cada um mantém uma
    fração dos seus chunks.

    A ordem original é preservada, pelo mesmo motivo de `rotular`: quem chama
    usa a lista para selecionar linhas da matriz de embeddings.
    """
    import numpy as np

    if not 0 < fracao <= 1:
        raise ValueError(f"fracao fora de (0, 1]: {fracao}")
    n = round(len(chunks) * fracao)
    if n == 0:
        raise ValueError(f"fracao {fracao} nao mantem nenhum chunk de {len(chunks)}")
    rng = np.random.default_rng(seed)
    escolhidos = np.sort(rng.choice(len(chunks), size=n, replace=False))
    return [chunks[i] for i in escolhidos]


def pesos_por_chunk(
    chunks: Sequence[Chunk],
    pesos: dict[str, float],
    spans_por_doc: dict[str, list[dict]],
    peso_padrao: float = 1.0,
) -> dict[str, float]:
    """`{chunk_id: peso}` para a ponderação por seção.

    Só entram no dicionário os chunks cujo peso difere de `peso_padrao` — com
    2,2 milhões de chunks, guardar o peso 1.0 de todos custaria centenas de MB
    para não dizer nada.
    """
    resultado: dict[str, float] = {}
    for chunk, secao in zip(chunks, rotular(chunks, spans_por_doc)):
        peso = pesos.get(secao, peso_padrao) if secao else peso_padrao
        if peso != peso_padrao:
            resultado[chunk.chunk_id] = peso
    return resultado
