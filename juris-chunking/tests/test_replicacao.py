"""F7 — estatística da replicação: efeito pareado, TOST e Bonferroni.

O TOST é o teste que mais facilmente sai invertido sem erro: trocar os dois
lados unilaterais dá um p que parece razoável e afirma equivalência onde não
há. Os testes abaixo usam casos em que a resposta certa é óbvia.
"""

import numpy as np

from src.replicacao import bonferroni, efeito_pareado, tost

QIDS = [str(i) for i in range(200)]


def _scores(valores):
    return {q: float(v) for q, v in zip(QIDS, valores)}


def test_efeito_pareado_mede_o_delta_e_o_ic_contem_o_verdadeiro():
    rng = np.random.default_rng(0)
    b = rng.uniform(0.1, 0.5, size=200)
    a = b + 0.05 + rng.normal(0, 0.02, size=200)
    e = efeito_pareado(_scores(a), _scores(b), QIDS)
    assert abs(e["delta"] - 0.05) < 0.01
    assert e["ic95_inf"] < 0.05 < e["ic95_sup"]
    assert e["p"] < 1e-10
    assert e["vitorias"] + e["empates"] + e["derrotas"] == 200


def test_tost_declara_equivalencia_quando_a_diferenca_e_minima():
    rng = np.random.default_rng(1)
    b = rng.uniform(0.1, 0.5, size=200)
    a = b + rng.normal(0, 0.01, size=200)  # média da diferença ~0, ruído pequeno
    r = tost(_scores(a), _scores(b), QIDS, margem=0.01)
    assert r["equivalente"]
    assert -0.01 < r["ic90_inf"] and r["ic90_sup"] < 0.01


def test_tost_recusa_equivalencia_quando_a_diferenca_passa_da_margem():
    rng = np.random.default_rng(2)
    b = rng.uniform(0.1, 0.5, size=200)
    a = b + 0.03 + rng.normal(0, 0.01, size=200)
    r = tost(_scores(a), _scores(b), QIDS, margem=0.01)
    assert not r["equivalente"]
    assert r["p_tost"] > 0.5


def test_tost_recusa_equivalencia_quando_falta_poder():
    # diferença média zero, mas ruído enorme e poucas consultas: o IC 90%
    # não cabe na margem, e "não significativo" NÃO pode virar "equivalente"
    rng = np.random.default_rng(3)
    q = QIDS[:10]
    b = rng.uniform(0, 1, size=10)
    a = b + rng.normal(0, 0.3, size=10)
    r = tost(_scores(a), _scores(b), q, margem=0.01)
    assert not r["equivalente"]


def test_bonferroni_multiplica_e_satura_em_um():
    assert bonferroni([0.01, 0.2, 0.5]) == [0.03, 0.6000000000000001, 1.0]
