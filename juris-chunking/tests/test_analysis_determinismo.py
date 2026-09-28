"""`per_query_scores` tem de dar o mesmo numero sempre.

Este arquivo existe por causa de um bug real encontrado em 28/09: o recorte
"consulta real de log" do MESMO arquivo TREC deu 0,1322 numa tabela e 0,1336
em outra. Nao era aleatoriedade nem erro de indice: era EMPATE DE SCORE na
fronteira do corte da metrica.

Na consulta 6 do corpus, tres documentos empatam em 5,295338 e ocupam as
posicoes 9, 10 e 11 — e um dos tres e relevante (nivel 3). Se ele fica em 9 ou
10, a consulta vale 0,066; se e empurrado para 11, vale 0. O ranx nao fixa o
desempate, e a ordem que ele usa muda conforme o objeto `Run` ja ter sido
avaliado antes: `Run.sort()` reordena por valor com um sort instavel, e
reordenar o que ja estava ordenado permuta os empatados.

O efeito e minusculo (uma consulta em 150) e invisivel na media global, porque
o score entra na soma dos dois jeitos. Ele so aparece nos RECORTES, onde cada
consulta vai para um grupo. Ou seja: passa despercebido e vai para o artigo.

**A fixture e dados reais.** Reproduzir isso sinteticamente nao funcionou: com
um punhado de documentos o numpy usa insertion sort, que e estavel, e o bug
nao aparece. `tests/dados/empate_*.trec` sao as 20 primeiras posicoes das
consultas 1 e 6 da rodada `20260906-0515_bm25`, que e o menor recorte que
ainda reproduz.
"""

from pathlib import Path

import pytest

from src.analysis import per_query_scores, slice_by_query_type
from src.evaluate import evaluate_runs, load_qrels, load_run

DADOS = Path(__file__).parent / "dados"


@pytest.fixture
def qrels():
    return load_qrels(DADOS / "empate_qrels.trec")


@pytest.fixture
def carregar_run():
    # Uma FUNCAO, nao um Run: cada teste precisa de objetos novos, porque o
    # que esta em jogo e justamente o estado que fica no objeto.
    return lambda: load_run(DADOS / "empate_run.trec", name="fixture")


def test_avaliar_o_mesmo_run_duas_vezes_da_o_mesmo_numero(qrels, carregar_run):
    r = carregar_run()
    assert per_query_scores(qrels, r) == per_query_scores(qrels, r)


def test_resultado_nao_muda_se_o_run_ja_passou_por_evaluate_runs(qrels, carregar_run):
    """O caminho exato do bug: `evaluate.main` avalia todos os runs (etapa 1) e
    so depois calcula os recortes (etapa 3). O estado deixado pela primeira
    etapa vazava para a terceira."""
    esperado = per_query_scores(qrels, carregar_run())

    alvo = carregar_run()
    evaluate_runs(qrels, [alvo])
    assert per_query_scores(qrels, alvo) == esperado


def test_resultado_nao_muda_com_a_ordem_das_chamadas(qrels, carregar_run):
    from src.evaluate import paired_significance

    esperado = per_query_scores(qrels, carregar_run())

    a, b = carregar_run(), carregar_run()
    evaluate_runs(qrels, [a, b])
    paired_significance(qrels, [a, b])
    assert per_query_scores(qrels, a) == esperado


def test_consulta_do_empate_recebe_sempre_o_mesmo_score(qrels, carregar_run):
    """A consulta 6 e a que tem o empate na fronteira do top-10. Fixar o valor
    faz o teste falhar se alguem trocar o criterio de desempate sem perceber
    que isso muda numeros ja publicados."""
    alvo = carregar_run()
    evaluate_runs(qrels, [alvo])
    assert per_query_scores(qrels, alvo)["6"] == pytest.approx(0.063621, abs=1e-6)


def test_nao_altera_o_run_do_chamador(qrels, carregar_run):
    """`make_comparable` do ranx mexe no objeto recebido. Uma funcao de LEITURA
    nao pode deixar o run do chamador diferente do que era."""
    r = carregar_run()
    antes = r.to_dict()
    per_query_scores(qrels, r)
    assert r.to_dict() == antes


def test_recorte_e_estavel_entre_avaliacoes(qrels, carregar_run):
    """O sintoma como ele apareceu: o mesmo run, o mesmo recorte, dois
    numeros."""
    meta = {"6": "search log", "1": "LLM"}

    antes = slice_by_query_type(qrels, [carregar_run()], meta, "ndcg@10")
    alvo = carregar_run()
    evaluate_runs(qrels, [alvo])
    depois = slice_by_query_type(qrels, [alvo], meta, "ndcg@10")

    assert [x["media"] for x in antes] == [x["media"] for x in depois]


def test_consulta_ausente_do_run_vale_zero(qrels):
    """Nao recuperar nada e falhar, nao e 'nao se aplica'. Se a consulta
    sumisse do dicionario, ela sairia da media e o numero subiria sozinho."""
    from ranx import Run

    parcial = Run({"1": {"397-2008-plenário": 1.0}}, name="parcial")
    scores = per_query_scores(qrels, parcial)
    assert set(scores) == {"1", "6"}
    assert scores["6"] == 0.0
