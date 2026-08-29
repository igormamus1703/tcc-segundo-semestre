"""Contrato compartilhado entre segmenter, chunkers e indexing.

`section` é None para fixed e recursive; structural sempre o preenche.
Isso permite fazer análise por seção também nas baselines, mapeando o
offset (start, end) do chunk fixo/recursivo contra os spans rotulados
pelo segmenter (ver seção 1 do plano_tecnico.md).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

Section = Literal["ementa", "relatorio", "fundamentacao", "dispositivo"]


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str  # chave da agregação chunk -> documento
    text: str
    section: Section | None
    start: int
    end: int


@dataclass
class Document:
    doc_id: str
    text: str
    # spans ouro (colunas do CSV do TCU), só usado por
    # StructuralChunker(span_source="gold") — ver corpus_docs.jsonl.
    gold_spans: list[dict] | None = None


class Chunker(ABC):
    """Interface comum às três estratégias (fixed, recursive, structural)."""

    @abstractmethod
    def chunk(self, doc: Document) -> list[Chunk]:
        raise NotImplementedError
