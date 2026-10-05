"""F7 — reranking: a lógica que decide o que o cross-encoder lê e como vira ranking.

Nada aqui usa GPU: o pontuador é uma função falsa. Os riscos silenciosos são
três, e cada teste trava um:

- um documento sem passagem sumir do ranking (ou subir sem ter sido lido);
- a variante `sem_relatorio` ler uma passagem do relatório;
- o cache reprocessar pares já pontuados, ou perdê-los numa queda.
"""

import json

from src.rerank import (
    fora_do_relatorio,
    ler_cache,
    pares_pendentes,
    passagens_por_documento,
    pontuar_com_cache,
    reranquear,
)

SPANS = [
    {"section": "relatorio", "start": 0, "end": 1000},
    {"section": "fundamentacao", "start": 1000, "end": 2000},
]


def _sidecar(tmp_path, nome, linhas):
    p = tmp_path / f"{nome}__chunks.jsonl"
    p.write_text("\n".join(json.dumps(l) for l in linhas) + "\n", encoding="utf-8")
    return p


def _linha(q, d, c, s, e):
    return {"query_id": q, "doc_id": d, "chunk_id": c, "start": s, "end": e}


def test_mesmo_chunk_em_duas_fontes_e_lido_uma_vez(tmp_path):
    a = _sidecar(tmp_path, "bm25", [_linha("1", "D", "D::1", 0, 100)])
    b = _sidecar(tmp_path, "denso", [_linha("1", "D", "D::1", 0, 100),
                                    _linha("1", "D", "D::7", 1200, 1300)])
    pas = passagens_por_documento({"bm25": a, "denso": b})
    assert set(pas[("1", "D")]) == {"D::1", "D::7"}
    assert pas[("1", "D")]["D::1"]["fontes"] == ["bm25", "denso"]


def test_reranqueia_pelo_max_e_mantem_cauda_e_documentos_sem_passagem():
    candidatos = {"1": {"A": 5.0, "B": 4.0, "C": 3.0, "Z": 1.0}}
    passagens = {("1", "A"): {"a1": {}, "a2": {}}, ("1", "B"): {"b1": {}}}
    scores = {("1", "a1"): 0.1, ("1", "a2"): 0.2, ("1", "b1"): 0.9}
    run, cob = reranquear(candidatos, passagens, scores, top=3)
    ordem = sorted(run["1"], key=lambda d: -run["1"][d])
    # B (0,9) passa A (max 0,2); C não tem passagem e vem depois dos lidos;
    # Z está fora do top e fica na cauda, na ordem original
    assert ordem == ["B", "A", "C", "Z"]
    assert cob == {"documentos_lidos": 2, "documentos_sem_passagem": 1,
                   "fracao_sem_passagem": round(1 / 3, 4)}


def test_variante_sem_relatorio_nao_le_passagem_do_relatorio():
    candidatos = {"1": {"A": 2.0, "B": 1.0}}
    passagens = {
        ("1", "A"): {"rel": {"start": 10, "end": 200}, "fund": {"start": 1100, "end": 1300}},
        ("1", "B"): {"rel_b": {"start": 10, "end": 200}},
    }
    # a passagem do relatório de A é a que tem nota alta: se fosse lida, A
    # continuaria na frente com 0,99
    scores = {("1", "rel"): 0.99, ("1", "fund"): 0.1, ("1", "rel_b"): 0.5}
    run, cob = reranquear(candidatos, passagens, scores, top=2,
                          filtro=lambda doc, info: fora_do_relatorio(info, SPANS))
    ordem = sorted(run["1"], key=lambda d: -run["1"][d])
    assert ordem == ["A", "B"]  # A lido pela fundamentação; B sem passagem permitida
    assert cob["documentos_sem_passagem"] == 1


def test_preservar_le_pelo_relatorio_quem_nao_tem_outra_passagem():
    candidatos = {"1": {"A": 2.0, "B": 1.0}}
    passagens = {
        ("1", "A"): {"rel": {"start": 10, "end": 200}, "fund": {"start": 1100, "end": 1300}},
        ("1", "B"): {"rel_b": {"start": 10, "end": 200}},
    }
    scores = {("1", "rel"): 0.99, ("1", "fund"): 0.1, ("1", "rel_b"): 0.5}
    run, cob = reranquear(candidatos, passagens, scores, top=2,
                          filtro=lambda doc, info: fora_do_relatorio(info, SPANS),
                          preservar=True)
    # A tem passagem permitida e é lido só por ela (0,1); B não tem, e em vez
    # de ser rebaixado é lido pelo relatório (0,5) e passa A
    ordem = sorted(run["1"], key=lambda d: -run["1"][d])
    assert ordem == ["B", "A"]
    assert cob["documentos_sem_passagem"] == 0


def test_sem_spans_a_passagem_e_mantida():
    assert fora_do_relatorio({"start": 0, "end": 10}, None) is True


def test_cache_nao_repontua_e_sobrevive_a_releitura(tmp_path):
    cache = tmp_path / "scores.tsv"
    chamadas = []

    def falso(pares):
        chamadas.append(len(pares))
        return [float(len(p[1])) for p in pares]

    pontuar_com_cache([("1", "c1"), ("1", "c2")], {"1": "q"}, {"c1": "ab", "c2": "abcd"},
                      falso, cache, bloco=1, log=lambda _m: None)
    assert ler_cache(cache) == {("1", "c1"): 2.0, ("1", "c2"): 4.0}

    candidatos = {"1": {"D": 1.0}}
    passagens = {("1", "D"): {"c1": {}, "c2": {}, "c3": {}}}
    pend = pares_pendentes(candidatos, passagens, top=10, ja_pontuados=set(ler_cache(cache)))
    assert pend == [("1", "c3")]
