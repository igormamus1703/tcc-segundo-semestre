"""F7 — ranker aprendido: os atributos e a separação treino/validação.

Os erros que contam aqui são silenciosos por natureza:

- uma consulta cair no treino E na validação (o early stopping passa a medir
  o que já viu, e o número de validação infla);
- a linha i da matriz não corresponder ao (consulta, documento) i das chaves
  (o run gravado reordena os documentos errados);
- um documento ausente de um sinal receber score/posição de "presente".
"""

import numpy as np

from src.ltr import (
    AUSENTE,
    POOL,
    candidatos,
    dividir_por_consulta,
    matriz,
    nomes_atributos,
    normalizar,
    run_do_modelo,
)


def test_normalizar_da_score_minmax_e_posicao_com_desempate_por_doc():
    norm, pos = normalizar({"b": 2.0, "a": 2.0, "c": 0.0})
    assert norm == {"a": 1.0, "b": 1.0, "c": 0.0}
    assert pos == {"a": 1, "b": 2, "c": 3}  # empate desfeito por doc_id, fixo


def test_normalizar_corta_antes_do_minmax():
    # 1.000 documentos com scores 1000..1: o top-3 normalizado tem de ir de 1
    # a 0 dentro do próprio top, e não ficar espremido perto de 1
    docs = {f"d{i:04d}": float(1000 - i) for i in range(1000)}
    norm, pos = normalizar(docs, topo=3)
    assert set(norm) == {"d0000", "d0001", "d0002"}
    assert norm["d0002"] == 0.0 and norm["d0000"] == 1.0
    assert max(pos.values()) == 3


def test_candidatos_sao_a_uniao_dos_sinais_pool_sem_repetir():
    sinais = {POOL[0]: {"1": {"a": 3, "b": 2}}, POOL[2]: {"1": {"b": 5, "c": 1}},
              "bm25_relatorio": {"1": {"z": 9}}}  # não-pool não traz candidato
    assert candidatos(sinais, "1") == ["a", "b", "c"]


def test_matriz_alinha_linhas_chaves_e_rotulos_e_marca_ausentes():
    sinais = {"bm25_doc": {"1": {"a": 2.0, "b": 1.0}}, "dense_doc": {"1": {"b": 0.9}}}
    usar = ["bm25_doc", "dense_doc"]
    X, y, grupos, chaves = matriz(sinais, usar, ["1"], {"1": "tres palavras aqui"},
                                  {"a": (5.0, 0.7)}, {"1": {"b": 1}})
    assert grupos == [2]
    assert chaves == [("1", "a"), ("1", "b")]
    assert list(y) == [0, 1]
    nomes = nomes_atributos(usar)
    linha_a = dict(zip(nomes, X[0]))
    assert linha_a["dense_doc__posicao"] == AUSENTE    # a não está no denso
    assert linha_a["dense_doc__score"] == 0.0
    assert linha_a["bm25_doc__posicao"] == 1
    assert linha_a["doc_fracao_relatorio"] == np.float32(0.7)
    assert "consulta_palavras" not in nomes


def test_treino_e_validacao_nunca_compartilham_consulta():
    qids = [str(i) for i in range(1000)]
    tr, va = dividir_por_consulta(qids, 0.15)
    assert not set(tr) & set(va)
    assert len(va) == 150 and len(tr) + len(va) == 1000
    # e a divisão não depende da ordem de entrada
    assert dividir_por_consulta(list(reversed(qids)), 0.15) == (tr, va)


def test_run_do_modelo_respeita_as_chaves():
    run = run_do_modelo([("1", "a"), ("1", "b"), ("2", "a")], np.array([0.1, 0.9, 0.5]))
    assert run == {"1": {"a": 0.1, "b": 0.9}, "2": {"a": 0.5}}
