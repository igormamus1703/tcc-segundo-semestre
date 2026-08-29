"""Chunker de janela deslizante (tamanho/stride parametrizáveis).

Baseline sem consciência estrutural. `section` sempre None — a análise
por seção, quando necessária, é feita a posteriori mapeando (start, end)
contra os spans do segmenter.
"""

from __future__ import annotations

from ..tokenization import token_windows
from .base import Chunk, Chunker, Document


class FixedChunker(Chunker):
    def __init__(self, size: int, stride: int, name: str = "fixed"):
        if stride <= 0 or stride > size:
            raise ValueError("stride deve estar em (0, size]")
        self.size = size
        self.stride = stride
        self.name = name

    def chunk(self, doc: Document) -> list[Chunk]:
        return [
            Chunk(
                chunk_id=f"{doc.doc_id}::{self.name}::{i:04d}",
                doc_id=doc.doc_id,
                text=doc.text[start:end],
                section=None,
                start=start,
                end=end,
            )
            for i, (start, end) in enumerate(token_windows(doc.text, self.size, self.stride))
        ]
