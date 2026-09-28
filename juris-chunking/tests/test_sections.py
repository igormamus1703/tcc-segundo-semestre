"""F6 — recorte e ponderação por macro-seção do acórdão.

O que estes testes protegem, acima de tudo, é o ALINHAMENTO: a lista de
seções tem de sair na mesma ordem dos chunks de entrada, porque quem chama a
usa para selecionar linhas da matriz de embeddings. Um desalinhamento aqui não
levanta exceção — só produz um nDCG errado.
"""

import pytest

from src.chunkers.base import Chunk
from src.sections import (
    SECOES_VALIDAS,
    amostra_aleatoria,
    filtrar,
    parse_pesos,
    parse_secoes,
    pesos_por_chunk,
    rotular,
    rotulo_pesos,
    rotulo_secoes,
    secao_do_chunk,
)

SPANS = {
    "docA": [
        {"section": "ementa", "start": 0, "end": 100},
        {"section": "relatorio", "start": 100, "end": 500},
        {"section": "fundamentacao", "start": 500, "end": 800},
        {"section": "dispositivo", "start": 800, "end": 900},
    ]
}


# --- parsing ----------------------------------------------------------------

def test_parse_secoes_positivo():
    assert parse_secoes("ementa,fundamentacao") == {"ementa", "fundamentacao"}


def test_parse_secoes_negativo_e_o_complemento():
    """'-relatorio' é como a intervenção é descrita no texto; tem de dar as
    outras três sem o autor precisar listá-las."""
    assert parse_secoes("-relatorio") == set(SECOES_VALIDAS) - {"relatorio"}


def test_parse_secoes_recusa_mistura_de_positivo_e_negativo():
    with pytest.raises(ValueError, match="ambiguo"):
        parse_secoes("ementa,-relatorio")


def test_parse_secoes_recusa_secao_inexistente():
    with pytest.raises(ValueError, match="desconhecida"):
        parse_secoes("conclusao")


def test_parse_pesos_le_pares():
    assert parse_pesos("relatorio=0.5,fundamentacao=2") == {
        "relatorio": 0.5, "fundamentacao": 2.0
    }


def test_parse_pesos_recusa_negativo():
    """Peso negativo inverteria a ordem do ranking — o chunk mais parecido com
    a consulta passaria a ser o pior colocado."""
    with pytest.raises(ValueError, match="negativo"):
        parse_pesos("relatorio=-1")


def test_rotulo_de_complemento_unico_e_legivel():
    assert rotulo_secoes(parse_secoes("-relatorio")) == "sem_relatorio"
    assert rotulo_secoes(set(SECOES_VALIDAS)) == "completo"
    assert rotulo_secoes({"ementa", "fundamentacao"}) == "em+fund"


def test_rotulo_de_pesos_nao_depende_da_ordem_de_digitacao():
    """Dois runs com os mesmos pesos precisam ter o mesmo nome de arquivo —
    senão o segundo não sobrescreve o primeiro e a tabela ganha uma linha
    duplicada que parece um resultado novo."""
    a = rotulo_pesos(parse_pesos("fundamentacao=2,relatorio=0.5"))
    b = rotulo_pesos(parse_pesos("relatorio=0.5,fundamentacao=2"))
    assert a == b == "rel0.5-fund2"


# --- resolução da seção -----------------------------------------------------

def test_rotulo_do_chunk_tem_precedencia_sobre_o_offset():
    """Nas estruturais o rótulo É a definição do chunk. Resolver pelo offset
    reatribuiria um chunk que encosta no span vizinho."""
    c = Chunk("c1", "docA", "...", "fundamentacao", 90, 110)  # offset cai na ementa
    assert secao_do_chunk(c, SPANS["docA"]) == "fundamentacao"


def test_chunk_sem_rotulo_e_resolvido_pelo_offset():
    """É o que faz o recorte por seção valer também para fixed/recursive, que
    não carregam rótulo."""
    c = Chunk("c1", "docA", "...", None, 520, 700)
    assert secao_do_chunk(c, SPANS["docA"]) == "fundamentacao"


def test_chunk_a_cavalo_vai_para_a_secao_de_maior_sobreposicao():
    c = Chunk("c1", "docA", "...", None, 450, 700)  # 50 de relatorio, 200 de fundamentacao
    assert secao_do_chunk(c, SPANS["docA"]) == "fundamentacao"


def test_documento_sem_spans_devolve_none():
    c = Chunk("c1", "docSemSpans", "...", None, 0, 100)
    assert secao_do_chunk(c, None) is None


def test_rotular_preserva_a_ordem_de_entrada():
    """Contrato crítico: a posição i da lista tem de ser o chunk i, porque a
    linha i da matriz de embeddings é esse chunk."""
    chunks = [
        Chunk("c3", "docA", "...", None, 800, 900),
        Chunk("c1", "docA", "...", None, 0, 50),
        Chunk("c2", "docA", "...", None, 600, 700),
    ]
    assert rotular(chunks, SPANS) == ["dispositivo", "ementa", "fundamentacao"]


# --- filtro -----------------------------------------------------------------

