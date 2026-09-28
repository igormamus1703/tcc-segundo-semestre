"""F6 — fusão de rankings (RRF e soma normalizada).

O risco silencioso aqui é de ESCALA: BM25 devolve scores na casa das dezenas e
o cosseno na casa do 0,x. Uma fusão que some os dois crus é dominada pelo BM25
sem que nada falhe — a métrica simplesmente sai igual à do BM25 sozinho, e
alguém conclui que "a fusão não ajudou".
"""

import pytest

from src.fusion import (
    agrupar_por_estrategia,
    escrever_trec,
    ler_trec,
    rrf,
    soma_normalizada,
)


def test_rrf_usa_posicao_e_nao_score():
    """O ranking A tem scores gigantes; se o RRF olhasse magnitude, A dominaria.
    Olhando posição, o documento que os dois põem em 2º ganha do que só A põe
    em 1º... ou não — o que o teste fixa é que o resultado NÃO depende da
    escala de A."""
    a = {"q1": {"d1": 1000.0, "d2": 999.0}}
    b = {"q1": {"d2": 0.9, "d3": 0.1}}
    fundido = rrf([a, b], k=60)

    a_escalado = {"q1": {"d1": 1.0, "d2": 0.999}}
    assert rrf([a_escalado, b], k=60) == fundido


def test_rrf_premia_quem_aparece_nos_dois_rankings():
    a = {"q1": {"d1": 10.0, "d2": 9.0}}
    b = {"q1": {"d2": 0.9, "d3": 0.8}}
    fundido = rrf([a, b], k=60)
    # d2: 1/62 + 1/61 ; d1: 1/61 ; d3: 1/62
    assert fundido["q1"]["d2"] > fundido["q1"]["d1"] > fundido["q1"]["d3"]


def test_rrf_com_peso_favorece_o_retriever_mais_forte():
    """Peso é o parâmetro que permite testar 'BM25 vence o denso, então deve
    pesar mais na fusão' — que é a hipótese natural dado o resultado da F5."""
    a = {"q1": {"d1": 10.0}}
    b = {"q1": {"d2": 0.9}}
    fundido = rrf([a, b], k=60, pesos=[2.0, 1.0])
    assert fundido["q1"]["d1"] > fundido["q1"]["d2"]


def test_rrf_recusa_numero_de_pesos_diferente_do_de_rankings():
    with pytest.raises(ValueError, match="pesos"):
        rrf([{"q1": {"d1": 1.0}}], pesos=[1.0, 1.0])


def test_soma_normalizada_iguala_escalas():
    """Sem min-max, o BM25 (dezenas) abafaria o cosseno (0,x) e a fusão seria
    o BM25 com passos extras."""
    bm25 = {"q1": {"d1": 30.0, "d2": 10.0}}
    denso = {"q1": {"d2": 0.9, "d1": 0.1}}
    fundido = soma_normalizada([bm25, denso])
    # d1: 1.0 + 0.0 ; d2: 0.0 + 1.0 — empate, que é a leitura correta de dois
    # retrievers que discordam com a mesma convicção.
    assert fundido["q1"]["d1"] == pytest.approx(fundido["q1"]["d2"])


def test_soma_normalizada_nao_produz_nan_quando_todos_os_scores_sao_iguais():
    """Denominador zero. NaN aqui se propaga até a métrica final sem erro."""
    plano = {"q1": {"d1": 5.0, "d2": 5.0}}
    fundido = soma_normalizada([plano])
    assert all(v == 0.5 for v in fundido["q1"].values())


def test_agrupar_por_estrategia_casa_bm25_com_denso(tmp_path):
    caminhos = [
        tmp_path / "structural_gold__bm25.trec",
        tmp_path / "structural_gold__dense-bge_m3.trec",
        tmp_path / "fixed_512_256__bm25.trec",
    ]
    grupos = agrupar_por_estrategia(caminhos)
    assert len(grupos["structural_gold"]) == 2
    assert len(grupos["fixed_512_256"]) == 1


def test_ida_e_volta_trec_preserva_o_ranking(tmp_path):
    """O arquivo TREC é o artefato que o artigo cita; se a escrita reordenasse
    ou truncasse, o número publicado não corresponderia ao medido."""
    ranking = {"q1": {"d1": 0.9, "d2": 0.5}, "q2": {"d3": 0.7}}
    caminho = tmp_path / "r.trec"
    escrever_trec(caminho, ranking, "teste")
    assert ler_trec(caminho) == ranking


def test_escrever_trec_respeita_top_docs(tmp_path):
    ranking = {"q1": {f"d{i}": float(100 - i) for i in range(10)}}
    caminho = tmp_path / "r.trec"
    escrever_trec(caminho, ranking, "teste", top_docs=3)
    lido = ler_trec(caminho)
    assert list(lido["q1"]) == ["d0", "d1", "d2"]
