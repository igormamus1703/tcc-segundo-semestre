import pytest
from ranx import Qrels, Run

from src.analysis import (
    bootstrap_ci,
    doc_length_terciles,
    per_query_scores,
    query_length_terciles,
    slice_by_doc_length_tercile,
    slice_by_query_type,
    slice_by_retriever,
)
from src.evaluate import (
    DEFAULT_METRICS,
    evaluate_run,
    evaluate_runs,
    load_qrels,
    load_run,
    paired_significance,
    significance_rows,
)


@pytest.fixture
def qrels():
    return Qrels({f"q{i}": {f"d{i}": 3} for i in range(20)})


@pytest.fixture
def run_bom():
    # relevante sempre em 1o lugar
    return Run(
        {f"q{i}": {f"d{i}": 0.9, f"x{i}": 0.1} for i in range(20)},
        name="structural_gold__bm25",
    )


@pytest.fixture
def run_ruim():
    # relevante sempre em 2o lugar
    return Run(
        {f"q{i}": {f"x{i}": 0.9, f"d{i}": 0.1} for i in range(20)},
        name="fixed_512_256__bm25",
    )


def test_evaluate_run_devolve_as_quatro_metricas(qrels, run_bom):
    scores = evaluate_run(qrels, run_bom)
    assert set(scores) == set(DEFAULT_METRICS)
    assert scores["ndcg@10"] == pytest.approx(1.0)


def test_evaluate_runs_quebra_nome_em_colunas(qrels, run_bom, run_ruim):
    linhas = evaluate_runs(qrels, [run_bom, run_ruim])
    assert linhas[0]["estrategia"] == "structural_gold"
    assert linhas[0]["retriever"] == "bm25"
    assert linhas[0]["agregacao"] == "max_pooling"
    # run melhor tem nDCG maior — sanidade da direção da métrica
    assert linhas[0]["ndcg@10"] > linhas[1]["ndcg@10"]


def test_evaluate_runs_le_agregacao_do_nome(qrels):
    run = Run({"q0": {"d0": 1.0}}, name="recursive_default__dense__sum_top_k")
    linha = evaluate_runs(qrels, [run])[0]
    assert linha["estrategia"] == "recursive_default"
    assert linha["retriever"] == "dense"
    assert linha["agregacao"] == "sum_top_k"


def test_significance_rows_tem_uma_linha_por_par(qrels, run_bom, run_ruim):
    report = paired_significance(qrels, [run_bom, run_ruim])
    linhas = significance_rows(report)
    assert len(linhas) == 1
    linha = linhas[0]
    assert linha["p_value"] < 0.05
    assert linha["significativo_p<0.05"] is True
    # o run melhor precisa ganhar na contagem de vitórias por consulta
    vencedor = linha["run_a"] if linha["wins_a"] > linha["losses_a"] else linha["run_b"]
    assert vencedor == "structural_gold__bm25"


def test_trec_roundtrip(qrels, run_bom, tmp_path):
    """Grava e relê no formato TREC — é o contrato entre F4 e F5."""
    p = tmp_path / "r.trec"
    p.write_text(
        "\n".join(
            f"q{i} Q0 d{i} 1 0.900000 teste" for i in range(20)
        ),
        encoding="utf-8",
    )
    run = load_run(p, name="teste")
    assert evaluate_run(qrels, run)["ndcg@10"] == pytest.approx(1.0)

    qp = tmp_path / "q.trec"
    qp.write_text("\n".join(f"q{i} 0 d{i} 3" for i in range(20)), encoding="utf-8")
    assert evaluate_run(load_qrels(qp), run)["ndcg@10"] == pytest.approx(1.0)


# --- análise ----------------------------------------------------------------

def test_bootstrap_ci_contem_a_media_e_e_deterministico():
    scores = [0.1, 0.5, 0.9, 0.3, 0.7] * 6
    media, low, high = bootstrap_ci(scores, n_resamples=1000)
    assert low <= media <= high
    assert bootstrap_ci(scores, n_resamples=1000) == (media, low, high)


def test_bootstrap_ci_de_valores_identicos_tem_intervalo_nulo():
    media, low, high = bootstrap_ci([0.4] * 10, n_resamples=500)
    assert media == low == high == pytest.approx(0.4)


def test_bootstrap_ci_rejeita_lista_vazia():
    with pytest.raises(ValueError):
        bootstrap_ci([])


def test_per_query_scores_alinha_score_com_a_consulta_certa(qrels):
    run = Run(
        {"q0": {"d0": 0.9}, "q1": {"zz": 0.9, "d1": 0.1}},
        name="r",
    )
    scores = per_query_scores(qrels, run)
    assert scores["q0"] == pytest.approx(1.0)
    assert scores["q1"] < 1.0


def test_slice_by_query_type_agrupa_por_source(qrels, run_bom):
    meta = {f"q{i}": ("real" if i < 10 else "sintetica") for i in range(20)}
    linhas = slice_by_query_type(qrels, [run_bom], meta)
    assert {l["valor"] for l in linhas} == {"real", "sintetica"}
    assert all(l["n_queries"] == 10 for l in linhas)


def test_doc_length_terciles_ordenados():
    p33, p66 = doc_length_terciles({f"d{i}": i * 100 for i in range(30)})
    assert p33 < p66


