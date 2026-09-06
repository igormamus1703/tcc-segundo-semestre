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
