"""F7 — mapeamento do JUÁ-Juris para o corpus de acórdãos íntegros.

O risco silencioso aqui é de offset: a âncora é procurada no texto DOBRADO
(sem acento, sem caixa, espaços colapsados), mas a seção é resolvida contra os
`gold_spans`, que estão em offsets do texto ORIGINAL. Se a tradução de um para
o outro escorregar, a consulta cai na seção errada, e o recorte "por seção
onde mora a resposta" (H4 do pré-registro) mede outra coisa sem levantar erro.
"""

from src.analysis import section_of_span
from src.jua import ANCORA, dobrar, localizar, mapa_dobrado


def test_dobrar_tira_acento_caixa_e_espaco():
    assert dobrar("  Licitação   ÉTICA\n\tpública ") == "licitacao etica publica"


def test_mapa_dobrado_aponta_para_o_caractere_original():
    original = "Ação  do\nTCU"
    dobrado, origem = mapa_dobrado(original)
    assert dobrado == "acao do tcu"
    assert len(origem) == len(dobrado)
    # cada caractere dobrado aponta para a posição de onde veio no original
    assert original[origem[dobrado.index("t")]] == "T"
    assert original[origem[0]] == "A"


def _doc_com_secoes():
    relatorio = "Relatório. " + "historico do processo e alegações das partes. " * 20
    fundamentacao = ("Voto. A contratação direta exige justificativa de preço "
                     "compatível com o mercado, demonstrada por pesquisa ampla e "
                     "documentada nos autos, sob pena de responsabilização do gestor "
                     "que a autorizou sem esse cuidado. Fim do voto.")
    texto = relatorio + fundamentacao
    spans = [
        {"section": "relatorio", "start": 0, "end": len(relatorio)},
        {"section": "fundamentacao", "start": len(relatorio), "end": len(texto)},
    ]
    return texto, spans, fundamentacao


def test_excerto_com_acento_e_espacos_diferentes_cai_na_secao_certa():
    texto, spans, fundamentacao = _doc_com_secoes()
    # o excerto publicado difere na caixa, nos acentos e no espaçamento
    excerto = ("  A CONTRATACAO   direta exige justificativa de preco compativel com o mercado,\n"
               "demonstrada por pesquisa ampla e documentada nos autos, sob pena de "
               "responsabilizacao do gestor que a autorizou sem esse cuidado.")
    pos = localizar(excerto, *mapa_dobrado(texto))
    assert pos is not None
    assert section_of_span(pos, pos + ANCORA, spans) == "fundamentacao"


def test_excerto_ausente_devolve_none():
    texto, _spans, _f = _doc_com_secoes()
    assert localizar("um trecho que nao existe no documento " * 5, *mapa_dobrado(texto)) is None


def test_excerto_curto_demais_nao_e_localizado():
    texto, _spans, _f = _doc_com_secoes()
    # âncora curta casa em qualquer lugar: melhor não localizar do que localizar errado
    assert localizar("Voto.", *mapa_dobrado(texto)) is None
