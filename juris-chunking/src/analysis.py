"""Bootstrap, testes pareados e recortes analíticos (F5).

Os recortes respondem à segunda metade da pergunta de pesquisa — não só "qual
estratégia ganha", mas "SOB QUAIS CONDIÇÕES". Um resultado global nulo com um
recorte que mostra ganho consistente em documentos longos, por exemplo, é um
resultado melhor (e mais publicável) do que uma média que esconde os dois casos.

Todas as funções aqui trabalham sobre scores POR CONSULTA — é isso que permite
reamostrar consultas no bootstrap e parear na comparação. Métrica agregada já
calculada não serve.
"""

from __future__ import annotations

import numpy as np
from ranx import Qrels, Run, evaluate


def per_query_scores(qrels: Qrels, run: Run, metric: str = "ndcg@10") -> dict[str, float]:
    """{query_id: score} — a base de todo o resto deste módulo.

    `make_comparable=True` não é opcional: sem ele o ranx aborta com
    AssertionError quando o run não tem exatamente as mesmas consultas do
    qrels — o que acontece de verdade sempre que alguma consulta não recupera
    nenhum documento. Com ele, a consulta ausente entra valendo 0, que é a
    leitura correta (não recuperar nada é falhar, não é "não se aplica").
    """
    scores = evaluate(qrels, run, metric, return_mean=False, make_comparable=True)
    # A ordem só bate DEPOIS da chamada acima: make_comparable normaliza o run
    # in-place, preenchendo as consultas faltantes. Ler os ids antes daria um
    # pareamento errado, silenciosamente.
    query_ids = run.get_query_ids()
    return {qid: float(s) for qid, s in zip(query_ids, np.asarray(scores).ravel())}


def bootstrap_ci(
    scores: list[float],
    n_resamples: int = 10_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """IC percentílico da MÉDIA, reamostrando consultas com reposição.

    Devolve `(media, limite_inferior, limite_superior)`.

    Reamostramos consultas (não documentos) porque a consulta é a unidade
    experimental: as 150 consultas do JurisTCU são uma amostra do universo de
    consultas possíveis, e é sobre essa variabilidade que queremos falar.
    """
    arr = np.asarray(scores, dtype=float)
    if arr.size == 0:
        raise ValueError("lista de scores vazia")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(n_resamples, arr.size))
    means = arr[idx].mean(axis=1)
    low, high = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(arr.mean()), float(low), float(high)


def _mean_ci_row(name: str, recorte: str, valor: str, scores: list[float], **extra) -> dict:
    mean, low, high = bootstrap_ci(scores)
    return {
        "run": name,
        "recorte": recorte,
        "valor": valor,
        "n_queries": len(scores),
        "media": mean,
        "ic95_inf": low,
        "ic95_sup": high,
        **extra,
    }


def slice_by_query_type(
    qrels: Qrels,
    runs: list[Run],
    query_metadata: dict[str, str],
    metric: str = "ndcg@10",
) -> list[dict]:
    """Recorte por tipo de consulta (campo `source` do JurisTCU: consultas reais
    de usuário, sintéticas por palavra-chave, sintéticas por pergunta)."""
    rows = []
    for run in runs:
        by_query = per_query_scores(qrels, run, metric)
        grupos: dict[str, list[float]] = {}
        for qid, score in by_query.items():
            grupos.setdefault(query_metadata.get(qid, "desconhecido"), []).append(score)
        for tipo, scores in sorted(grupos.items()):
            rows.append(_mean_ci_row(run.name, "tipo_consulta", tipo, scores, metrica=metric))
    return rows


def doc_length_terciles(doc_lengths: dict[str, int]) -> tuple[float, float]:
    """Pontos de corte (p33, p66) do tamanho dos documentos, em tokens."""
    valores = np.asarray(list(doc_lengths.values()), dtype=float)
    return tuple(np.percentile(valores, [33.333, 66.667]))


