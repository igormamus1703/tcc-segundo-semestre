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


# --- checkpoint do encode ---------------------------------------------------

def test_encode_com_checkpoint_grava_e_retoma(chunks, monkeypatch, tmp_path):
    """O encode do corpus leva ~10h. Uma queda na nona hora nao pode custar o
    trabalho todo: cada bloco vai para o disco assim que fica pronto."""
    chamadas = {"n": 0}

    class Contando(FakeModel):
        def encode(self, texts, **kw):
            chamadas["n"] += 1
            return super().encode(texts, **kw)

    idx = DenseIndex("fake/model")
    monkeypatch.setattr(idx, "_get_model", lambda: Contando())
    idx.chunk_ids = [c.chunk_id for c in chunks]
    textos = [c.text for c in chunks]

    emb = idx.encode_com_checkpoint(textos, tmp_path, bloco=1, log=lambda *a: None)
    assert emb.shape[0] == len(chunks)
    assert chamadas["n"] == 3  # um encode por bloco
    # ao terminar, o cache final existe e os parciais foram limpos
    assert (tmp_path / "emb_fake__model.npy").exists()
    assert not (tmp_path / "parcial_fake__model").exists()


def test_checkpoint_retomado_nao_reencoda(chunks, monkeypatch, tmp_path):
    class Contando(FakeModel):
        chamadas = 0

        def encode(self, texts, **kw):
            Contando.chamadas += 1
            return super().encode(texts, **kw)

    # primeira passada: interrompida depois do primeiro bloco
    idx = DenseIndex("fake/model")
    monkeypatch.setattr(idx, "_get_model", lambda: Contando())
    textos = [c.text for c in chunks]
    partes = tmp_path / "parcial_fake__model"
    partes.mkdir()
    primeiro = idx.encode([textos[0]], "")
    with (partes / "bloco_00000.npy.tmp").open("wb") as f:
        np.save(f, primeiro)
    (partes / "bloco_00000.npy.tmp").replace(partes / "bloco_00000.npy")
    Contando.chamadas = 0

    idx2 = DenseIndex("fake/model")
    monkeypatch.setattr(idx2, "_get_model", lambda: Contando())
    emb = idx2.encode_com_checkpoint(textos, tmp_path, bloco=1, log=lambda *a: None)
    assert emb.shape[0] == 3
    assert Contando.chamadas == 2  # o bloco 0 veio do checkpoint


def test_checkpoint_descarta_bloco_truncado(chunks, monkeypatch, tmp_path):
    """Bloco com tamanho errado (escrita interrompida) tem que ser refeito, nao
    aceito — senao os embeddings ficariam desalinhados dos chunks."""
    idx = DenseIndex("fake/model")
    monkeypatch.setattr(idx, "_get_model", lambda: FakeModel())
    partes = tmp_path / "parcial_fake__model"
    partes.mkdir()
    with (partes / "bloco_00000.npy").open("wb") as f:
        np.save(f, np.zeros((5, 3), dtype="float32"))  # deveria ter 2 linhas

    emb = idx.encode_com_checkpoint(
        [c.text for c in chunks], tmp_path, bloco=2, log=lambda *a: None
    )
    assert emb.shape[0] == 3


# --- F6: cache reaproveitado por SUBCONJUNTO --------------------------------

def test_cache_serve_um_subconjunto_dos_chunks(chunks, monkeypatch, tmp_path):
    """Indexar so algumas secoes do acordao usa um SUBCONJUNTO dos chunks da
    estrategia. Os embeddings ja existem e custaram ~10 h de GPU: reencodar
    para jogar dois tercos fora seria absurdo."""
    chamadas = {"n": 0}

    class Contando(FakeModel):
        def encode(self, texts, **kw):
            chamadas["n"] += 1
            return super().encode(texts, **kw)

    completo = DenseIndex("fake/model")
    monkeypatch.setattr(completo, "_get_model", lambda: Contando())
    completo.build(chunks, cache_dir=tmp_path)
    assert chamadas["n"] == 1

    recorte = DenseIndex("fake/model")
    monkeypatch.setattr(recorte, "_get_model", lambda: Contando())
    recorte.build([chunks[0], chunks[2]], cache_dir=tmp_path)
    assert chamadas["n"] == 1  # nao reencodou nada
    assert recorte.chunk_ids == ["c1", "c3"]


def test_subconjunto_do_cache_sai_na_ordem_dos_chunks_pedidos(chunks, monkeypatch, tmp_path):
    """O alinhamento e o risco silencioso: a linha i da matriz tem de ser o
    chunk i da lista pedida. Fora de ordem, a busca devolve o chunk_id errado
    para cada resultado, e nenhuma excecao e levantada."""
    completo = DenseIndex("fake/model")
    monkeypatch.setattr(completo, "_get_model", lambda: FakeModel())
    completo.build(chunks, cache_dir=tmp_path)

    invertido = DenseIndex("fake/model")
    monkeypatch.setattr(invertido, "_get_model", lambda: FakeModel())
    invertido.build([chunks[2], chunks[0]], cache_dir=tmp_path)

    esperado = FakeModel().encode([chunks[2].text, chunks[0].text])
    obtido = invertido._load_cache(tmp_path, log=lambda *a: None)
    assert np.allclose(obtido, esperado)


def test_cache_somente_leitura_nao_grava_recorte_por_cima_do_completo(
    chunks, monkeypatch, tmp_path
):
    """Sem essa trava, indexar so a fundamentacao de uma estrategia ainda nao
    encodada deixaria em emb_*.npy um cache com um terco dos chunks."""
    idx = DenseIndex("fake/model")
    monkeypatch.setattr(idx, "_get_model", lambda: FakeModel())
    idx.build(chunks[:2], cache_dir=tmp_path, cache_somente_leitura=True)
    assert not (tmp_path / "emb_fake__model.npy").exists()
    assert idx.search("contas", top_k=1)  # mas o indice funciona


def test_chunk_ausente_do_cache_forca_reencode(chunks, monkeypatch, tmp_path):
    """Subconjunto e aceito; conjunto com chunk NOVO, nao — nesse caso nao ha
    embedding para ele, e aproveitar o cache deixaria uma linha errada."""
    chamadas = {"n": 0}

    class Contando(FakeModel):
        def encode(self, texts, **kw):
            chamadas["n"] += 1
            return super().encode(texts, **kw)

    idx1 = DenseIndex("fake/model")
    monkeypatch.setattr(idx1, "_get_model", lambda: Contando())
    idx1.build(chunks, cache_dir=tmp_path)

    novos = [chunks[0], Chunk("c99", "docZ", "Texto inedito", None, 0, 13)]
    idx2 = DenseIndex("fake/model")
    monkeypatch.setattr(idx2, "_get_model", lambda: Contando())
    idx2.build(novos, cache_dir=tmp_path)
    assert chamadas["n"] > 1
