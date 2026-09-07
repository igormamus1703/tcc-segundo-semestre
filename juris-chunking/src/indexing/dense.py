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
import time
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
        max_seq_length: int | None = None,
        dtype: str = "auto",
        device: str | None = None,
    ):
        self.model_name = model_name
        self.query_prefix = query_prefix
        self.passage_prefix = passage_prefix
        self.batch_size = batch_size
        # A janela do modelo NÃO é detalhe de performance, é de validade: com
        # 512 tokens, ~37% do conteúdo dos chunks de 1024 é descartado, e só a
        # estratégia fixed_512_256 caberia inteira — o que lhe daria uma
        # vantagem artificial na comparação. Ver o doc 10 do docsleo.
        self.max_seq_length = max_seq_length
        self.dtype = dtype
        self.device = device
        self._model = None
        self._index = None
        self.chunk_ids: list[str] = []
        self.doc_ids: list[str] = []

    # -- modelo (carregado só quando precisa: importar torch custa segundos) --
    def _resolve_device(self) -> str:
        if self.device:
            return self.device
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"

    def _resolve_dtype(self, device: str):
        """fp16 na GPU dá ~3x de velocidade sem perda mensurável de qualidade
        para recuperação; na CPU o fp16 é emulado e fica mais LENTO, então lá
        o padrão continua sendo fp32."""
        import torch

        if self.dtype == "auto":
            return torch.float16 if device == "cuda" else None
        return {"fp16": torch.float16, "bf16": torch.bfloat16, "fp32": None}[self.dtype]

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            device = self._resolve_device()
            torch_dtype = self._resolve_dtype(device)
            kwargs = {}
            if torch_dtype is not None:
                kwargs["model_kwargs"] = {"torch_dtype": torch_dtype}
            self._model = SentenceTransformer(self.model_name, device=device, **kwargs)
            if self.max_seq_length:
                self._model.max_seq_length = self.max_seq_length
        return self._model

    def describe(self) -> str:
        """Uma linha com a configuração efetiva — vai para o log da rodada."""
        m = self._get_model()
        return (
            f"{self.model_name} | device={self._resolve_device()} "
            f"| dtype={self.dtype} | janela={m.max_seq_length} | batch={self.batch_size}"
        )

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

    def encode_com_checkpoint(
        self,
        texts: list[str],
        cache_dir: Path,
        bloco: int = 50_000,
        show_progress: bool = False,
        log=print,
    ) -> np.ndarray:
        """Encoda em blocos, gravando cada bloco em disco assim que fica pronto.

        O encode do corpus inteiro leva ~10 h. Sem checkpoint, uma queda de
        energia, um crash de driver ou um Ctrl+C na nona hora jogam fora o
        trabalho todo. Gravando de bloco em bloco, a retomada custa no máximo
        um bloco — e o `.npy` final só é escrito quando todos os blocos
        existem, então um cache completo nunca representa um encode parcial.
        """
        cache_dir.mkdir(parents=True, exist_ok=True)
        stem = _safe_name(self.model_name)
        partes_dir = cache_dir / f"parcial_{stem}"
        partes_dir.mkdir(exist_ok=True)

        n_blocos = (len(texts) + bloco - 1) // bloco
        partes: list[np.ndarray] = []
        for i in range(n_blocos):
            parte_path = partes_dir / f"bloco_{i:05d}.npy"
            ini, fim = i * bloco, min((i + 1) * bloco, len(texts))
            if parte_path.exists():
                arr = np.load(parte_path)
                if arr.shape[0] == fim - ini:  # bloco íntegro
                    partes.append(arr)
                    log(f"    bloco {i+1}/{n_blocos} recuperado do checkpoint")
                    continue
                parte_path.unlink()  # bloco truncado por interrupção
            t0 = time.time()
            arr = self.encode(texts[ini:fim], self.passage_prefix, show_progress)
            # grava em arquivo temporário e renomeia: se o processo morrer no
            # meio da escrita, não fica um .npy pela metade parecendo íntegro.
            # O np.save é chamado com um FILE OBJECT de propósito — recebendo um
            # caminho, ele acrescenta ".npy" ao nome e o arquivo escrito não
            # seria o que o rename procura.
            tmp = parte_path.with_name(parte_path.name + ".tmp")
            with tmp.open("wb") as f:
                np.save(f, arr)
            tmp.replace(parte_path)
            partes.append(arr)
            dt = time.time() - t0
            restante = (n_blocos - i - 1) * dt
            log(
                f"    bloco {i+1}/{n_blocos} ({fim-ini:,} chunks) em {dt/60:.1f} min"
                f" — faltam ~{restante/3600:.1f} h"
            )

        emb = np.vstack(partes)
        self._save_cache(cache_dir, emb)
        for p in partes_dir.glob("bloco_*.npy"):
            p.unlink()
        partes_dir.rmdir()
        return emb

    # -- construção --
    def build(
        self,
        chunks: list[Chunk],
        cache_dir: Path | None = None,
        show_progress: bool = False,
        bloco: int = 50_000,
        log=print,
    ) -> None:
        """Indexa `chunks`, reaproveitando embeddings de `cache_dir` quando os
        chunk_ids cacheados batem exatamente com os atuais."""
        if not chunks:
            raise ValueError("não dá para indexar uma lista vazia de chunks")
        self.chunk_ids = [c.chunk_id for c in chunks]
        self.doc_ids = [c.doc_id for c in chunks]

        emb = self._load_cache(cache_dir) if cache_dir else None
        if emb is None:
            textos = [c.text for c in chunks]
            if cache_dir:
                emb = self.encode_com_checkpoint(
                    textos, cache_dir, bloco=bloco, show_progress=show_progress, log=log
                )
            else:
                emb = self.encode(textos, self.passage_prefix, show_progress)
        else:
            log("    embeddings recuperados do cache (sem reencode)")

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
