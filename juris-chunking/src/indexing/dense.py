"""Retriever denso: sentence-transformers + FAISS IndexFlatIP.

Para ~16k documentos, brute force (IndexFlatIP) é suficiente — não
precisa de ANN aproximado (ver seção 2, E4, do plano_tecnico.md).
"""

from __future__ import annotations

from ..chunkers.base import Chunk


class DenseIndex:
    def __init__(self, model_name: str):
        self.model_name = model_name  # ver configs/models.yaml
        self._index = None
        self._chunk_ids: list[str] = []

    def build(self, chunks: list[Chunk]) -> None:
        raise NotImplementedError(
            "TODO (Semana 8): carregar SentenceTransformer(self.model_name), "
            "embedar chunks[i].text, normalizar e indexar em "
            "faiss.IndexFlatIP."
        )

    def search(self, query: str, top_k: int = 100) -> list[tuple[str, float]]:
        """Retorna [(chunk_id, score), ...] ordenado por score desc."""
        raise NotImplementedError("TODO (Semana 8)")
