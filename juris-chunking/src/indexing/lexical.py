"""Retriever léxico BM25 sobre chunks (F4).

O índice é construído sobre CHUNKS, não sobre documentos: a agregação
chunk -> documento acontece depois, em `src/retrieval.py`. Por isso o índice
guarda, para cada posição, o `chunk_id` e o `doc_id` de origem.
"""

from __future__ import annotations

import bm25s

from ..chunkers.base import Chunk
from .text_norm import normalize_for_bm25


class BM25Index:
    """Índice BM25 de chunks, via `bm25s`.

    A mesma normalização (`normalize_for_bm25`) é aplicada na indexação e na
    busca — ver o docstring de `text_norm.py` para por que isso é crítico.
    """

    def __init__(self, backend: str = "bm25s"):
        if backend != "bm25s":
            raise ValueError(f"backend não suportado: {backend!r} (só 'bm25s')")
        self.backend = backend
        self._index: bm25s.BM25 | None = None
        self.chunk_ids: list[str] = []
        self.doc_ids: list[str] = []

    def build(self, chunks: list[Chunk], show_progress: bool = False) -> None:
        if not chunks:
            raise ValueError("não dá para indexar uma lista vazia de chunks")
        self.chunk_ids = [c.chunk_id for c in chunks]
        self.doc_ids = [c.doc_id for c in chunks]
        corpus_tokens = [normalize_for_bm25(c.text) for c in chunks]
        self._index = bm25s.BM25()
        self._index.index(corpus_tokens, show_progress=show_progress)

    def _require_index(self) -> bm25s.BM25:
        if self._index is None:
            raise RuntimeError("índice não construído — chame build() antes de search()")
        return self._index

    def search(self, query: str, top_k: int = 100) -> list[tuple[str, float]]:
        """Retorna [(chunk_id, score), ...] ordenado por score desc."""
        return self.search_batch([query], top_k=top_k)[0]

    def search_batch(self, queries: list[str], top_k: int = 100) -> list[list[tuple[str, float]]]:
        """Versão em lote — o `bm25s` pontua todas as consultas de uma vez, o
        que é bem mais rápido do que 150 chamadas separadas."""
        index = self._require_index()
        # `k` maior que o corpus faz o bm25s levantar erro; nas estratégias com
        # poucos chunks (smoke test) isso acontece de verdade.
        k = min(top_k, len(self.chunk_ids))
        query_tokens = [normalize_for_bm25(q) for q in queries]
        indices, scores = index.retrieve(query_tokens, k=k, show_progress=False)
        results: list[list[tuple[str, float]]] = []
        for row_idx, row_scores in zip(indices, scores):
            results.append(
                [(self.chunk_ids[int(i)], float(s)) for i, s in zip(row_idx, row_scores)]
            )
        return results

    def doc_of(self, chunk_id: str) -> str:
        """chunk_id -> doc_id (a chave da agregação)."""
        return self.doc_ids[self.chunk_ids.index(chunk_id)]
