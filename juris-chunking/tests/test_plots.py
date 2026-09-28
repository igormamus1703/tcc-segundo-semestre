"""Leitura dos nomes de run pelas figuras.

Todas as figuras agrupam por `partes_do_run`. Se duas condicoes diferentes
devolverem a mesma chave, elas caem na mesma barra e uma SOME do grafico sem
nenhum erro — a figura fica errada, nao incompleta, e vai para o artigo assim.
Foi exatamente o que aconteceu na primeira versao da tabela principal da F6.
"""

from src.plots import partes_do_run


def test_run_simples():
    assert partes_do_run("structural_gold__bm25") == ("structural_gold", "bm25")


def test_recorte_por_secao_nao_colapsa_no_indice_completo():
    completo = partes_do_run("fixed_512_256__bm25")
    recortado = partes_do_run("fixed_512_256__bm25__sec-sem_relatorio")
    assert completo != recortado
    assert recortado == ("fixed_512_256", "bm25 · sem relatório")


def test_controle_aleatorio_nao_colapsa_no_recorte():
    """As duas condicoes tem o mesmo tamanho de indice e resultados opostos;
    junta-las numa barra apagaria justamente o controle."""
    a = partes_do_run("fixed_512_256__bm25__sec-sem_relatorio")
    b = partes_do_run("fixed_512_256__bm25__amostra-0.2800s42")
    assert a != b
    assert "amostra aleatória" in b[1]


def test_peso_entra_no_rotulo():
    _est, cond = partes_do_run("structural_gold__dense-bge_m3__peso-rel0.5")
    assert cond == "dense-bge_m3 · peso rel0.5"


def test_prefixo_de_rodada_com_barra_e_descartado():
    """`--incluir` prefixa com a rodada so para desempatar nomes iguais; o
    caminho inteiro no eixo deixaria a figura ilegivel."""
    assert partes_do_run("20260906-0215_bm25/structural_gold__bm25") == (
        "structural_gold", "bm25"
    )


def test_prefixo_de_rodada_com_hifen_duplo_vira_discriminador():
    """Aqui o prefixo NAO pode ser descartado: `--runs` so o coloca quando dois
    runs escolhidos tinham o mesmo nome de arquivo, ou seja, quando ele e a
    unica coisa que separa as duas condicoes."""
    a = partes_do_run("20260928-1645_cv_fusao_bm25_denso--fixed_512_256__cv-soma_norm")
    b = partes_do_run("20260928-1653_cv_fusao_sec_sem_relatorio--fixed_512_256__cv-soma_norm")
    assert a != b
    assert a[0] == b[0] == "fixed_512_256"
    assert "cv fusao bm25 denso" in a[1] and "cv fusao sec sem relatorio" in b[1]


def test_agregacao_alternativa_tambem_separa():
    a = partes_do_run("structural_gold__bm25")
    b = partes_do_run("structural_gold__bm25__sum_top_k")
    assert a != b
    assert b[1] == "bm25 · sum_top_k"
