import pytest

from src.chunkers.base import Document
from src.chunkers.fixed import FixedChunker
from src.chunkers.recursive import RecursiveChunker
from src.chunkers.structural import StructuralChunker
from src.segmenter.rules import FALLBACK_LABEL
from src.segmenter.segment import LabeledSpan, Segmenter


def _assert_offset_invariant(doc: Document, chunks) -> None:
    for chunk in chunks:
        assert doc.text[chunk.start : chunk.end] == chunk.text
        assert chunk.doc_id == doc.doc_id


# ---------- FixedChunker ----------


def test_fixed_chunker_offsets_and_chunk_ids():
    text = " ".join(f"palavra{i}" for i in range(200))
    doc = Document(doc_id="doc-1", text=text)
    chunker = FixedChunker(size=20, stride=10, name="fixed_test")

    chunks = chunker.chunk(doc)

    assert len(chunks) > 1
    _assert_offset_invariant(doc, chunks)
    assert all(c.section is None for c in chunks)
    assert [c.chunk_id for c in chunks[:2]] == ["doc-1::fixed_test::0000", "doc-1::fixed_test::0001"]


def test_fixed_chunker_rejects_invalid_stride():
    with pytest.raises(ValueError):
        FixedChunker(size=10, stride=0)
    with pytest.raises(ValueError):
        FixedChunker(size=10, stride=20)


# ---------- RecursiveChunker ----------


def test_recursive_chunker_offsets_and_covers_text_in_order():
    text = "\n\n".join(f"Parágrafo número {i}, com algum texto de exemplo." for i in range(30))
    doc = Document(doc_id="doc-2", text=text)
    chunker = RecursiveChunker(
        chunk_size=20, chunk_overlap=5, separators=["\n\n", " ", ""], name="recursive_test"
    )

    chunks = chunker.chunk(doc)

    assert len(chunks) > 1
    _assert_offset_invariant(doc, chunks)
    assert all(c.section is None for c in chunks)
    # ordem crescente e não regressiva (permite sobreposição, não retrocesso maior que o overlap)
    starts = [c.start for c in chunks]
    assert starts == sorted(starts)


def test_recursive_chunker_offsets_with_token_based_overlap_on_long_text():
    # Regressão: com length_function=count_tokens, o add_start_index nativo
    # do LangChain subtrai chunk_overlap (contagem de TOKENS) de um
    # comprimento em CARACTERES, e o piso de busca resultante fica além da
    # posição real — find() retorna -1. Só aparece com texto longo o
    # bastante (muitos parágrafos numerados curtos, como itens de
    # dispositivo de acórdão); textos curtos não acionam o bug.
    text = "\n\n".join(f"{i}. Item numerado com um pouco mais de texto de exemplo aqui." for i in range(200))
    doc = Document(doc_id="doc-long", text=text)
    chunker = RecursiveChunker(
        chunk_size=1024, chunk_overlap=128, separators=["\n\n", " ", ""], name="recursive_default"
    )

    chunks = chunker.chunk(doc)

    assert len(chunks) > 1
    _assert_offset_invariant(doc, chunks)
    assert all(c.start >= 0 for c in chunks)


def test_recursive_chunker_handles_repeated_text_without_offset_drift():
    # trecho repetido de propósito (comum em acórdãos SIGILOSO, ver
    # docstring de segment.py) — testa que os offsets não "grudam" na
    # primeira ocorrência.
    text = "\n\n".join(["[SIGILOSO]"] * 10)
    doc = Document(doc_id="doc-3", text=text)
    chunker = RecursiveChunker(chunk_size=3, chunk_overlap=1, separators=["\n\n", " ", ""])

    chunks = chunker.chunk(doc)
    _assert_offset_invariant(doc, chunks)


# ---------- StructuralChunker ----------


def _gold_doc() -> Document:
    text = "AAAA" + "B" * 400 + "CCCC"
    gold_spans = [
        {"section": "ementa", "start": 0, "end": 4},
        {"section": "relatorio", "start": 4, "end": 404},
        {"section": "dispositivo", "start": 404, "end": 408},
    ]
    return Document(doc_id="doc-4", text=text, gold_spans=gold_spans)


def test_structural_chunker_gold_never_crosses_section_boundary():
    doc = _gold_doc()
    chunker = StructuralChunker(max_section_tokens=20, overlap=5, span_source="gold")

    chunks = chunker.chunk(doc)

    _assert_offset_invariant(doc, chunks)
    for chunk in chunks:
        matching_spans = [s for s in doc.gold_spans if s["start"] <= chunk.start and chunk.end <= s["end"]]
        assert len(matching_spans) == 1, f"chunk {chunk.chunk_id} cruza fronteira de seção"


def test_structural_chunker_gold_short_span_is_a_single_chunk():
    doc = _gold_doc()
    chunker = StructuralChunker(max_section_tokens=20, overlap=5, span_source="gold")

    chunks = chunker.chunk(doc)
    ementa_chunks = [c for c in chunks if c.section == "ementa"]
    dispositivo_chunks = [c for c in chunks if c.section == "dispositivo"]

    assert len(ementa_chunks) == 1
    assert len(dispositivo_chunks) == 1


def test_structural_chunker_gold_long_span_propagates_label_to_subchunks():
    doc = _gold_doc()
    chunker = StructuralChunker(max_section_tokens=20, overlap=5, span_source="gold")

    chunks = chunker.chunk(doc)
    relatorio_chunks = [c for c in chunks if c.section == "relatorio"]

    assert len(relatorio_chunks) > 1
    assert all(c.section == "relatorio" for c in relatorio_chunks)


def test_structural_chunker_gold_requires_gold_spans_on_document():
    doc = Document(doc_id="doc-5", text="algum texto")
    chunker = StructuralChunker(max_section_tokens=20, overlap=5, span_source="gold")

    with pytest.raises(ValueError):
        chunker.chunk(doc)


def test_structural_chunker_pred_requires_segmenter_at_construction():
    with pytest.raises(ValueError):
        StructuralChunker(max_section_tokens=20, overlap=5, span_source="pred")


class _FakeSegmenter:
    def segment(self, doc_id, text):
        return [
            LabeledSpan(doc_id, "relatorio", 0, 10),
            LabeledSpan(doc_id, FALLBACK_LABEL, 10, len(text)),
        ]


def test_structural_chunker_pred_maps_fallback_label_to_none_section():
    text = "0123456789" + "resto do texto indefinido aqui"
    doc = Document(doc_id="doc-6", text=text)
    chunker = StructuralChunker(
        max_section_tokens=20, overlap=5, span_source="pred", segmenter=_FakeSegmenter()
    )

    chunks = chunker.chunk(doc)

    _assert_offset_invariant(doc, chunks)
    sections = {c.section for c in chunks}
    assert "relatorio" in sections
    assert None in sections
    assert FALLBACK_LABEL not in sections


def test_structural_chunker_pred_uses_real_segmenter_end_to_end():
    text = (
        "Concessão de aposentadoria.\n\n"
        "Trata-se de processo de aposentadoria.\n\n"
        "É o Relatório.\n\n"
        "Ante o exposto, voto por negar o registro.\n\n"
        "VISTOS, relatados e discutidos, ACORDAM os Ministros em negar o registro."
    )
    doc = Document(doc_id="doc-7", text=text)
    chunker = StructuralChunker(
        max_section_tokens=50, overlap=5, span_source="pred", segmenter=Segmenter()
    )

    chunks = chunker.chunk(doc)

    _assert_offset_invariant(doc, chunks)
    assert [c.section for c in chunks] == ["ementa", "relatorio", "fundamentacao", "dispositivo"]
