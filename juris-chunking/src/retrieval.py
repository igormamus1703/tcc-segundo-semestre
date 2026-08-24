"""E4 — Agregação chunk -> documento.

Padrão: max-pooling. sum-top-k (k=3) como análise de sensibilidade — se
concordarem, reportar isso blinda a metodologia (ver plano_tecnico.md).
"""

from __future__ import annotations

from collections import defaultdict


def max_pooling(chunk_scores: list[tuple[str, str, float]]) -> dict[str, float]:
    """chunk_scores: [(chunk_id, doc_id, score), ...] -> {doc_id: score}."""
    doc_scores: dict[str, float] = {}
    for _chunk_id, doc_id, score in chunk_scores:
        if doc_id not in doc_scores or score > doc_scores[doc_id]:
            doc_scores[doc_id] = score
    return doc_scores


def sum_top_k(chunk_scores: list[tuple[str, str, float]], k: int = 3) -> dict[str, float]:
    """Soma os k maiores scores de chunk por documento."""
    by_doc: dict[str, list[float]] = defaultdict(list)
    for _chunk_id, doc_id, score in chunk_scores:
        by_doc[doc_id].append(score)
    return {
        doc_id: sum(sorted(scores, reverse=True)[:k])
        for doc_id, scores in by_doc.items()
    }
