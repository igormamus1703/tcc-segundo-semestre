"""F7 — a medida de sobreposição consulta × ementa usada na análise do mecanismo."""

from src.mecanismo import cobertura, termos


def test_termos_ignora_acento_caixa_stopwords_e_palavras_curtas():
    assert termos("Não se CONHECE de recurso contra decisão") == {"conhece", "recurso", "contra", "decisao"}


def test_cobertura_e_a_fracao_dos_termos_da_consulta_na_ementa():
    assert cobertura("recurso contra decisão genérica e abstrata",
                     "Não se conhece de recurso contra decisão genérica") == 0.8
    assert cobertura("", "qualquer ementa") == 0.0