def test_filtrar_mantem_so_as_secoes_pedidas_e_preserva_a_ordem():
    chunks = [
        Chunk("c1", "docA", "...", None, 0, 50),        # ementa
        Chunk("c2", "docA", "...", None, 200, 300),     # relatorio
        Chunk("c3", "docA", "...", None, 600, 700),     # fundamentacao
        Chunk("c4", "docA", "...", None, 820, 880),     # dispositivo
    ]
    mantidos, contagem = filtrar(chunks, parse_secoes("-relatorio"), SPANS)
    assert [c.chunk_id for c in mantidos] == ["c1", "c3", "c4"]
    assert contagem == {"ementa": 1, "relatorio": 1, "fundamentacao": 1, "dispositivo": 1}


def test_filtrar_descarta_chunk_sem_secao_resolvivel():
    """Escolha conservadora: manter o indefinido contaminaria o índice 'sem
    relatório' com trechos de relatório, puxando o efeito medido para baixo."""
    chunks = [
        Chunk("c1", "docA", "...", None, 600, 700),
        Chunk("c2", "docDesconhecido", "...", None, 0, 100),
    ]
    mantidos, contagem = filtrar(chunks, {"fundamentacao"}, SPANS)
    assert [c.chunk_id for c in mantidos] == ["c1"]
    assert contagem["indefinido"] == 1


def test_contagem_do_filtro_cobre_todos_os_chunks():
    """A contagem vai para o manifesto; se não somar o total, o número de
    'chunks antes' reportado no artigo estaria errado."""
    chunks = [
        Chunk(f"c{i}", "docA", "...", None, s, s + 40)
        for i, s in enumerate([0, 200, 600, 820, 850])
    ]
    _mantidos, contagem = filtrar(chunks, {"ementa"}, SPANS)
    assert sum(contagem.values()) == len(chunks)


# --- pesos ------------------------------------------------------------------

def test_pesos_por_chunk_so_guarda_o_que_difere_do_padrao():
    """Com 2,2 M de chunks, guardar o peso 1.0 de todos custaria centenas de MB
    para não dizer nada."""
    chunks = [
        Chunk("c1", "docA", "...", None, 200, 300),   # relatorio
        Chunk("c2", "docA", "...", None, 600, 700),   # fundamentacao
    ]
    assert pesos_por_chunk(chunks, {"relatorio": 0.5}, SPANS) == {"c1": 0.5}


def test_chunk_de_secao_indefinida_fica_com_o_peso_padrao():
    """Ao contrário do filtro, a ponderação NÃO descarta o indefinido: aqui o
    conservador é deixá-lo competir sem desconto, não removê-lo do índice."""
    chunks = [Chunk("c1", "docDesconhecido", "...", None, 0, 100)]
    assert pesos_por_chunk(chunks, {"relatorio": 0.5}, SPANS) == {}


def test_forma_negativa_sem_hifen_para_a_linha_de_comando():
    """'-relatorio' solto na CLI e lido pelo argparse como uma opcao e a rodada
    aborta. 'sem:relatorio' passa em qualquer shell e diz a mesma coisa."""
    assert parse_secoes("sem:relatorio") == parse_secoes("-relatorio")


# --- controle: amostra aleatoria --------------------------------------------

def test_amostra_aleatoria_mantem_a_fracao_pedida():
    chunks = [Chunk(f"c{i}", "docA", "...", None, i, i + 1) for i in range(100)]
    assert len(amostra_aleatoria(chunks, 0.33)) == 33


def test_amostra_aleatoria_preserva_a_ordem_original():
    """Mesmo contrato de `rotular`: a posicao i tem de continuar sendo o chunk
    i, porque a lista seleciona linhas da matriz de embeddings."""
    chunks = [Chunk(f"c{i}", "docA", "...", None, i, i + 1) for i in range(100)]
    amostrados = amostra_aleatoria(chunks, 0.3)
    indices = [int(c.chunk_id[1:]) for c in amostrados]
    assert indices == sorted(indices)


def test_amostra_aleatoria_e_reprodutivel():
    """O controle so vale como controle se a mesma semente der o mesmo indice:
    senao o numero muda a cada execucao e nao da para comparar com o recorte."""
    chunks = [Chunk(f"c{i}", "docA", "...", None, i, i + 1) for i in range(100)]
    a = [c.chunk_id for c in amostra_aleatoria(chunks, 0.3, seed=7)]
    b = [c.chunk_id for c in amostra_aleatoria(chunks, 0.3, seed=7)]
    c = [c.chunk_id for c in amostra_aleatoria(chunks, 0.3, seed=8)]
    assert a == b and a != c


def test_amostra_aleatoria_nao_repete_chunk():
    chunks = [Chunk(f"c{i}", "docA", "...", None, i, i + 1) for i in range(100)]
    ids = [c.chunk_id for c in amostra_aleatoria(chunks, 0.5)]
    assert len(ids) == len(set(ids))


def test_amostra_aleatoria_recusa_fracao_invalida():
    chunks = [Chunk("c0", "docA", "...", None, 0, 1)]
    with pytest.raises(ValueError, match="fracao"):
        amostra_aleatoria(chunks, 0.0)
    with pytest.raises(ValueError, match="fracao"):
        amostra_aleatoria(chunks, 1.5)
