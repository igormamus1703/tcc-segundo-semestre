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
