"""F6 — validacao cruzada para escolher o peso da fusao.

O bug que estes testes procuram nao e uma excecao: e VAZAMENTO. Se a consulta
de teste participar da escolha do peso, o numero sobe, nada falha, e o
resultado vira ajuste no conjunto de teste disfarcado de achado.
"""

import numpy as np
import pytest
from ranx import Qrels

from src.tuning import ResultadoCV, dobras, validacao_cruzada


def qrels_sinteticos(n_queries=20):
    return Qrels({f"q{i}": {f"d{i}": 1} for i in range(n_queries)})


def rankings_complementares(n_queries=20):
    """Dois retrievers que erram de formas DIFERENTES.

    Cada um poe o documento certo em 2o lugar, mas atras de um distrator
    distinto. E o cenario que justifica fundir: o distrator de um e afundado
    pelo outro, e o documento certo — o unico que os dois gostam — sobe para o
    1o lugar. Com os dois errando junto, nenhuma fusao poderia ajudar, e um
    teste que passasse assim nao estaria medindo nada.

    Note que os scores sao deliberadamente assimetricos (10/9/1 contra
    0,9/0,8/0,1): com dois documentos so, a normalizacao min-max manda um para
    1,0 e outro para 0,0, tudo empata em 0,5 e o teste passaria a medir o
    criterio de desempate do sort.
    """
    bm25, denso = {}, {}
    for i in range(n_queries):
        certo, distrator_lex, distrator_sem = f"d{i}", f"x{i}", f"y{i}"
        bm25[f"q{i}"] = {distrator_lex: 10.0, certo: 9.0, distrator_sem: 1.0}
        denso[f"q{i}"] = {distrator_sem: 0.9, certo: 0.8, distrator_lex: 0.1}
    return bm25, denso


# --- particao ---------------------------------------------------------------

def test_dobras_cobrem_todas_as_consultas_sem_repetir():
    qids = [f"q{i}" for i in range(17)]  # numero primo: nao divide igual
    partes = dobras(qids, n_folds=5)
    juntas = [q for p in partes for q in p]
    assert sorted(juntas) == sorted(qids)
    assert len(juntas) == len(set(juntas))


def test_dobras_sao_reprodutiveis_com_a_mesma_semente():
    """Sem semente fixa, dois autores rodando o mesmo comando publicariam
    numeros diferentes e nenhum saberia por que."""
    qids = [f"q{i}" for i in range(20)]
    assert dobras(qids, 4, seed=7) == dobras(qids, 4, seed=7)
    assert dobras(qids, 4, seed=7) != dobras(qids, 4, seed=8)


def test_dobras_nao_dependem_da_ordem_de_entrada():
    """A lista de consultas vem de um dict; sua ordem nao pode mudar a
    particao, senao a CV deixa de ser reprodutivel entre execucoes."""
    qids = [f"q{i}" for i in range(20)]
    assert dobras(qids, 4, seed=1) == dobras(list(reversed(qids)), 4, seed=1)


# --- vazamento --------------------------------------------------------------

def test_consulta_de_teste_nao_participa_da_escolha_do_peso(monkeypatch):
    """O teste central do modulo: registramos quais consultas foram usadas
    para pontuar cada candidato e exigimos que a dobra de teste nunca apareca
    entre elas."""
    import src.tuning as tuning

    bm25, denso = rankings_complementares()
    qrels = qrels_sinteticos()

    vistos: list[set[str]] = []
    original = tuning._pontuar

    def espiao(qrels_, ranking, qids, metric):
        vistos.append(set(qids))
        return original(qrels_, ranking, qids, metric)

    monkeypatch.setattr(tuning, "_pontuar", espiao)
    resultado = validacao_cruzada(qrels, bm25, denso, n_folds=4)

    partes = dobras(sorted(qrels.to_dict()), 4, seed=42)
    grade = tuning.GRADE_SOMA_NORM
    # Por dobra: len(grade) chamadas de SELECAO (treino) + 2 de medicao.
    por_dobra = len(grade) + 2
    for i, teste in enumerate(partes):
        selecao = vistos[i * por_dobra: i * por_dobra + len(grade)]
        for usados in selecao:
            assert not (set(teste) & usados), (
                f"dobra {i}: consultas de teste entraram na selecao do peso"
            )
    assert len(resultado.scores_teste) == len(qrels.to_dict())


def test_cada_consulta_e_pontuada_exatamente_uma_vez():
    """Se uma consulta aparecesse em duas dobras de teste, ela pesaria o dobro
    na media final."""
    bm25, denso = rankings_complementares(20)
    r = validacao_cruzada(qrels_sinteticos(20), bm25, denso, n_folds=5)
    assert len(r.scores_teste) == 20
    assert set(r.scores_teste) == set(r.scores_baseline)


# --- comportamento ----------------------------------------------------------

