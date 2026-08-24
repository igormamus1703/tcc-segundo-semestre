from src.segmenter.rules import FALLBACK_LABEL
from src.segmenter.segment import Segmenter
from src.segmenter.validate import accuracy


def _labels(spans):
    return [s.section for s in spans]


def test_segment_full_doc_with_all_sections():
    text = (
        "Concessão de aposentadoria. Legalidade.\n\n"
        "Trata-se de processo de concessão de aposentadoria ao servidor.\n\n"
        "É o Relatório.\n\n"
        "Ante o exposto, voto por que seja negado o registro.\n\n"
        "VISTOS, relatados e discutidos estes autos, ACORDAM os Ministros "
        "em negar o registro."
    )
    spans = Segmenter().segment("doc-1", text)

    assert _labels(spans) == ["ementa", "relatorio", "fundamentacao", "dispositivo"]
    # spans são contíguos e cobrem o texto inteiro
    assert spans[0].start == 0
    assert spans[-1].end == len(text)
    for prev, nxt in zip(spans, spans[1:]):
        assert prev.end == nxt.start


def test_segment_only_voto_e_acordao_has_no_ementa_or_relatorio_marker():
    text = (
        "Ante o exposto, voto por que seja aplicada multa ao responsável.\n\n"
        "VISTOS, relatados e discutidos estes autos, ACORDAM os Ministros "
        "em aplicar multa."
    )
    spans = Segmenter().segment("doc-2", text)

    # sem marca de abertura de relatório: o prefixo antes do único marcador
    # encontrado (dispositivo) não pode ser chamado de "ementa" com confiança.
    assert _labels(spans) == [FALLBACK_LABEL, "dispositivo"]
    assert spans[0].start == 0
    assert spans[-1].end == len(text)


def test_segment_without_any_marker_falls_back_to_whole_doc():
    text = "Texto corrido qualquer, sem nenhum marcador estrutural conhecido."
    spans = Segmenter().segment("doc-3", text)

    assert len(spans) == 1
    assert spans[0].section == FALLBACK_LABEL
    assert spans[0].start == 0
    assert spans[0].end == len(text)


def test_segment_ignores_repeated_or_backward_marker_occurrences():
    text = (
        "Auditoria em obras rodoviárias. Irregularidades. Multa.\n\n"
        "Trata-se de processo relativo a auditoria.\n\n"
        "Trata-se de assunto correlato mencionado no relatório.\n\n"
        "É o Relatório.\n\n"
        "VISTOS, relatados e discutidos estes autos."
    )
    spans = Segmenter().segment("doc-4", text)

    # o segundo "Trata-se de" não deve gerar uma segunda fronteira de
    # relatorio nem retroceder o estado depois de "É o Relatório".
    assert _labels(spans) == ["ementa", "relatorio", "fundamentacao", "dispositivo"]


def test_fallback_rate_counts_only_pure_fallback_docs():
    segmenter = Segmenter()
    spans_by_doc = {
        "doc-a": segmenter.segment("doc-a", "sem marcador nenhum aqui"),
        "doc-b": segmenter.segment(
            "doc-b",
            "Trata-se do processo.\n\nÉ o Relatório.\n\nVISTOS, relatados e discutidos.",
        ),
    }
    assert segmenter.fallback_rate(spans_by_doc) == 0.5


def test_accuracy_matches_gold_spans_by_char_overlap():
    text = "AAAABBBBCCCC"
    gold = [
        {"section": "ementa", "start": 0, "end": 4},
        {"section": "relatorio", "start": 4, "end": 8},
        {"section": "dispositivo", "start": 8, "end": 12},
    ]
    predicted = Segmenter().segment("doc-5", text)
    # sem nenhum marcador conhecido no texto sintético -> tudo "indefinido"
    assert accuracy(predicted, gold) == 0.0

    from src.segmenter.segment import LabeledSpan

    perfect = [
        LabeledSpan("doc-5", "ementa", 0, 4),
        LabeledSpan("doc-5", "relatorio", 4, 8),
        LabeledSpan("doc-5", "dispositivo", 8, 12),
    ]
    assert accuracy(perfect, gold) == 1.0
