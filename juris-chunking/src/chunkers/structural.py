"""Chunker estrutural: nunca cruza fronteira de macro-seção.

Duas variantes de run (seção F3 do plano_implementacao.md), escolhidas por
`span_source`:
- `"gold"`: usa `doc.gold_spans` (as colunas do CSV do TCU, gravadas em
  `corpus_docs.jsonl` por `ingest.py`) — a ablação ideal, sem erro de
  segmentação.
- `"pred"`: roda `segmenter.segment(doc.doc_id, doc.text)` — o que um
  pipeline real teria disponível num corpus sem estrutura ouro.

Se uma seção exceder `max_section_tokens`, subdivide em subjanelas com
overlap (mesma lógica de `tokenization.token_windows`, restrita ao span),
propagando o rótulo da seção para cada subchunk. `"indefinido"` (fallback
do segmenter — ver `segmenter/rules.py`) vira `section=None` no Chunk,
igual ao fixed/recursive: não é uma seção conhecida, então não recebe um
rótulo emprestado.
"""

from __future__ import annotations

from ..segmenter.rules import FALLBACK_LABEL
from ..tokenization import token_windows
from .base import Chunk, Chunker, Document


class StructuralChunker(Chunker):
    def __init__(
        self,
        max_section_tokens: int,
        overlap: int,
        span_source: str,
        segmenter=None,
        name: str = "structural",
    ):
        if span_source not in ("gold", "pred"):
            raise ValueError("span_source deve ser 'gold' ou 'pred'")
        if span_source == "pred" and segmenter is None:
            raise ValueError("segmenter é obrigatório quando span_source='pred'")
        if overlap < 0 or overlap >= max_section_tokens:
            raise ValueError("overlap deve estar em [0, max_section_tokens)")
        self.max_section_tokens = max_section_tokens
        self.overlap = overlap
        self.span_source = span_source
        self.segmenter = segmenter
        self.name = name

    def _labeled_spans(self, doc: Document) -> list[tuple[str, int, int]]:
        if self.span_source == "gold":
            if doc.gold_spans is None:
                raise ValueError(
                    f"doc {doc.doc_id!r} sem gold_spans (span_source='gold')"
                )
            return [(s["section"], s["start"], s["end"]) for s in doc.gold_spans]
        return [(s.section, s.start, s.end) for s in self.segmenter.segment(doc.doc_id, doc.text)]

    def chunk(self, doc: Document) -> list[Chunk]:
        stride = self.max_section_tokens - self.overlap
        chunks: list[Chunk] = []
        for section, span_start, span_end in self._labeled_spans(doc):
            label = None if section == FALLBACK_LABEL else section
            section_text = doc.text[span_start:span_end]
            for w_start, w_end in token_windows(section_text, self.max_section_tokens, stride):
                start, end = span_start + w_start, span_start + w_end
                chunks.append(
                    Chunk(
                        chunk_id=f"{doc.doc_id}::{self.name}::{len(chunks):04d}",
                        doc_id=doc.doc_id,
                        text=doc.text[start:end],
                        section=label,
                        start=start,
                        end=end,
                    )
                )
        return chunks
