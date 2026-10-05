"""F7 — JUÁ-Juris como segunda coleção de teste, sobre o MESMO corpus.

O JurisTCU tem 150 consultas. É pouco: o efeito mínimo detectável entre
estratégias de chunking ficou em ~0,02 de nDCG@10 (F5/F6), e nas 50 consultas
reais de log nem o ganho do recorte por seção é significativo.

O JUÁ-Juris (Pereira et al. 2026, arXiv:2604.06098) foi montado a partir da
mesma base de jurisprudência selecionada do TCU: cada instância é um par
(enunciado, excerto). O id `JURISPRUDENCIA-SELECIONADA-<N>` usa o mesmo `KEY`
do `doc.csv` do JurisTCU, então dá para levar cada excerto ao acórdão íntegro
que o contém pelo mesmo join (NUMACORDAO, ANOACORDAO, COLEGIADO) da ingestão.

Resultado: ~1,6 mil consultas de teste (e ~14 mil de treino) cujo acórdão já
está nos 12.880 do corpus — mesmos índices, mesmos embeddings, zero reencode.

Protocolo: a consulta é o enunciado; o relevante é o acórdão que contém o
excerto (relevância binária, `known-item`). Outros acórdãos podem ser
relevantes e não estão julgados — como no MS MARCO, o número é um limite
inferior, e a comparação entre sistemas continua pareada.

Para cada consulta, também localizamos o excerto DENTRO do acórdão e
registramos a macro-seção em que ele está. O campo vai em `source`, então
todo recorte "por tipo de consulta" do `src.evaluate` vira, de graça, um
recorte "por seção onde mora a resposta". É o teste direto da limitação
declarada na F6: quando a resposta está no relatório, o recorte prejudica?
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from .analysis import section_of_span
from .ingest import DATA_ROOT, INTERIM_DIR, JURISTCU_DOCS, _join_key, normalize_html

JUA_DIR = DATA_ROOT / "jua"
OUT_DIR = INTERIM_DIR / "jua"
PREFIXO = "JURISPRUDENCIA-SELECIONADA-"
ANCORA = 120  # caracteres, como na análise de domínio da F4

csv.field_size_limit(2**28)
_ESPACO = re.compile(r"\s+")


def dobrar(texto: str) -> str:
    """Sem acento, sem caixa, espaços colapsados — para casar excerto e acórdão."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return _ESPACO.sub(" ", sem_acento.lower()).strip()


def mapa_dobrado(texto: str) -> tuple[str, list[int]]:
    """Texto dobrado + posição original de cada caractere dobrado.

    Localizar no texto dobrado e devolver offset do texto original é o que
    permite cruzar com os `gold_spans`, que estão em offsets do original.
    """
    saida: list[str] = []
    origem: list[int] = []
    ultimo_espaco = True
    for i, c in enumerate(texto):
        for d in unicodedata.normalize("NFKD", c):
            if unicodedata.combining(d):
                continue
            d = d.lower()
            if d.isspace():
                if ultimo_espaco:
                    continue
                d, ultimo_espaco = " ", True
            else:
                ultimo_espaco = False
            saida.append(d)
            origem.append(i)
    return "".join(saida), origem