def query_length_terciles(
    qrels: Qrels, doc_lengths: dict[str, int]
) -> tuple[dict[str, str], tuple[float, float]]:
    """Classifica cada CONSULTA em curto/médio/longo pela mediana do tamanho
    dos seus documentos relevantes.

    Os cortes vêm da distribuição dessas medianas POR CONSULTA, não da
    distribuição de tamanho dos 12.880 documentos do corpus. A diferença
    importa muito: os documentos julgados relevantes são sistematicamente
    maiores que o acervo (são os acórdãos mais substantivos), então usar os
    percentis do corpus joga quase todas as consultas nos tercis superiores —
    na primeira rodada isso deu 3 / 67 / 80 consultas, e um grupo de 3 não
    sustenta nenhuma comparação. Usando os percentis das próprias consultas,
    os três grupos ficam equilibrados por construção.
    """
    medianas: dict[str, float] = {}
    for qid, docs in qrels.to_dict().items():
        tamanhos = [doc_lengths[d] for d in docs if d in doc_lengths]
        if tamanhos:
            medianas[qid] = float(np.median(tamanhos))
    if not medianas:
        return {}, (0.0, 0.0)

    p33, p66 = np.percentile(np.asarray(list(medianas.values())), [33.333, 66.667])
    tercil: dict[str, str] = {}
    for qid, m in medianas.items():
        tercil[qid] = "curto" if m <= p33 else ("medio" if m <= p66 else "longo")
    return tercil, (float(p33), float(p66))


def slice_by_doc_length_tercile(
    qrels: Qrels,
    runs: list[Run],
    doc_lengths: dict[str, int],
    metric: str = "ndcg@10",
) -> list[dict]:
    """Recorte por tamanho de documento, em tercis.

    A consulta é classificada pelo tercil dos seus documentos RELEVANTES (a
    mediana dos tamanhos dos docs no qrel daquela consulta). Recortar assim, e
    não pelos documentos recuperados, mantém o recorte independente do run —
    senão cada estratégia seria avaliada sobre um subconjunto diferente de
    consultas, e as colunas da tabela deixariam de ser comparáveis.
    """
    tercil_da_query, _cortes = query_length_terciles(qrels, doc_lengths)

    rows = []
    for run in runs:
        by_query = per_query_scores(qrels, run, metric)
        grupos: dict[str, list[float]] = {}
        for qid, score in by_query.items():
            tercil = tercil_da_query.get(qid)
            if tercil:
                grupos.setdefault(tercil, []).append(score)
        for tercil in ("curto", "medio", "longo"):
            if tercil in grupos:
                rows.append(
                    _mean_ci_row(run.name, "tamanho_doc", tercil, grupos[tercil], metrica=metric)
                )
    return rows


def poder_estatistico(
    qrels: Qrels,
    run_a: Run,
    run_b: Run,
    metric: str = "ndcg@10",
    alpha: float = 0.05,
    poder: float = 0.80,
) -> dict:
    """Qual diferença seria detectável com o número de consultas que temos?

    Um resultado não significativo tem duas leituras possíveis — "não há
    diferença" e "há, mas o teste não teria como vê-la" — e só a análise de
    poder separa as duas. É a pergunta natural da banca diante de uma tabela
    sem nenhum p < 0,05.

    Devolve o **efeito mínimo detectável (MDE)**: a menor diferença média de
    métrica que um teste t pareado com estas `n` consultas detectaria, com o
    poder pedido. Se a diferença observada for menor que o MDE, o experimento
    simplesmente não tem resolução para ela — o que é um achado a reportar, não
    um defeito a esconder.
    """
    from scipy import stats

    a = per_query_scores(qrels, run_a, metric)
    b = per_query_scores(qrels, run_b, metric)
    qids = sorted(set(a) & set(b))
    difs = np.array([a[q] - b[q] for q in qids])
    n = len(difs)
    if n < 2:
        raise ValueError("consultas insuficientes para análise de poder")

    dp = float(difs.std(ddof=1))
    observado = float(difs.mean())
    # z de duas caudas para alpha + z de uma cauda para o poder
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_poder = stats.norm.ppf(poder)
    mde = (z_alpha + z_poder) * dp / np.sqrt(n) if dp > 0 else 0.0
    d_cohen = observado / dp if dp > 0 else 0.0

    # quantas consultas seriam necessárias para detectar o efeito observado
    n_necessario = (
        int(np.ceil(((z_alpha + z_poder) * dp / abs(observado)) ** 2))
        if observado != 0 else None
    )
    return {
        "run_a": run_a.name,
        "run_b": run_b.name,
        "metric": metric,
        "n_queries": n,
        "diferenca_observada": observado,
        "desvio_padrao_das_diferencas": dp,
        "mde": float(mde),
        "detectavel": bool(abs(observado) >= mde),
        "d_de_cohen": float(d_cohen),
        "n_necessario_para_detectar": n_necessario,
    }


