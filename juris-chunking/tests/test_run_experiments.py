import json

import pytest

from src.run_experiments import (
    build_index,
    load_chunks,
    load_models_config,
    load_queries,
    run_one,
    write_trec_run,
)


@pytest.fixture
def models_cfg():
    return load_models_config()


@pytest.fixture
def processed_dir(tmp_path):
    """Duas estratégias com chunks de dois documentos cada."""
    textos = {
        "fixed_512_256": [
            ("f1", "docA", "Tomada de contas especial julgada irregular pelo Tribunal"),
            ("f2", "docA", "Licitacao na modalidade pregao eletronico para servicos"),
            ("f3", "docB", "Debito imputado ao responsavel com juros de mora"),
        ],
        "structural_gold": [
            ("s1", "docA", "Tomada de contas especial julgada irregular"),
            ("s2", "docB", "Debito imputado ao responsavel"),
        ],
    }
    for estrategia, linhas in textos.items():
        d = tmp_path / estrategia
        d.mkdir(parents=True)
        with (d / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for i, (cid, doc_id, texto) in enumerate(linhas):
                f.write(
                    json.dumps(
                        {
                            "chunk_id": cid,
                            "doc_id": doc_id,
                            "text": texto,
                            "section": None,
                            "start": i * 10,
                            "end": i * 10 + len(texto),
                        }
                    )
                    + "\n"
                )
    return tmp_path


@pytest.fixture
def queries_file(tmp_path):
    p = tmp_path / "queries.jsonl"
    with p.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"query_id": "1", "text": "contas irregulares", "source": "real"}) + "\n")
        f.write(json.dumps({"query_id": "2", "text": "debito juros", "source": "sintetica"}) + "\n")
    return p


def test_load_queries_respeita_limite(queries_file):
    assert len(load_queries(queries_file)) == 2
    assert len(load_queries(queries_file, limit=1)) == 1


def test_load_chunks_reconstroi_o_dataclass(processed_dir):
    chunks = load_chunks("fixed_512_256", processed_dir)
    assert len(chunks) == 3
    assert chunks[0].chunk_id == "f1"
    assert chunks[0].doc_id == "docA"
    assert chunks[0].section is None


def test_load_chunks_erro_claro_se_estrategia_nao_foi_gerada(processed_dir):
    with pytest.raises(FileNotFoundError, match="src.chunkers.run"):
        load_chunks("inexistente", processed_dir)


def test_write_trec_run_formato(tmp_path):
    ranked = {"1": [("docA", 0.9), ("docB", 0.5)], "2": [("docB", 0.7)]}
    p = tmp_path / "r.trec"
    n = write_trec_run(p, ranked, "teste__bm25")
    assert n == 3
    linhas = p.read_text(encoding="utf-8").strip().split("\n")
    assert linhas[0] == "1 Q0 docA 1 0.900000 teste__bm25"
    assert linhas[1] == "1 Q0 docB 2 0.500000 teste__bm25"
    # rank reinicia em cada consulta
    assert linhas[2] == "2 Q0 docB 1 0.700000 teste__bm25"


def test_build_index_retriever_desconhecido(models_cfg):
    with pytest.raises(SystemExit, match="retriever desconhecido"):
        build_index("colbert", [], models_cfg, None)


def test_build_index_embedder_desconhecido(models_cfg):
    with pytest.raises(SystemExit, match="embedder desconhecido"):
        build_index("dense", [], models_cfg, "nao_existe")


def test_models_yaml_nao_tem_mais_preencher(models_cfg):
    """O `PREENCHER` do pt_compact bloqueava a F4."""
    for e in models_cfg["embedders"]:
        assert e["hf_id"] != "PREENCHER"


def test_models_yaml_default_embedder_nao_e_gated(models_cfg):
    """O default precisa rodar sem passo manual: quem clonar o repo tem que
    conseguir reproduzir sem criar conta no Hugging Face."""
    default = models_cfg["dense"]["default_embedder"]
    cfg = next(e for e in models_cfg["embedders"] if e["name"] == default)
    assert cfg.get("gated") is False


def test_models_yaml_todo_embedder_tem_prefixos(models_cfg):
    """Prefixo errado degrada a recuperação silenciosamente — nenhum pode
    ficar sem declaração explícita."""
    for e in models_cfg["embedders"]:
        assert "query_prefix" in e and "passage_prefix" in e


def test_run_one_bm25_ponta_a_ponta(processed_dir, queries_file, models_cfg, tmp_path):
    runs_dir = tmp_path / "runs"
    info = run_one(
        "fixed_512_256",
        "bm25",
        load_queries(queries_file),
        models_cfg,
        top_chunks=10,
        top_docs=10,
        processed_dir=processed_dir,
        runs_dir=runs_dir,
    )
    assert info["run"] == "fixed_512_256__bm25"
    assert info["n_chunks"] == 3

    conteudo = (runs_dir / "fixed_512_256__bm25.trec").read_text(encoding="utf-8")
    linhas = [l.split() for l in conteudo.strip().split("\n")]
    # A agregação chunk->doc precisa colapsar docA (2 chunks) em UMA linha por
    # consulta: é a diferença entre um ranking de chunks e um de documentos.
    docs_q1 = [l[2] for l in linhas if l[0] == "1"]
    assert len(docs_q1) == len(set(docs_q1))
    assert "docA" in docs_q1
    # consulta "contas irregulares" deve rankear docA na frente de docB
    assert docs_q1[0] == "docA"


