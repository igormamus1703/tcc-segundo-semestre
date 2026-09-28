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
    parse_run_name,
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


# --- análise por seção do acórdão -------------------------------------------

def test_section_of_span_escolhe_a_maior_sobreposicao():
    from src.analysis import section_of_span

    spans = [
        {"section": "ementa", "start": 0, "end": 100},
        {"section": "relatorio", "start": 100, "end": 1000},
        {"section": "dispositivo", "start": 1000, "end": 1200},
    ]
    # chunk quase todo no relatorio, com uma ponta na ementa
    assert section_of_span(90, 500, spans) == "relatorio"
    assert section_of_span(0, 60, spans) == "ementa"
    assert section_of_span(1050, 1200, spans) == "dispositivo"
    # fora de qualquer span
    assert section_of_span(5000, 6000, spans) is None


def test_slice_by_section_usa_offset_nas_baselines():
    """`fixed` e `recursive` devolvem section=None, mas o offset diz de onde o
    chunk veio — é isso que permite a análise por seção também nas baselines."""
    from src.analysis import slice_by_section

    gold = {"docA": [
        {"section": "ementa", "start": 0, "end": 100},
        {"section": "relatorio", "start": 100, "end": 1000},
    ]}
    chunks_top = [
        {"run": "fixed_512_256__bm25", "query_id": "1", "rank": 1, "doc_id": "docA",
         "section": None, "start": 0, "end": 90},
        {"run": "fixed_512_256__bm25", "query_id": "2", "rank": 1, "doc_id": "docA",
         "section": None, "start": 200, "end": 900},
        {"run": "fixed_512_256__bm25", "query_id": "3", "rank": 99, "doc_id": "docA",
         "section": None, "start": 200, "end": 900},  # fora do top_k
    ]
    linhas = slice_by_section(chunks_top, gold, top_k=10)
    por_secao = {l["valor"]: l for l in linhas}
    assert por_secao["ementa"]["n_chunks"] == 1
    assert por_secao["relatorio"]["n_chunks"] == 1
    assert por_secao["ementa"]["fracao"] == 0.5


def test_slice_by_section_respeita_rotulo_do_structural():
    """Quando o chunker já rotula a seção, usamos o rótulo, sem remapear."""
    from src.analysis import slice_by_section

    chunks_top = [
        {"run": "structural_gold__bm25", "query_id": "1", "rank": 1, "doc_id": "docA",
         "section": "dispositivo", "start": 0, "end": 50},
    ]
    linhas = slice_by_section(chunks_top, {}, top_k=10)
    assert linhas[0]["valor"] == "dispositivo"


# --- poder estatístico ------------------------------------------------------

def test_poder_detecta_efeito_grande(qrels, run_bom, run_ruim):
    """Diferença grande e consistente tem que ficar acima do MDE."""
    from src.analysis import poder_estatistico

    r = poder_estatistico(qrels, run_bom, run_ruim)
    assert r["n_queries"] == 20
    assert r["diferenca_observada"] > 0
    assert r["detectavel"] is True
    assert r["mde"] < r["diferenca_observada"]


def test_poder_aponta_falta_de_amostra_em_efeito_minusculo(qrels):
    """Diferença minúscula: o teste tem que dizer que NÃO é detectável e
    estimar quantas consultas seriam necessárias — que é a resposta honesta
    para 'por que não deu significativo?'."""
    from src.analysis import poder_estatistico

    a = Run({f"q{i}": {f"d{i}": 0.9, f"x{i}": 0.10} for i in range(20)}, name="a")
    b = Run({f"q{i}": ({f"d{i}": 0.9, f"x{i}": 0.10} if i else {f"x0": 0.9, "d0": 0.1})
             for i in range(20)}, name="b")
    r = poder_estatistico(qrels, a, b)
    assert r["detectavel"] is False
    assert r["n_necessario_para_detectar"] > r["n_queries"]


def test_poder_exige_consultas_suficientes(qrels):
    from src.analysis import poder_estatistico

    um = Run({"q0": {"d0": 1.0}}, name="um")
    with pytest.raises(ValueError):
        poder_estatistico(Qrels({"q0": {"d0": 3}}), um, um)


# --- avaliação cruzando rodadas ---------------------------------------------

def test_desambigua_runs_de_mesmo_nome_em_rodadas_diferentes(tmp_path):
    """`fixed__bm25` pode existir em duas rodadas. Sem prefixo, o
    `Report.comparisons` do ranx — indexado por frozenset({a, b}) — colapsa o
    par num conjunto de um elemento e estoura com KeyError."""
    from src.evaluate import _desambiguar_nomes

    a = tmp_path / "20260101-0000_x" / "runs" / "fixed__bm25.trec"
    b = tmp_path / "20260202-0000_y" / "runs" / "fixed__bm25.trec"
    c = tmp_path / "20260202-0000_y" / "runs" / "outro__bm25.trec"
    runs = [Run({"q0": {"d0": 1.0}}, name="fixed__bm25"),
            Run({"q0": {"d0": 1.0}}, name="fixed__bm25"),
            Run({"q0": {"d0": 1.0}}, name="outro__bm25")]
    _desambiguar_nomes(runs, [a, b, c])
    assert runs[0].name == "20260101-0000_x/fixed__bm25"
    assert runs[1].name == "20260202-0000_y/fixed__bm25"
    assert runs[2].name == "outro__bm25"  # sem colisão, fica como está


