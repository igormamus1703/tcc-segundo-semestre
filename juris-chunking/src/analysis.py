"""Bootstrap, testes pareados e recortes analíticos (Semana 10-11)."""

from __future__ import annotations


def bootstrap_ci(scores: list[float], n_resamples: int = 10_000, alpha: float = 0.05):
    raise NotImplementedError(
        "TODO (Semana 11): bootstrap manual (scipy.stats.bootstrap ou "
        "resampling explícito) para intervalo de confiança das métricas."
    )


def slice_by_query_type(results, query_metadata):
    raise NotImplementedError("TODO (Semana 10): recorte por tipo de consulta.")


def slice_by_doc_length_tercile(results, doc_lengths):
    raise NotImplementedError(
        "TODO (Semana 10): recorte por tamanho de documento (tercis)."
    )


def slice_by_retriever(results):
    raise NotImplementedError("TODO (Semana 10): recorte por retriever.")