def test_fusao_ganha_quando_os_retrievers_sao_complementares():
    bm25, denso = rankings_complementares(20)
    r = validacao_cruzada(qrels_sinteticos(20), bm25, denso, n_folds=5)
    assert r.media > r.media_baseline
    assert r.ganho_relativo > 0


def test_baseline_medido_nas_mesmas_consultas_de_teste():
    """Comparar a media da CV com a media global do BM25 compararia dois
    numeros calculados sobre conjuntos diferentes."""
    bm25, denso = rankings_complementares(20)
    r = validacao_cruzada(qrels_sinteticos(20), bm25, denso, n_folds=5)
    assert set(r.scores_teste) == set(r.scores_baseline)
    assert r.teste_pareado()["n_queries"] == 20


def test_peso_estavel_detecta_escolha_divergente_entre_dobras():
    r = ResultadoCV(metodo="soma_norm", metric="ndcg@10", n_folds=3)
    r.pesos_escolhidos = [0.7, 0.7, 0.7]
    assert r.peso_estavel
    r.pesos_escolhidos = [0.7, 0.8, 0.7]
    assert not r.peso_estavel


def test_rrf_tambem_e_suportado():
    bm25, denso = rankings_complementares(20)
    r = validacao_cruzada(qrels_sinteticos(20), bm25, denso, metodo="rrf", n_folds=5)
    assert r.metodo == "rrf"
    assert all(p in (1.0, 1.5, 2.0, 3.0, 5.0) for p in r.pesos_escolhidos)


def test_recusa_menos_consultas_que_dobras():
    bm25, denso = rankings_complementares(3)
    with pytest.raises(ValueError, match="dobras"):
        validacao_cruzada(qrels_sinteticos(3), bm25, denso, n_folds=5)


def test_teste_pareado_conta_vitorias_empates_e_derrotas():
    r = ResultadoCV(metodo="soma_norm", metric="ndcg@10", n_folds=2)
    r.scores_teste = {"q1": 1.0, "q2": 0.0, "q3": 0.5}
    r.scores_baseline = {"q1": 0.0, "q2": 1.0, "q3": 0.5}
    t = r.teste_pareado()
    assert (t["vitorias"], t["empates"], t["derrotas"]) == (1, 1, 1)
    assert np.isfinite(t["p_value"])


# --- selecao de CONFIGURACAO por CV -----------------------------------------

def candidatos_sinteticos(n_queries=20):
    """Tres configuracoes: uma boa, uma ruim e uma que so parece boa por acaso
    num subconjunto pequeno de consultas."""
    qrels = qrels_sinteticos(n_queries)
    bom, ruim, sortudo = {}, {}, {}
    for i in range(n_queries):
        certo, errado = f"d{i}", f"x{i}"
        bom[f"q{i}"] = {certo: 2.0, errado: 1.0}
        ruim[f"q{i}"] = {errado: 2.0, certo: 1.0}
        # acerta so nas 3 primeiras consultas
        sortudo[f"q{i}"] = {certo: 2.0, errado: 1.0} if i < 3 else {errado: 2.0, certo: 1.0}
    return qrels, {"bom": bom, "ruim": ruim, "sortudo": sortudo}


def test_selecao_escolhe_a_configuracao_boa_e_mede_fora_dela():
    from src.tuning import selecao_por_cv

    qrels, cands = candidatos_sinteticos(20)
    r = selecao_por_cv(qrels, cands, baseline="ruim", n_folds=5)
    assert r.escolha_estavel and set(r.escolhidas) == {"bom"}
    assert r.media > r.media_baseline
    assert r.teste_pareado()["p_value"] < 0.05


def test_selecao_nao_premia_quem_so_acerta_no_treino():
    """O ponto do metodo: uma configuracao que parece boa por acaso nao pode
    levar credito nas consultas que nao participaram da escolha."""
    from src.tuning import selecao_por_cv

    qrels, cands = candidatos_sinteticos(20)
    del cands["bom"]  # sobram 'ruim' e 'sortudo'
    r = selecao_por_cv(qrels, cands, baseline="ruim", n_folds=5)
    # 'sortudo' so ganha em 3 de 20 consultas: mesmo se escolhido em alguma
    # dobra, o ganho medido fora dela e pequeno.
    assert r.ganho_relativo < 0.30


def test_selecao_pontua_cada_consulta_uma_vez_so():
    from src.tuning import selecao_por_cv

    qrels, cands = candidatos_sinteticos(20)
    r = selecao_por_cv(qrels, cands, baseline="ruim", n_folds=5)
    assert len(r.scores_teste) == 20
    assert set(r.scores_teste) == set(r.scores_baseline)


def test_selecao_recusa_baseline_fora_dos_candidatos():
    from src.tuning import selecao_por_cv

    qrels, cands = candidatos_sinteticos(20)
    with pytest.raises(ValueError, match="baseline"):
        selecao_por_cv(qrels, cands, baseline="inexistente")
