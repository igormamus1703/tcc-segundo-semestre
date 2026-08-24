"""Chunker estrutural: nunca cruza fronteira de macro-seção.

Depende da saída do segmenter (List[LabeledSpan]). Se uma seção exceder
max_section_tokens, subdivide internamente e propaga o rótulo da seção
para cada subchunk.
"""

from __future__ import annotations

from .base import Chunk, Chunker, Document


class StructuralChunker(Chunker):
    def __init__(self, max_section_tokens: int, overlap: int, segmenter):
        self.max_section_tokens = max_section_tokens
        self.overlap = overlap
        self.segmenter = segmenter  # instância de segmenter.segment.Segmenter

    def chunk(self, doc: Document) -> list[Chunk]:
        raise NotImplementedError(
            "TODO (Semana 6): obter spans rotulados via self.segmenter, "
            "para cada span dentro do limite emitir 1 Chunk com section "
            "preenchido; se exceder max_section_tokens, subdividir e "
            "propagar o mesmo rótulo para os subchunks."
        )
