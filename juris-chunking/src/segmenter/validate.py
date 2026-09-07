"""Validação automática do segmentador contra os spans ouro do corpus
(colunas do CSV do TCU, gravados em `data/interim/corpus_docs.jsonl` pelo
`ingest.py`) — seção F2 do plano_implementacao.md.

Isto substitui a amostra manual de 80 docs do `plano_tecnico.md`: o
gabarito agora é derivado estruturalmente (uma seção por coluna), não
anotado à mão, então a acurácia pode ser medida sobre o corpus inteiro
(~13k acórdãos) em vez de uma amostra. A amostra manual que resta (20
docs) é só para checar a sanidade da MONTAGEM do texto (não entra aqui —
é inspeção visual, ver seção 0 do plano_implementacao.md).

Métrica de acurácia: por CARACTERE, via sobreposição de intervalos entre
spans ouro e spans previstos (não por span inteiro, porque o segmentador
pode discordar só na fronteira exata e ainda assim acertar quase todo o
conteúdo). `cobertura` (recall) e `precisão` são calculadas por seção.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from .rules import FALLBACK_LABEL
from .segment import LabeledSpan, Segmenter

INTERIM_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "interim"
CORPUS_DOCS = INTERIM_DIR / "corpus_docs.jsonl"
RESULTS_CORPUS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "results" / "corpus"


def iter_corpus_docs(path: Path = CORPUS_DOCS):
    with path.open(encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            yield doc["doc_id"], doc["text"], doc["gold_spans"]


def _doc_char_stats(gold_spans: list[dict], pred_spans: list[LabeledSpan]) -> dict:
    """Sobreposição gold x previsto de UM doc, em caracteres.

    Retorna `{"gold": int, "correct": int, "por_secao": {secao: {"gold",
    "predicted", "correct"}}}`. `gold` conta só chars cobertos por algum
    gold_span (os separadores entre colunas ficam de fora, dos dois lados).
    """
    per_section: dict[str, dict[str, int]] = defaultdict(lambda: {"gold": 0, "predicted": 0, "correct": 0})
    total_gold = 0
    total_correct = 0

    for g in gold_spans:
        length = g["end"] - g["start"]
        total_gold += length
        per_section[g["section"]]["gold"] += length

    for p in pred_spans:
        per_section[p.section]["predicted"] += p.end - p.start

    for g in gold_spans:
        for p in pred_spans:
            overlap = min(g["end"], p.end) - max(g["start"], p.start)
            if overlap > 0 and g["section"] == p.section:
                total_correct += overlap
                per_section[g["section"]]["correct"] += overlap

    return {"gold": total_gold, "correct": total_correct, "por_secao": dict(per_section)}


def accuracy(predicted: list[LabeledSpan], gold: list[dict]) -> float:
    """Acurácia por caractere de UM doc: fração dos chars cobertos pelo
    gabarito ouro onde o segmentador previu a mesma seção."""
    stats = _doc_char_stats(gold, predicted)
    if stats["gold"] == 0:
        return 0.0
    return stats["correct"] / stats["gold"]


def validate(corpus_path: Path = CORPUS_DOCS, limit: int | None = None) -> dict:
    segmenter = Segmenter()
    n_docs = 0
    n_fallback = 0
    total_gold = 0
    total_correct = 0
    per_section: dict[str, dict[str, int]] = defaultdict(lambda: {"gold": 0, "predicted": 0, "correct": 0})

    for doc_id, text, gold_spans in iter_corpus_docs(corpus_path):
        if limit is not None and n_docs >= limit:
            break
        n_docs += 1
        pred_spans = segmenter.segment(doc_id, text)
        if len(pred_spans) == 1 and pred_spans[0].section == FALLBACK_LABEL:
            n_fallback += 1

        stats = _doc_char_stats(gold_spans, pred_spans)
        total_gold += stats["gold"]
        total_correct += stats["correct"]
        for section, counts in stats["por_secao"].items():
            per_section[section]["gold"] += counts["gold"]
            per_section[section]["predicted"] += counts["predicted"]
            per_section[section]["correct"] += counts["correct"]

    def safe_div(a: int, b: int) -> float:
        return round(a / b, 4) if b else 0.0

    report = {
        "n_docs": n_docs,
        "acuracia_char_global": safe_div(total_correct, total_gold),
        "fallback_rate": safe_div(n_fallback, n_docs),
        "por_secao": {
            section: {
                "cobertura": safe_div(counts["correct"], counts["gold"]),
                "precisao": safe_div(counts["correct"], counts["predicted"]),
                "gold_chars": counts["gold"],
                "predicted_chars": counts["predicted"],
            }
            for section, counts in sorted(per_section.items())
        },
    }
    return report


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    report = validate(limit=limit)
    RESULTS_CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    with (RESULTS_CORPUS_DIR / "segmenter_validation.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
