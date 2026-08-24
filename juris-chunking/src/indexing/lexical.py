"""Retriever léxico BM25 (bm25s, ou rank_bm25 como fallback)."""

from __future__ import annotations

from ..chunkers.base import Chunk


class BM25Index:
    def __init__(self, backend: str = "bm25s"):
        self.backend = backend
        self._index = None

    def build(self, chunks: list[Chunk]) -> None:
        raise NotImplementedError(
            "TODO (Semana 7): tokenizar chunks[i].text e construir o índice "
            "BM25 via bm25s (ou rank_bm25)."
        )

    def search(self, query: str, top_k: int = 100) -> list[tuple[str, float]]:
        """Retorna [(chunk_id, score), ...] ordenado por score desc."""
        raise NotImplementedError("TODO (Semana 7)")
