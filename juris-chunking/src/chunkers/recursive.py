"""Wrapper sobre RecursiveCharacterTextSplitter (langchain-text-splitters)
com separadores genéricos de texto corrido. `section` sempre None (ver
base.py) — ao contrário de `structural.py`, este chunker não tem acesso
à estrutura do acórdão, de propósito: é a baseline "estrutura-cega" com a
qual `structural_pred`/`structural_gold` são comparados.

Offsets recuperados via `str.find` com cursor móvel (não pelo
`add_start_index` nativo do `TextSplitter`): esse recurso do LangChain
calcula o piso de busca como `posição_anterior + len(chunk_anterior) -
chunk_overlap`, assumindo que `chunk_overlap` está na MESMA unidade de
`len(chunk)` (caracteres) — mas aqui `length_function=count_tokens`, então
`chunk_overlap` é uma contagem de TOKENS. Misturar as unidades faz o piso
ficar muito à frente da posição real e `find` falha (medido: 51 de 132
chunks com offset errado num smoke test no corpus real). A alternativa
abaixo usa como piso o INÍCIO do chunk anterior — sempre ≤ à posição real
do próximo (o overlap nunca ultrapassa o começo do chunk anterior) — e
não depende de conhecer o overlap em nenhuma unidade específica.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..tokenization import count_tokens
from .base import Chunk, Chunker, Document


class RecursiveChunker(Chunker):
    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        separators: list[str],
        name: str = "recursive",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators
        self.name = name
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=count_tokens,
        )

    def chunk(self, doc: Document) -> list[Chunk]:
        pieces = self._splitter.split_text(doc.text)
        chunks: list[Chunk] = []
        floor = 0
        for i, piece in enumerate(pieces):
            start = doc.text.find(piece, floor)
            if start == -1:
                start = doc.text.find(piece)
            if start == -1:
                raise ValueError(
                    f"pedaço {i} do RecursiveCharacterTextSplitter não encontrado "
                    f"em doc.text (doc_id={doc.doc_id!r})"
                )
            end = start + len(piece)
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}::{self.name}::{i:04d}",
                    doc_id=doc.doc_id,
                    text=piece,
                    section=None,
                    start=start,
                    end=end,
                )
            )
            floor = start  # próximo piso: início deste chunk, nunca depois
        return chunks
