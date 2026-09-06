"""E5 — Avaliação: nDCG@10, MRR@10, MAP@10, Recall@100 via `ranx`.

Consome os TREC runs gravados pela F4 em `results/runs/` e o `qrels.trec`
produzido pela ingestão. Não recalcula nada do pipeline: recebe arquivos,
devolve tabelas.
"""

from __future__ import annotations

from pathlib import Path

from ranx import Qrels, Run, compare, evaluate

DEFAULT_METRICS = ("ndcg@10", "mrr@10", "map@10", "recall@100")


def load_qrels(path: Path) -> Qrels:
    """Lê um qrels TREC em UTF-8.

    NÃO usa `Qrels.from_file`: o ranx lê o arquivo com o encoding padrão da
    plataforma (latin-1/cp1252 no Windows), e todo doc_id acentuado volta como
    mojibake — `plenário` vira `plenÃ¡rio`. Como os runs passariam pela mesma
    corrupção, as métricas até fechariam; mas qualquer cruzamento com dados
    lidos fora do ranx (os tamanhos de documento do recorte por tercil, por
    exemplo) deixa de casar, e o recorte sai VAZIO sem nenhum erro.
    Os doc_ids do corpus do TCU são do tipo `2251-2017-plenário`, ou seja,
    quase todos têm acento.
    """
    d: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 4:
                continue
            qid, _, doc_id, score = parts[0], parts[1], parts[2], parts[3]
            d.setdefault(qid, {})[doc_id] = int(float(score))
    return Qrels(d)


def load_run(path: Path, name: str | None = None) -> Run:
    """Lê um run TREC em UTF-8 — mesmo motivo do `load_qrels`."""
    d: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 5:
                continue
            qid, doc_id, score = parts[0], parts[2], parts[4]
            d.setdefault(qid, {})[doc_id] = float(score)
    return Run(d, name=name or path.stem)


def evaluate_run(qrels: Qrels, run: Run, metrics=DEFAULT_METRICS) -> dict[str, float]:
    """{'ndcg@10': 0.42, ...} para um único run.

    `make_comparable=True` porque o ranx aborta se o run não cobrir exatamente
    as mesmas consultas do qrels; consulta que não recuperou nada entra
    valendo 0, que é a leitura correta.
    """
    scores = evaluate(qrels, run, list(metrics), make_comparable=True)
    if isinstance(scores, dict):
        return {k: float(v) for k, v in scores.items()}
    # ranx devolve escalar quando recebe uma métrica só.
    return {metrics[0]: float(scores)}


def evaluate_runs(qrels: Qrels, runs: list[Run], metrics=DEFAULT_METRICS) -> list[dict]:
    """Uma linha por run, pronta para virar `main_results.csv`.

    O nome do run segue a convenção de arquivo da F4
    (`{estrategia}__{retriever}[__{agregacao}]`) e é quebrado em colunas para
    a tabela do artigo poder ser pivotada por estratégia x retriever.
    """
    rows = []
    for run in runs:
        parts = run.name.split("__")
        row = {
            "run": run.name,
            "estrategia": parts[0] if parts else run.name,
            "retriever": parts[1] if len(parts) > 1 else "",
            "agregacao": parts[2] if len(parts) > 2 else "max_pooling",
        }
        row.update(evaluate_run(qrels, run, metrics))
        rows.append(row)
    return rows


def paired_significance(
    qrels: Qrels,
    runs: list[Run],
    metric: str = "ndcg@10",
    stat_test: str = "student",
    max_p: float = 0.05,
):
    """Comparação pareada de TODOS os runs entre si, com correção de Bonferroni
    para comparações múltiplas (é o que o `ranx.compare` faz internamente).

    Comparar 10 runs dois a dois são 45 testes: sem correção, ~2 "diferenças
    significativas" apareceriam só por acaso a p<0.05. É exatamente o erro que
    a banca procura numa tabela de significância.
    """
    return compare(
        qrels,
        runs=runs,
        metrics=[metric],
        stat_test=stat_test,
        max_p=max_p,
        make_comparable=True,
    )


def significance_rows(report, metric: str = "ndcg@10") -> list[dict]:
    """Achata o `Report` do ranx em linhas para `significance.csv`.

    O `Report.comparisons` é um `FrozensetDict`: a chave é `frozenset({a, b})`,
    não um dicionário aninhado `[a][b]`. E `win_tie_loss` é indexado pela TUPLA
    ordenada `(a, b)`, que é o que dá o sentido da diferença (quem ganhou em
    quantas queries) — o p-valor sozinho não diz quem foi melhor.
    """
    rows = []
    names = list(report.model_names)
    wtl = getattr(report, "win_tie_loss", {}) or {}
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            entry = report.comparisons[frozenset({a, b})]
            if metric not in entry:
                continue
            p_value = float(entry[metric]["p_value"])
            counts = wtl.get((a, b), {}).get(metric, {})
            rows.append(
                {
                    "metric": metric,
                    "run_a": a,
                    "run_b": b,
                    "p_value": p_value,
                    "significativo_p<0.05": p_value < 0.05,
                    "wins_a": counts.get("W", ""),
                    "ties": counts.get("T", ""),
                    "losses_a": counts.get("L", ""),
                }
            )
    return rows


