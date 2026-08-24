"""Wrapper sobre RecursiveCharacterTextSplitter (langchain-text-splitters)
com separadores jurídicos. `section` sempre None (ver base.py)."""

from __future__ import annotations

from .base import Chunk, Chunker, Document


class RecursiveChunker(Chunker):
    def __init__(self, chunk_size: int, chunk_overlap: int, separators: list[str]):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators

    def chunk(self, doc: Document) -> list[Chunk]:
        raise NotImplementedError(
            "TODO (Semana 6): usar langchain_text_splitters."
            "RecursiveCharacterTextSplitter com self.separators, recuperar "
            "offsets e devolver List[Chunk]."
        )