def test_slice_by_doc_length_usa_docs_relevantes_nao_recuperados(qrels, run_bom):
    """O tercil vem do qrel, então é o MESMO conjunto de consultas para todos
    os runs — senão as colunas da tabela não seriam comparáveis."""
    lengths = {f"d{i}": (100 if i < 7 else 5000 if i < 14 else 60000) for i in range(20)}
    linhas = slice_by_doc_length_tercile(qrels, [run_bom], lengths)
    assert [l["valor"] for l in linhas] == ["curto", "medio", "longo"]
    assert sum(l["n_queries"] for l in linhas) == 20


def test_slice_by_retriever_extrai_retriever_do_nome(qrels, run_bom):
    linhas = slice_by_retriever(qrels, [run_bom])
    assert linhas[0]["valor"] == "bm25"
    assert linhas[0]["estrategia"] == "structural_gold"


# --- tamanhos de documento --------------------------------------------------

def test_load_doc_lengths_usa_n_tokens_quando_existe(tmp_path):
    import json

    from src.evaluate import load_doc_lengths

    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        "\n".join(
            json.dumps({"doc_id": f"d{i}", "text": "x " * 50, "n_tokens": 123 + i})
            for i in range(3)
        ),
        encoding="utf-8",
    )
    assert load_doc_lengths(corpus) == {"d0": 123, "d1": 124, "d2": 125}


def test_load_doc_lengths_conta_quando_campo_ausente(tmp_path):
    """O ingest atual não grava `n_tokens`, apesar do contrato do plano."""
    import json

    from src.evaluate import load_doc_lengths

    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        json.dumps({"doc_id": "d0", "text": "acórdão do tribunal de contas"}),
        encoding="utf-8",
    )
    lengths = load_doc_lengths(corpus)
    assert lengths["d0"] > 0


def test_load_doc_lengths_cacheia(tmp_path):
    import json

    from src.evaluate import load_doc_lengths

    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(json.dumps({"doc_id": "d0", "text": "texto"}), encoding="utf-8")
    cache = tmp_path / "doc_lengths.json"
    load_doc_lengths(corpus, cache)
    assert cache.exists()

    # com o cache no lugar, o corpus nem é lido de novo
    corpus.unlink()
    assert load_doc_lengths(corpus, cache) == {"d0": 1}


# --- encoding dos doc_ids ---------------------------------------------------

def test_load_qrels_preserva_acento_no_doc_id(tmp_path):
    """`Qrels.from_file` do ranx lê com o encoding da plataforma e transforma
    `plenário` em `plenÃ¡rio`. Quase todo doc_id do corpus do TCU tem acento,
    e a corrupção some silenciosamente (as métricas fecham, porque os runs
    sofrem a mesma), só quebrando o cruzamento com dados externos."""
    p = tmp_path / "q.trec"
    p.write_text("1 0 2251-2017-plenário 3\n1 0 29-2009-plenário 1\n", encoding="utf-8")
    qrels = load_qrels(p)
    docs = qrels.to_dict()["1"]
    assert "2251-2017-plenário" in docs
    assert docs["2251-2017-plenário"] == 3


def test_load_run_preserva_acento_no_doc_id(tmp_path):
    p = tmp_path / "r.trec"
    p.write_text("1 Q0 2251-2017-plenário 1 0.900000 teste\n", encoding="utf-8")
    run = load_run(p)
    assert "2251-2017-plenário" in run.to_dict()["1"]


def test_qrels_e_run_com_acento_casam_e_avaliam(tmp_path):
    """Ponta a ponta: doc_id acentuado tem que gerar nDCG 1.0, não 0."""
    q = tmp_path / "q.trec"
    q.write_text("1 0 2251-2017-plenário 3\n", encoding="utf-8")
    r = tmp_path / "r.trec"
    r.write_text("1 Q0 2251-2017-plenário 1 0.900000 t\n", encoding="utf-8")
    assert evaluate_run(load_qrels(q), load_run(r))["ndcg@10"] == pytest.approx(1.0)


def test_query_terciles_ficam_equilibrados_mesmo_com_relevantes_grandes():
    """Os documentos relevantes são sistematicamente maiores que o corpus, então
    cortar pelos percentis do CORPUS joga quase tudo nos tercis superiores (na
    rodada real deu 3/67/80). Cortando pelos percentis das próprias consultas,
    os grupos ficam equilibrados."""
    # 30 consultas cujos relevantes são todos grandes em relação ao corpus
    qrels = Qrels({f"q{i}": {f"d{i}": 3} for i in range(30)})
    lengths = {f"d{i}": 10_000 + i * 500 for i in range(30)}
    tercil, (p33, p66) = query_length_terciles(qrels, lengths)
    contagem = {}
    for t in tercil.values():
        contagem[t] = contagem.get(t, 0) + 1
    assert set(contagem) == {"curto", "medio", "longo"}
    assert min(contagem.values()) >= 9  # ~10 por grupo
    assert p33 < p66


def test_query_terciles_ignora_consulta_sem_doc_conhecido():
    qrels = Qrels({"q0": {"d0": 3}, "q1": {"fantasma": 3}})
    tercil, _ = query_length_terciles(qrels, {"d0": 1000})
    assert "q0" in tercil and "q1" not in tercil
