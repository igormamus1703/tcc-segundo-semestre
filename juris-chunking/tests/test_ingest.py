from src.ingest import _join_key, _norm_colegiado, _norm_num, assemble_document, normalize_html


def test_normalize_html_strips_paragraph_tags_to_newlines():
    assert normalize_html("<p>VISTOS, relatados</p><p>e discutidos</p>") == (
        "VISTOS, relatados\n\ne discutidos"
    )


def test_normalize_html_unescapes_entities():
    assert normalize_html("art. 71, III &amp; ss.") == "art. 71, III & ss."


def test_normalize_html_keeps_inner_text_of_citation_tags():
    raw = (
        'confirmar a medida cautelar deferida por meio do '
        '<acordao_decisao_tcu colegiado="Plenário" numero="1334" ano="2020">'
        "Acórdão 1.334/2020-Plenário</acordao_decisao_tcu>."
    )
    assert normalize_html(raw) == (
        "confirmar a medida cautelar deferida por meio do "
        "Acórdão 1.334/2020-Plenário."
    )


def test_normalize_html_linearizes_table():
    raw = "<table><tbody><tr><td>Item</td><td>Valor</td></tr></tbody></table>"
    result = normalize_html(raw)
    assert "<" not in result
    assert "Item" in result and "Valor" in result


def test_normalize_html_collapses_blank_lines_and_spaces():
    raw = "<p>a</p>\n\n\n\n<p>  b   c  </p>"
    assert normalize_html(raw) == "a\n\nb c"


def test_normalize_html_empty_input():
    assert normalize_html("") == ""
    assert normalize_html(None) == ""


def test_norm_num_strips_trailing_zero_decimal():
    assert _norm_num("358.0") == "358"
    assert _norm_num("358") == "358"
    assert _norm_num("") is None
    assert _norm_num(None) is None


def test_norm_colegiado_casefolds_and_strips():
    assert _norm_colegiado(" Plenário ") == "plenário"
    assert _norm_colegiado("PLENÁRIO") == "plenário"


def test_join_key_matches_juristcu_and_tcu_formats():
    juristcu = _join_key("358.0", "2020.0", "Plenário")
    tcu = _join_key("358", "2020", "Plenário")
    assert juristcu == tcu
    assert juristcu == ("358", "2020", "plenário")


def test_join_key_none_when_any_field_missing():
    assert _join_key(None, "2020", "Plenário") is None
    assert _join_key("358", "", "Plenário") is None


def test_assemble_document_orders_sections_and_records_gold_spans():
    row = {
        "SUMARIO": "<p>Resumo do caso.</p>",
        "RELATORIO": "",
        "VOTO": "<p>Voto do relator.</p>",
        "DECLARACAOVOTO": "",
        "VOTOCOMPLEMENTAR": "",
        "VOTOMINISTROREVISOR": "",
        "ACORDAO": "<p>ACORDAM os Ministros.</p>",
    }
    text, spans = assemble_document(row)

    assert [s.section for s in spans] == ["ementa", "fundamentacao", "dispositivo"]
    for span in spans:
        assert text[span.start : span.end] == {
            "ementa": "Resumo do caso.",
            "fundamentacao": "Voto do relator.",
            "dispositivo": "ACORDAM os Ministros.",
        }[span.section]


def test_assemble_document_skips_empty_columns():
    row = {col: "" for col, _ in [
        ("SUMARIO", "ementa"),
        ("RELATORIO", "relatorio"),
        ("VOTO", "fundamentacao"),
        ("DECLARACAOVOTO", "fundamentacao"),
        ("VOTOCOMPLEMENTAR", "fundamentacao"),
        ("VOTOMINISTROREVISOR", "fundamentacao"),
        ("ACORDAO", "fundamentacao"),
    ]}
    row["ACORDAO"] = "<p>Só o dispositivo.</p>"
    text, spans = assemble_document(row)
    assert text == "Só o dispositivo."
    assert len(spans) == 1