def poder_de_todos_os_pares(qrels: Qrels, runs: list[Run], metric: str = "ndcg@10") -> list[dict]:
    linhas = []
    for i, a in enumerate(runs):
        for b in runs[i + 1 :]:
            try:
                linhas.append(poder_estatistico(qrels, a, b, metric))
            except ValueError:
                continue
    return linhas


def section_of_span(start: int, end: int, gold_spans: list[dict]) -> str | None:
    """De qual macro-seção do acórdão vem o trecho `[start, end)`?

    Devolve a seção com maior sobreposição de caracteres. É isto que permite
    fazer a análise por seção **também nas baselines**: `fixed` e `recursive`
    devolvem `section=None`, mas o offset do chunk sabe de onde ele veio.
    O `plano_tecnico.md` §1 aponta esta análise como valendo "uma seção inteira
    de discussão no TCC" — ela responde se o chunking estrutural muda *quais
    partes do acórdão* chegam ao topo do ranking, não só o quanto acerta.
    """
    melhor, maior = None, 0
    for s in gold_spans:
        sobreposicao = min(end, s["end"]) - max(start, s["start"])
        if sobreposicao > maior:
            melhor, maior = s["section"], sobreposicao
    return melhor


def slice_by_section(
    chunks_top: list[dict],
    gold_spans_por_doc: dict[str, list[dict]],
    top_k: int = 10,
) -> list[dict]:
    """Distribuição das seções entre os chunks que venceram a agregação.

    `chunks_top` traz, por consulta, o chunk que deu o score de cada documento
    recuperado (o argmax do max-pooling). Contamos de qual seção veio cada um,
    nos `top_k` primeiros documentos de cada consulta.
    """
    contagem: dict[tuple[str, str], int] = {}
    totais: dict[str, int] = {}
    for reg in chunks_top:
        if reg["rank"] > top_k:
            continue
        run = reg["run"]
        secao = reg.get("section") or section_of_span(
            reg["start"], reg["end"], gold_spans_por_doc.get(reg["doc_id"], [])
        ) or "indefinido"
        contagem[(run, secao)] = contagem.get((run, secao), 0) + 1
        totais[run] = totais.get(run, 0) + 1

    linhas = []
    for (run, secao), n in sorted(contagem.items()):
        linhas.append({
            "run": run,
            "recorte": "secao_do_chunk",
            "valor": secao,
            "n_chunks": n,
            "fracao": n / totais[run] if totais[run] else 0.0,
            "top_k": top_k,
        })
    return linhas


def slice_by_retriever(qrels: Qrels, runs: list[Run], metric: str = "ndcg@10") -> list[dict]:
    """Recorte por retriever: agrupa os runs por BM25 vs. denso, para responder
    se o efeito do chunking depende do tipo de retriever."""
    rows = []
    for run in runs:
        partes = run.name.split("__")
        retriever = partes[1] if len(partes) > 1 else "desconhecido"
        estrategia = partes[0]
        scores = list(per_query_scores(qrels, run, metric).values())
        rows.append(
            _mean_ci_row(
                run.name, "retriever", retriever, scores,
                metrica=metric, estrategia=estrategia,
            )
        )
    return rows
