"""Chunker de janela deslizante (tamanho/stride parametrizáveis).

Baseline sem consciência estrutural. `section` sempre None — a análise
por seção, quando necessária, é feita a posteriori mapeando (start, end)
contra os spans do segmenter.
"""

from __future__ import annotations

from .base import Chunk, Chunker, Document


class FixedChunker(Chunker):
    def __init__(self, size: int, stride: int, tokenizer=None):
        if stride <= 0 or stride > size:
            raise ValueError("stride deve estar em (0, size]")
        self.size = size
        self.stride = stride
        self.tokenizer = tokenizer  # ver configs/chunkers.yaml: tokenizer

    def chunk(self, doc: Document) -> list[Chunk]:
        raise NotImplementedError(
            "TODO (Semana 6): tokenizar doc.text, janelar por (size, stride) "
            "e devolver List[Chunk] com offsets (start, end) em caracteres."
        )