def localizar(excerto: str, doc_dobrado: str, origem: list[int]) -> int | None:
    """Offset (no texto original) de uma âncora do excerto, ou None.

    Tenta âncoras no meio, no início e no fim: a do meio evita cabeçalhos
    ("Voto:", "Relatório:") que o excerto publicado acrescenta, e as outras
    duas salvam excertos em que o meio sofreu alguma edição.
    """
    exc = dobrar(excerto)
    if len(exc) < 40:
        return None
    meio = max(0, len(exc) // 2 - ANCORA // 2)
    for ini in (meio, 0, max(0, len(exc) - ANCORA)):
        ancora = exc[ini:ini + ANCORA]
        pos = doc_dobrado.find(ancora)
        if pos >= 0:
            return origem[pos]
    return None


def _ler_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def construir(jua_dir: Path = JUA_DIR, out_dir: Path = OUT_DIR,
              corpus_path: Path = INTERIM_DIR / "corpus_docs.jsonl") -> dict:
    """Grava queries_<split>.jsonl e qrels_<split>.trec para test e train."""
    chave_para_doc: dict[str, str] = {}
    excerto_por_chave: dict[str, str] = {}
    with JURISTCU_DOCS.open(encoding="utf-8", newline="", errors="replace") as f:
        for row in csv.DictReader(f):
            k = _join_key(row.get("NUMACORDAO"), row.get("ANOACORDAO"), row.get("COLEGIADO"))
            if k is None:
                continue
            chave_para_doc[row["KEY"]] = f"{k[0]}-{k[1]}-{k[2].replace(' ', '_')}"
            excerto_por_chave[row["KEY"]] = normalize_html(row.get("EXCERTO"))

    docs = {d["doc_id"]: d for d in _ler_jsonl(corpus_path)}
    textos = {q["_id"]: q["text"] for q in _ler_jsonl(jua_dir / "queries.jsonl")}

    out_dir.mkdir(parents=True, exist_ok=True)
    relatorio: dict = {}
    cache_dobrado: dict[str, tuple[str, list[int]]] = {}
    for split in ("test", "train"):
        with (jua_dir / "qrels" / f"{split}.tsv").open(encoding="utf-8") as f:
            pares = [(r["query-id"], r["corpus-id"]) for r in csv.DictReader(f, delimiter="\t")]
        secoes: Counter = Counter()
        n_fora = 0
        with (out_dir / f"queries_{split}.jsonl").open("w", encoding="utf-8") as fq, \
             (out_dir / f"qrels_{split}.trec").open("w", encoding="utf-8") as fr:
            for qid_jua, cid in pares:
                chave = cid.removeprefix(PREFIXO)
                doc_id = chave_para_doc.get(chave)
                if doc_id not in docs or qid_jua not in textos:
                    n_fora += 1
                    continue
                doc = docs[doc_id]
                if doc_id not in cache_dobrado:
                    cache_dobrado[doc_id] = mapa_dobrado(doc["text"])
                pos = localizar(excerto_por_chave.get(chave, ""), *cache_dobrado[doc_id])
                secao = None
                if pos is not None:
                    secao = section_of_span(pos, pos + ANCORA, doc["gold_spans"])
                secao = secao or "nao_localizado"
                secoes[secao] += 1
                qid = f"jua-{chave}"
                texto = normalize_html(textos[qid_jua])
                fq.write(json.dumps({"query_id": qid, "text": texto,
                                     "source": f"resposta em {secao}"},
                                    ensure_ascii=False) + "\n")
                fr.write(f"{qid} 0 {doc_id} 1\n")
        relatorio[split] = {
            "pares_jua": len(pares),
            "consultas_mapeadas": sum(secoes.values()),
            "fora_do_corpus": n_fora,
            "secao_da_resposta": dict(secoes.most_common()),
        }
    relatorio["test_independente"] = recorte_independente(out_dir)
    (out_dir / "construcao.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    return relatorio


def recorte_independente(out_dir: Path = OUT_DIR,
                         qrels_juristcu: Path = INTERIM_DIR / "qrels.trec") -> dict:
    """Teste do JUÁ sem as consultas cujo acórdão é relevante no JurisTCU.

    As consultas sintéticas do JurisTCU vieram de enunciados da mesma base.
    Nada é treinado nelas, então não há vazamento; mas a coleção deixa de ser
    100% independente da que guiou as decisões da F6. Este recorte é a
    análise de sensibilidade prometida no pré-registro (ameaça 2): se o efeito
    vale no teste inteiro e some aqui, ele era herança do JurisTCU.
    """
    relevantes = set()
    with qrels_juristcu.open(encoding="utf-8") as f:
        for linha in f:
            _q, _z, doc, score = linha.split()
            if int(score) > 0:
                relevantes.add(doc)
    with (out_dir / "qrels_test.trec").open(encoding="utf-8") as f:
        alvo = {l.split()[0]: l.split()[2] for l in f}
    manter = {q for q, d in alvo.items() if d not in relevantes}
    with (out_dir / "queries_test.jsonl").open(encoding="utf-8") as fi, \
         (out_dir / "queries_test_indep.jsonl").open("w", encoding="utf-8") as fo:
        for linha in fi:
            if json.loads(linha)["query_id"] in manter:
                fo.write(linha)
    with (out_dir / "qrels_test.trec").open(encoding="utf-8") as fi, \
         (out_dir / "qrels_test_indep.trec").open("w", encoding="utf-8") as fo:
        for linha in fi:
            if linha.split()[0] in manter:
                fo.write(linha)
    return {"consultas": len(manter), "removidas": len(alvo) - len(manter)}


if __name__ == "__main__":
    print(json.dumps(construir(), ensure_ascii=False, indent=2))