def test_recusa_juntar_rodadas_de_corpus_diferente(tmp_path):
    """Juntar uma rodada do corpus completo com uma de subcorpus daria uma
    tabela em que metade dos runs foi avaliada contra qrels que não são os
    seus — plausível à vista e completamente errado."""
    import json

    from src.evaluate import _exigir_mesmo_corpus

    a, b = tmp_path / "rodA", tmp_path / "rodB"
    for d, n_docs in ((a, 12880), (b, 451)):
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps(
            {"corpus": {"n_docs": n_docs}, "config": {"n_queries": 150}}), encoding="utf-8")

    with pytest.raises(SystemExit, match="não mediram o mesmo corpus"):
        _exigir_mesmo_corpus(a, b)


def test_aceita_juntar_rodadas_do_mesmo_corpus(tmp_path):
    """É o caso real: BM25 e denso rodam em rodadas separadas, mesmo corpus."""
    import json

    from src.evaluate import _exigir_mesmo_corpus

    a, b = tmp_path / "rodBM25", tmp_path / "rodDenso"
    for d in (a, b):
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps(
            {"corpus": {"n_docs": 12880}, "config": {"n_queries": 150}}), encoding="utf-8")

    _exigir_mesmo_corpus(a, b)  # não levanta


def test_rotulo_da_figura_ignora_o_prefixo_de_rodada():
    """Runs desambiguados viram `<rodada>/estrategia__retriever`; sem descartar
    o prefixo, o rotulo da figura viraria o caminho inteiro."""
    from src.plots import partes_do_run, rotulo_do_run

    assert partes_do_run("structural_gold__bm25") == ("structural_gold", "bm25")
    assert partes_do_run("20260906-0515_bm25/structural_gold__bm25") == ("structural_gold", "bm25")
    assert partes_do_run("fixed_512_256__dense-bge_m3__sum_top_k")[1] == "dense-bge_m3"
    assert rotulo_do_run("20260906-0515_bm25/structural_gold__bm25") == "estrutural (ouro)"


def test_rotulo_distingue_retriever_quando_ha_mais_de_um():
    """Numa figura que cruza BM25 e denso, 'recursivo' apareceria duas vezes
    nos eixos sem o retriever no rotulo."""
    from src.plots import mais_de_um_retriever, rotulo_do_run

    so_bm25 = ["structural_gold__bm25", "recursive_default__bm25"]
    misto = ["structural_gold__bm25", "structural_gold__dense-bge_m3"]
    assert mais_de_um_retriever(so_bm25) is False
    assert mais_de_um_retriever(misto) is True
    assert rotulo_do_run("recursive_default__bm25", False) == "recursivo"
    assert rotulo_do_run("recursive_default__bm25", True) == "recursivo\nBM25"
    assert rotulo_do_run("recursive_default__dense-bge_m3", True) == "recursivo\ndenso bge_m3"


# --- F6: nomes de run com variante de secao ---------------------------------

def test_parse_run_name_basico():
    campos = parse_run_name("structural_gold__bm25")
    assert campos["estrategia"] == "structural_gold"
    assert campos["retriever"] == "bm25"
    assert campos["agregacao"] == "max_pooling"
    assert campos["secoes"] == "" and campos["pesos"] == ""


def test_parse_run_name_le_variante_por_prefixo_e_nao_por_posicao():
    """Com --aggregation e --secoes juntos, o recorte fica na 4a posicao; ler
    por posicao poria 'sec-sem_relatorio' na coluna de agregacao e a tabela do
    artigo sairia embaralhada, sem nenhum erro."""
    a = parse_run_name("structural_gold__bm25__sec-sem_relatorio")
    b = parse_run_name("structural_gold__bm25__sum_top_k__sec-sem_relatorio")
    assert a["secoes"] == b["secoes"] == "sem_relatorio"
    assert a["agregacao"] == "max_pooling"
    assert b["agregacao"] == "sum_top_k"


def test_parse_run_name_separa_peso_de_secao():
    campos = parse_run_name("fixed_512_256__dense-bge_m3__peso-rel0.3")
    assert campos["pesos"] == "rel0.3"
    assert campos["secoes"] == ""
    assert campos["retriever"] == "dense-bge_m3"


def test_parse_run_name_preserva_prefixo_de_rodada():
    """`_desambiguar_nomes` prefixa runs homonimos com a rodada; o prefixo nao
    pode vazar para a coluna estrategia."""
    campos = parse_run_name("20260906-0215_bm25/structural_gold__bm25")
    assert campos["rodada"] == "20260906-0215_bm25"
    assert campos["estrategia"] == "structural_gold"
