"""F7 — montagem dos exemplos do fine-tune do reranker.

O erro silencioso aqui é de rótulo: um "negativo" que é, na verdade, um trecho
do acórdão relevante ensina o modelo a rebaixar a resposta certa, e o treino
roda normalmente, só que piorando o modelo.
"""

from src.finetune_reranker import chunk_que_contem, grupo
from src.jua import ANCORA


def test_positivo_e_o_chunk_que_contem_o_meio_da_ancora():
    # janelas sobrepostas: [0,100), [50,150), [100,200)
    chunks = [{"chunk_id": f"c{i}", "start": s, "end": s + 100} for i, s in enumerate((0, 50, 100))]
    pos = 90 - ANCORA // 2  # o meio da âncora cai em 90
    assert chunk_que_contem(chunks, pos)["chunk_id"] in {"c0", "c1"}
    assert chunk_que_contem(chunks, 10_000) is None


def test_negativos_nunca_vem_do_documento_relevante():
    venc = [
        {"rank": 1, "doc_id": "REL", "chunk_id": "REL::3"},
        {"rank": 2, "doc_id": "X", "chunk_id": "X::1"},
        {"rank": 3, "doc_id": "Y", "chunk_id": "Y::9"},
    ]
    assert grupo("q", "REL", "REL::0", venc, k=2) == ["REL::0", "X::1", "Y::9"]


def test_grupo_incompleto_e_descartado():
    venc = [{"rank": 1, "doc_id": "X", "chunk_id": "X::1"}]
    assert grupo("q", "REL", "REL::0", venc, k=2) is None


def test_grupo_misto_tira_de_tres_fontes_sem_repetir_nem_usar_o_relevante():
    import random

    from src.finetune_reranker import grupo_misto
    bm25 = [{"rank": i, "doc_id": d, "chunk_id": f"{d}::1"} for i, d in enumerate(["REL", "A", "B", "C", "D"], 1)]
    denso = [{"rank": 1, "doc_id": "A", "chunk_id": "A::1"}, {"rank": 2, "doc_id": "E", "chunk_id": "E::2"},
             {"rank": 3, "doc_id": "F", "chunk_id": "F::3"}]
    aleat = ["REL::9", "X::1", "Y::1", "Z::1"]
    g = grupo_misto("REL", "REL::0", bm25, denso, aleat, 3, 2, 2, random.Random(0))
    assert g[0] == "REL::0" and len(g) == 8 and len(set(g)) == 8
    assert g[1:4] == ["A::1", "B::1", "C::1"]
    assert g[4:6] == ["E::2", "F::3"]  # A::1 já usado: o denso pula para o próximo
    assert not any(c.startswith("REL::") for c in g[1:])


def test_grupo_misto_incompleto_e_descartado():
    import random

    from src.finetune_reranker import grupo_misto
    assert grupo_misto("REL", "REL::0", [], [], ["X::1"], 3, 2, 2, random.Random(0)) is None
