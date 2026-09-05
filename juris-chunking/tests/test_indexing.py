import json

import numpy as np
import pytest

from src.chunkers.base import Chunk
from src.indexing.dense import DenseIndex, _safe_name
from src.indexing.lexical import BM25Index
from src.indexing.text_norm import normalize_for_bm25, strip_accents


# --- normalização -----------------------------------------------------------

def test_strip_accents_preserva_letras():
    assert strip_accents("acórdão") == "acordao"
    assert strip_accents("RELATÓRIO") == "RELATORIO"


def test_normalize_iguala_termo_acentuado_e_nao_acentuado():
    """20 anos de publicação do TCU trazem as duas grafias; sem isso viram
    termos distintos no índice."""
    assert normalize_for_bm25("acórdão") == normalize_for_bm25("acordao")


def test_normalize_remove_stopwords_e_preserva_numeros():
    tokens = normalize_for_bm25("O acórdão de 2020 não foi reformado")
    assert "o" not in tokens and "de" not in tokens and "nao" not in tokens
    assert "2020" in tokens
    assert "acordao" in tokens and "reformado" in tokens


# --- BM25 -------------------------------------------------------------------

@pytest.fixture
def chunks():
    return [
        Chunk("c1", "docA", "Tomada de contas especial julgada irregular", None, 0, 42),
        Chunk("c2", "docA", "Licitação na modalidade pregão eletrônico", None, 42, 83),
        Chunk("c3", "docB", "Débito imputado ao responsável com juros", None, 0, 39),
    ]


def test_bm25_recupera_chunk_pertinente(chunks):
    index = BM25Index()
    index.build(chunks)
    hits = index.search("contas irregulares", top_k=3)
    assert hits[0][0] == "c1"


def test_bm25_casa_consulta_acentuada_com_texto_sem_acento(chunks):
    """A consulta passa pela MESMA normalização do índice — é o ponto do
    text_norm.py; se divergirem, o recall cai silenciosamente."""
    index = BM25Index()
    index.build(chunks)
    com_acento = index.search("licitação pregão", top_k=1)
    sem_acento = index.search("licitacao pregao", top_k=1)
    assert com_acento[0][0] == sem_acento[0][0] == "c2"


def test_bm25_top_k_maior_que_corpus_nao_quebra(chunks):
    index = BM25Index()
    index.build(chunks)
    assert len(index.search("contas", top_k=999)) == len(chunks)


def test_bm25_search_batch_equivale_a_buscas_individuais(chunks):
    index = BM25Index()
    index.build(chunks)
    queries = ["contas irregulares", "pregão eletrônico"]
    em_lote = index.search_batch(queries, top_k=2)
    individuais = [index.search(q, top_k=2) for q in queries]
    assert em_lote == individuais


def test_bm25_mapeia_chunk_para_documento(chunks):
    index = BM25Index()
    index.build(chunks)
    assert index.doc_of("c2") == "docA"
    assert index.doc_of("c3") == "docB"


def test_bm25_rejeita_corpus_vazio():
    with pytest.raises(ValueError):
        BM25Index().build([])


def test_bm25_search_sem_build_falha():
    with pytest.raises(RuntimeError):
        BM25Index().search("qualquer coisa")


def test_bm25_backend_desconhecido():
    with pytest.raises(ValueError):
        BM25Index(backend="rank_bm25")


# --- Denso (sem baixar modelo) ----------------------------------------------

class FakeModel:
    """Embedder determinístico: vetor de contagem de 3 termos-âncora.

    Evita baixar ~500 MB de pesos num teste unitário, e ainda deixa o
    resultado da busca previsível.
    """

    ANCHORS = ("contas", "licitacao", "debito")

    def encode(self, texts, batch_size=32, normalize_embeddings=True,
               convert_to_numpy=True, show_progress_bar=False):
        vecs = []
        for t in texts:
            low = strip_accents(t.lower())
            v = np.array([float(low.count(a)) for a in self.ANCHORS], dtype="float32")
            if v.sum() == 0:
                v = np.ones(len(self.ANCHORS), dtype="float32")
            if normalize_embeddings:
                v = v / np.linalg.norm(v)
            vecs.append(v)
        return np.vstack(vecs)


@pytest.fixture
def dense_index(chunks, monkeypatch):
    index = DenseIndex("fake/model", query_prefix="query: ", passage_prefix="passage: ")
    monkeypatch.setattr(index, "_get_model", lambda: FakeModel())
    index.build(chunks)
    return index


def test_dense_recupera_chunk_pertinente(dense_index):
    hits = dense_index.search("contas", top_k=3)
    assert hits[0][0] == "c1"


def test_dense_scores_sao_cosseno_no_intervalo(dense_index):
    for _chunk_id, score in dense_index.search("contas", top_k=3):
        assert -1.01 <= score <= 1.01


def test_dense_top_k_maior_que_corpus_nao_quebra(dense_index, chunks):
    assert len(dense_index.search("contas", top_k=999)) == len(chunks)


def test_dense_search_sem_build_falha():
    with pytest.raises(RuntimeError):
        DenseIndex("fake/model").search("x")


def test_safe_name_para_nome_de_arquivo():
    assert _safe_name("intfloat/multilingual-e5-base") == "intfloat__multilingual-e5-base"


def test_dense_cache_evita_reencode(chunks, monkeypatch, tmp_path):
    """Segunda build() com o mesmo cache_dir não chama o modelo de novo."""
    chamadas = {"n": 0}

    class Contando(FakeModel):
        def encode(self, texts, **kw):
            chamadas["n"] += 1
            return super().encode(texts, **kw)

    idx1 = DenseIndex("fake/model")
    monkeypatch.setattr(idx1, "_get_model", lambda: Contando())
    idx1.build(chunks, cache_dir=tmp_path)
    assert chamadas["n"] == 1
    assert (tmp_path / "emb_fake__model.npy").exists()

    idx2 = DenseIndex("fake/model")
    monkeypatch.setattr(idx2, "_get_model", lambda: Contando())
    idx2.build(chunks, cache_dir=tmp_path)
    assert chamadas["n"] == 1  # não re-encodou


def test_dense_cache_invalida_se_chunks_mudarem(chunks, monkeypatch, tmp_path):
    """Cache com chunk_ids diferentes NÃO pode ser reaproveitado: o embedding
    da posição i deixaria de corresponder ao chunk da posição i, e o resultado
    sairia errado sem nenhum erro visível."""
    idx1 = DenseIndex("fake/model")
    monkeypatch.setattr(idx1, "_get_model", lambda: FakeModel())
    idx1.build(chunks, cache_dir=tmp_path)

    outros = chunks[:2] + [Chunk("c9", "docC", "Outro texto qualquer", None, 0, 20)]
    idx2 = DenseIndex("fake/model")
    monkeypatch.setattr(idx2, "_get_model", lambda: FakeModel())
    idx2.build(outros, cache_dir=tmp_path)

    ids = json.loads((tmp_path / "chunk_ids_fake__model.json").read_text(encoding="utf-8"))
    assert ids == ["c1", "c2", "c9"]
    assert idx2.chunk_ids == ["c1", "c2", "c9"]
