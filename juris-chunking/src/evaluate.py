"""E5 — Avaliação: nDCG@10, MRR@10, MAP@10, Recall@100 via `ranx`.

Recortes obrigatórios (Semana 10): por tipo de consulta, por tamanho de
documento (tercis), por retriever.
"""

from __future__ import annotations


def evaluate_run(qrels, run, metrics=("ndcg@10", "mrr@10", "map@10", "recall@100")):
    raise NotImplementedError(
        "TODO (Semana 7-9): usar ranx.Qrels / ranx.Run / ranx.evaluate "
        "com os TREC run files salvos em results/runs/."
    )


def paired_significance(run_a, run_b, qrels, metric: str = "ndcg@10"):
    raise NotImplementedError(
        "TODO (Semana 11): usar ranx.compare (teste pareado com correção "
        "para comparações múltiplas)."
    )
