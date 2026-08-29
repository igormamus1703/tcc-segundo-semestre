"""Tokenização única do pipeline: tiktoken `cl100k_base` (seção 2 do
plano_implementacao.md — todo módulo que precisa contar ou janelar por
token importa daqui, nunca chama tiktoken direto).
"""

from __future__ import annotations

import bisect

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def token_windows(text: str, size: int, stride: int) -> list[tuple[int, int]]:
    """Janelas de até `size` tokens, passo `stride`, como offsets de
    CARACTERE `(start, end)` em `text` (não offsets de token nem de byte).
    A janela final, mesmo parcial, é incluída.

    Um token do BPE pode terminar no meio de um caractere multi-byte
    (comum com acentuação em UTF-8): os limites de janela são calculados
    por BYTE, a partir do comprimento de cada token
    (`decode_tokens_bytes`), e só então convertidos para o caractere mais
    próximo via busca binária sobre os offsets de byte de cada caractere
    de `text` — nunca corta um caractere ao meio, mesmo que isso desloque
    o limite da janela por 1 token de vez em quando.
    """
    if size <= 0 or stride <= 0 or stride > size:
        raise ValueError("stride deve estar em (0, size]")
    if not text:
        return []

    tokens = _ENCODING.encode(text)
    if not tokens:
        return []

    token_byte_offsets = [0]
    for token_bytes in _ENCODING.decode_tokens_bytes(tokens):
        token_byte_offsets.append(token_byte_offsets[-1] + len(token_bytes))

    char_byte_offsets = [0]
    for ch in text:
        char_byte_offsets.append(char_byte_offsets[-1] + len(ch.encode("utf-8")))

    def byte_to_char(byte_offset: int) -> int:
        return min(bisect.bisect_left(char_byte_offsets, byte_offset), len(text))

    windows: list[tuple[int, int]] = []
    n = len(tokens)
    i = 0
    while i < n:
        j = min(i + size, n)
        windows.append((byte_to_char(token_byte_offsets[i]), byte_to_char(token_byte_offsets[j])))
        if j == n:
            break
        i += stride
    return windows