def test_run_one_sum_top_k_gera_arquivo_com_sufixo(
    processed_dir, queries_file, models_cfg, tmp_path
):
    runs_dir = tmp_path / "runs"
    info = run_one(
        "fixed_512_256",
        "bm25",
        load_queries(queries_file),
        models_cfg,
        aggregation="sum_top_k",
        processed_dir=processed_dir,
        runs_dir=runs_dir,
    )
    assert info["run"] == "fixed_512_256__bm25__sum_top_k"
    assert (runs_dir / "fixed_512_256__bm25__sum_top_k.trec").exists()


# --- configuração do denso (janela e precisão) ------------------------------

def test_models_yaml_janela_acomoda_o_maior_chunk(models_cfg):
    """A janela do encoder tem que caber o maior chunk do desenho experimental
    (1024 tokens tiktoken ~ 910 de subword). Com 512, ~37% do conteudo dos
    chunks grandes seria descartado e so o fixed_512_256 caberia inteiro,
    ganhando vantagem artificial na comparacao."""
    default = models_cfg["dense"]["default_embedder"]
    cfg = next(e for e in models_cfg["embedders"] if e["name"] == default)
    assert cfg["max_seq_length"] >= 1024


def test_build_index_repassa_janela_e_dtype(models_cfg):
    idx = build_index("dense", [], models_cfg, "bge_m3")
    assert idx.max_seq_length == 1024
    assert idx.dtype == "auto"


def test_dense_resolve_dtype_por_dispositivo():
    """fp16 acelera ~3x na GPU; na CPU e emulado e fica mais lento, entao la
    o padrao continua fp32."""
    import torch

    from src.indexing.dense import DenseIndex

    idx = DenseIndex("m", dtype="auto")
    assert idx._resolve_dtype("cuda") is torch.float16
    assert idx._resolve_dtype("cpu") is None
    assert DenseIndex("m", dtype="fp32")._resolve_dtype("cuda") is None
    assert DenseIndex("m", dtype="bf16")._resolve_dtype("cuda") is torch.bfloat16


def test_run_name_do_denso_carrega_o_modelo(processed_dir, queries_file, models_cfg, tmp_path):
    """Sem o nome do embedder no arquivo, rodar um segundo modelo
    sobrescreveria o run do primeiro, sem aviso."""
    import src.run_experiments as rx

    class FakeIndex:
        chunk_ids = ["f1"]
        doc_ids = ["docA"]
        max_seq_length = 1024

        def describe(self):
            return "fake"

        def build(self, chunks, cache_dir=None, show_progress=False, bloco=50_000, log=print):
            pass

        def search_batch(self, queries, top_k=100):
            return [[("f1", 0.5)] for _ in queries]

    original = rx.build_index
    rx.build_index = lambda *a, **k: FakeIndex()
    try:
        info = rx.run_one(
            "fixed_512_256", "dense", load_queries(queries_file), models_cfg,
            embedder="bge_m3", processed_dir=processed_dir, runs_dir=tmp_path,
        )
    finally:
        rx.build_index = original
    assert info["run"] == "fixed_512_256__dense-bge_m3"
    assert (tmp_path / "fixed_512_256__dense-bge_m3.trec").exists()


def test_orcamento_de_tempo_registra_o_que_ficou_de_fora(monkeypatch, tmp_path,
                                                          processed_dir, queries_file):
    """Numa rodada noturna e melhor terminar 3 estrategias e ter resultado do
    que comecar a quarta e ser interrompido no meio."""
    import sys

    import src.run_experiments as rx

    chamadas = []

    def fake_run_one(strategy, retriever, *a, **kw):
        chamadas.append(strategy)
        return {"run": f"{strategy}__{retriever}", "n_chunks": 1, "n_queries": 1,
                "n_linhas_run": 1, "segundos": 0.0}

    # o orcamento ja esta estourado no primeiro laco -> nada roda, tudo e registrado
    monkeypatch.setattr(rx, "run_one", fake_run_one)
    # Sem redirecionar a raiz, o main() cria a pasta do experimento em
    # results/experiments/ DE VERDADE, e cada rodada da suite deixa lixo la.
    import src.experiment as ex
    monkeypatch.setattr(ex, "EXPERIMENTS_DIR", tmp_path / "experiments")
    monkeypatch.setattr(sys, "argv", [
        "run_experiments", "--strategy", "fixed_512_256", "structural_gold",
        "--retriever", "bm25", "--max-horas", "0",
        "--processed-dir", str(processed_dir),
        "--queries", str(queries_file),
        "--runs-dir", str(tmp_path / "runs"),
    ])
    rx.main()
    assert chamadas == []


def test_estimativa_usa_a_taxa_medida(processed_dir):
    """A estimativa vem da taxa observada na rodada, nao de constante chutada."""
    from src.run_experiments import _contar_chunks, _estimar_horas

    assert _contar_chunks("fixed_512_256", processed_dir) == 3
    # 3 chunks a 1 chunk/s = 3 s = 0,000833 h
    assert _estimar_horas("fixed_512_256", processed_dir, 1.0) == pytest.approx(3 / 3600)
    # sem taxa ainda (primeira etapa da rodada), nao ha base: nao bloqueia
    assert _estimar_horas("fixed_512_256", processed_dir, None) == 0.0


def test_estimativa_de_estrategia_inexistente_e_zero(processed_dir):
    from src.run_experiments import _estimar_horas

    assert _estimar_horas("nao_existe", processed_dir, 10.0) == 0.0
