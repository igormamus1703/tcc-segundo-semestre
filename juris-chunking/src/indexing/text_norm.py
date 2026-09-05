"""Normalização de texto para o retriever léxico (F4).

Isolado num módulo próprio porque a mesma normalização precisa ser aplicada
aos chunks na indexação E às consultas na busca — se as duas divergirem, o
BM25 simplesmente não encontra os termos, e o erro é silencioso (recall cai,
nada quebra).
"""

from __future__ import annotations

import re
import unicodedata

# Stopwords do português. Lista embutida de propósito: o `nltk` traria uma
# dependência nova (e um download em runtime) para uma lista de 200 palavras
# que não muda.
STOPWORDS_PT: frozenset[str] = frozenset(
    """
    a as o os um uma uns umas ao aos à às da das do dos de dum duns duma dumas
    e ou nem mas porem porque pois se senao que quem qual quais cujo cuja cujos cujas
    em no nos na nas num nuns numa numas por pelo pela pelos pelas para
    com sem sob sobre entre ate apos ante contra desde perante tras
    eu tu ele ela nos vos eles elas me te lhe nos vos lhes se si consigo
    meu minha meus minhas teu tua teus tuas seu sua seus suas nosso nossa nossos nossas
    este esta estes estas esse essa esses essas aquele aquela aqueles aquelas
    isto isso aquilo tal tais
    ser sou es e somos sois sao era eras eramos eram foi fui foram fosse fossem
    ter tem tenho tens temos tendes tinha tinham tive teve tiveram tenha tenham
    haver ha hao havia haviam houve houveram
    estar esta estao estava estavam esteve estiveram
    ja mais menos muito muita muitos muitas pouco pouca poucos poucas
    todo toda todos todas outro outra outros outras mesmo mesma mesmos mesmas
    nao sim tambem so apenas ainda entao assim como quando onde onde quanto
    depois antes agora hoje aqui ali la
    """.split()
)


_WORD_RE = re.compile(r"[0-9a-z]+")


def strip_accents(text: str) -> str:
    """Remove diacríticos preservando o resto (NFKD + descarte de combining)."""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )


def normalize_for_bm25(text: str) -> list[str]:
    """lowercase -> sem acentos -> palavras -> sem stopwords.

    A remoção de acentos é importante no corpus do TCU: o mesmo termo aparece
    acentuado e não acentuado ao longo de 20 anos de publicação ("acórdão" /
    "acordao"), e sem isso viram termos distintos no índice.

    Números são preservados: em acórdão, referências como "9.1" ou o ano de um
    processo carregam sinal.
    """
    lowered = strip_accents(text.lower())
    return [tok for tok in _WORD_RE.findall(lowered) if tok not in STOPWORDS_PT]
