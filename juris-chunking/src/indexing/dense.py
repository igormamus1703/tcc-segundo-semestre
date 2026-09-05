"""Retriever denso: sentence-transformers + FAISS IndexFlatIP (F4).

Brute force basta nesta escala (plano_tecnico.md §2, E4): com `IndexFlatIP` e
embeddings normalizados, o produto interno é a similaridade de cosseno e a
busca é exata — sem o erro de recall que um índice aproximado (HNSW/IVF)
introduziria e que precisaríamos justificar na banca.

O custo real aqui é o ENCODE, não a busca. Por isso os embeddings são
cacheados em `.npy`: reindexar para trocar de agregação ou de métrica não
recalcula nada.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..chunkers.base import Chunk


def _safe_name(model_name: str) -> str:
    """'intfloat/multilingual-e5-base' -> 'intfloat__multilingual-e5-base'."""
    return model_name.replace("/", "__").replace(":", "_")


class DenseIndex:
    """Índice denso de chunks.

    `query_prefix` / `passage_prefix` vêm do `configs/models.yaml` e NÃO são
    opcionais: e5 exige "query: "/"passage: " e o embeddinggemma exige
    "task: search result | query: "/"title: none | text: ". Usar o prefixo
    errado degrada a recuperação silenciosamente — o modelo não reclama, só
    recupera pior.
    """

    def __init__(
        self,
        model_name: str,
        query_prefix: str = "",
        passage_prefix: str = "",
        batch_size: int = 64,
    ):
        self.model_name = model_name
        self.query_prefix = query_prefix
        self.passage_prefix = passage_prefix
        self.batch_size = batch_size
        self._model = None
        self._index = None
        self.chunk_ids: list[str] = []
        self.doc_ids: list[str] = []

    # -- modelo (carregado só quando precisa: importar torch custa segundos) --
    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str], prefix: str, show_progress: bool = False) -> np.ndarray:
        model = self._get_model()
        prefixed = [prefix + t for t in texts] if prefix else texts
        emb = model.encode(
            prefixed,
            batch_size=self.batch_size,
            normalize_embeddings=True,  # torna IndexFlatIP == cosseno
            convert_to_numpy=True,
            show_progress_bar=show_progress,
        )
        return np.asarray(emb, dtype="float32")

    # -- construção --
    def build(
        self,
        chunks: list[Chunk],
        cache_dir: Path | None = None,
        show_progress: bool = False,
    ) -> None:
        """Indexa `chunks`, reaproveitando embeddings de `cache_dir` quando os
        chunk_ids cacheados batem exatamente com os atuais."""
        if not chunks:
            raise ValueError("não dá para indexar uma lista vazia de chunks")
        self.chunk_ids = [c.chunk_id for c in chunks]
        self.doc_ids = [c.doc_id for c in chunks]

        emb = self._load_cache(cache_dir) if cache_dir else None
        if emb is None:
            emb = self.encode([c.text for c in chunks], self.passage_prefix, show_progress)
            if cache_dir:
                self._save_cache(cache_dir, emb)

        import faiss

        self._index = faiss.IndexFlatIP(emb.shape[1])
        self._index.add(emb)

    def _cache_paths(self, cache_dir: Path) -> tuple[Path, Path]:
        stem = _safe_name(self.model_name)
        return cache_dir / f"emb_{stem}.npy", cache_dir / f"chunk_ids_{stem}.json"

    def _load_cache(self, cache_dir: Path) -> np.ndarray | None:
        emb_path, ids_path = self._cache_paths(cache_dir)
        if not (emb_path.exists() and ids_path.exists()):
            return None
        cached_ids = json.loads(ids_path.read_text(encoding="utf-8"))
        # Só reaproveita se o conjunto de chunks for exatamente o mesmo — senão
        # o embedding da posição i não corresponde ao chunk da posição i, e o
        # resultado sairia errado sem nenhum erro visível.
        if cached_ids != self.chunk_ids:
            return None
        return np.load(emb_path).astype("float32")

    def _save_cache(self, cache_dir: Path, emb: np.ndarray) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        emb_path, ids_path = self._cache_paths(cache_dir)
        np.save(emb_path, emb)
        ids_path.write_text(json.dumps(self.chunk_ids), encoding="utf-8")

    # -- busca --
    def _require_index(self):
        if self._index is None:
            raise RuntimeError("índice não construído — chame build() antes de search()")
        return self._index

    def search(self, query: str, top_k: int = 100) -> list[tuple[str, float]]:
        """Retorna [(chunk_id, score), ...] ordenado por score desc."""
        return self.search_batch([query], top_k=top_k)[0]

    def search_batch(self, queries: list[str], top_k: int = 100) -> list[list[tuple[str, float]]]:
        index = self._require_index()
        k = min(top_k, len(self.chunk_ids))
        q_emb = self.encode(queries, self.query_prefix)
        scores, indices = index.search(q_emb, k)
        return [
            [(self.chunk_ids[int(i)], float(s)) for i, s in zip(row_idx, row_scores) if i >= 0]
            for row_idx, row_scores in zip(indices, scores)
        ]

    def doc_of(self, chunk_id: str) -> str:
        return self.doc_ids[self.chunk_ids.index(chunk_id)]