def report_to_text(report) -> str:
    """`str(report)` usa superscritos Unicode que o console cp1252 do Windows
    não consegue imprimir (UnicodeEncodeError). Como o relatório vai para
    arquivo, devolvemos o texto e quem imprime decide."""
    return str(report)


# --- CLI: gera as tabelas finais do TCC -------------------------------------

def load_doc_lengths(corpus_path: Path, cache_path: Path | None = None) -> dict[str, int]:
    """{doc_id: n_tokens}, para o recorte por tercil de tamanho.

    A seção 2 do `plano_implementacao.md` especifica `n_tokens` como campo do
    `corpus_docs.jsonl`, mas o `ingest.py` não o grava (o `corpus_stats()`
    calcula as contagens e as descarta depois de montar o EDA). Então:
    usamos o campo quando ele existir e, senão, contamos aqui — cacheando o
    resultado, porque tokenizar o corpus inteiro leva minutos e o recorte não
    muda entre execuções.
    """
    import json as _json

    if cache_path is None:
        cache_path = corpus_path.parent / "doc_lengths.json"
    if cache_path.exists():
        return {k: int(v) for k, v in _json.loads(cache_path.read_text(encoding="utf-8")).items()}

    from .tokenization import count_tokens

    lengths: dict[str, int] = {}
    precisou_contar = False
    with corpus_path.open(encoding="utf-8") as f:
        for line in f:
            d = _json.loads(line)
            n = d.get("n_tokens")
            if n is None:
                if not precisou_contar:
                    print(
                        "  corpus_docs.jsonl sem 'n_tokens' — contando (uma vez; "
                        f"o resultado fica em {cache_path.name})",
                        flush=True,
                    )
                    precisou_contar = True
                n = count_tokens(d["text"])
            lengths[d["doc_id"]] = int(n)
    cache_path.write_text(_json.dumps(lengths), encoding="utf-8")
    return lengths


def _write_csv(path: Path, rows: list[dict]) -> None:
    import csv as _csv

    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    import argparse
    import json

    from .analysis import (
        slice_by_doc_length_tercile,
        slice_by_query_type,
        slice_by_retriever,
    )
    from .ingest import INTERIM_DIR

    repo_root = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(
        description="Avalia os TREC runs e grava as tabelas de results/tables/."
    )
    parser.add_argument("--runs-dir", type=Path, default=repo_root / "results" / "runs")
    parser.add_argument("--tables-dir", type=Path, default=repo_root / "results" / "tables")
    parser.add_argument("--qrels", type=Path, default=INTERIM_DIR / "qrels.trec")
    parser.add_argument("--queries", type=Path, default=INTERIM_DIR / "queries.jsonl")
    parser.add_argument("--corpus", type=Path, default=INTERIM_DIR / "corpus_docs.jsonl")
    parser.add_argument("--metric", default="ndcg@10", help="Métrica dos recortes/significância.")
    args = parser.parse_args()

    run_paths = sorted(args.runs_dir.glob("*.trec"))
    if not run_paths:
        raise SystemExit(
            f"nenhum run em {args.runs_dir} — rode `python -m src.run_experiments` antes"
        )
    qrels = load_qrels(args.qrels)
    runs = [load_run(p) for p in run_paths]
    print(f"{len(runs)} runs, qrels de {args.qrels.name}", flush=True)

    # 1. Tabela principal: estratégia x retriever x métricas.
    rows = evaluate_runs(qrels, runs)
    _write_csv(args.tables_dir / "main_results.csv", rows)
    for r in sorted(rows, key=lambda r: -r["ndcg@10"]):
        print(f"  {r['run']:<45} nDCG@10={r['ndcg@10']:.4f}  MAP@10={r['map@10']:.4f}")

    # 2. Significância pareada (só faz sentido com 2+ runs).
    if len(runs) > 1:
        report = paired_significance(qrels, runs, metric=args.metric)
        _write_csv(args.tables_dir / "significance.csv", significance_rows(report, args.metric))
        (args.tables_dir / "significance_report.txt").write_text(
            report_to_text(report), encoding="utf-8"
        )

    # 3. Recortes analíticos.
    if args.queries.exists():
        meta = {}
        with args.queries.open(encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                meta[d["query_id"]] = d.get("source", "desconhecido")
        _write_csv(
            args.tables_dir / "slices_query_type.csv",
            slice_by_query_type(qrels, runs, meta, args.metric),
        )

    if args.corpus.exists():
        lengths = load_doc_lengths(args.corpus)
        _write_csv(
            args.tables_dir / "slices_doc_length.csv",
            slice_by_doc_length_tercile(qrels, runs, lengths, args.metric),
        )

    _write_csv(
        args.tables_dir / "slices_retriever.csv",
        slice_by_retriever(qrels, runs, args.metric),
    )
    print(f"tabelas gravadas em {args.tables_dir}")


if __name__ == "__main__":
    main()
