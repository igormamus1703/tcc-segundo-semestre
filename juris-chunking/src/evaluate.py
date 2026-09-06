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


def load_gold_spans(corpus_path: Path, cache_path: Path | None = None) -> dict[str, list[dict]]:
    """{doc_id: [{section, start, end}, ...]} para o recorte por seção.

    Lê o `corpus_docs.jsonl` uma vez e cacheia só os spans — o arquivo tem
    780 MB por causa do texto dos acórdãos, e os spans somam poucos MB.
    """
    import json as _json

    if cache_path is None:
        cache_path = corpus_path.parent / "gold_spans.json"
    if cache_path.exists():
        return _json.loads(cache_path.read_text(encoding="utf-8"))

    spans: dict[str, list[dict]] = {}
    with corpus_path.open(encoding="utf-8") as f:
        for line in f:
            d = _json.loads(line)
            spans[d["doc_id"]] = d.get("gold_spans", [])
    cache_path.write_text(_json.dumps(spans), encoding="utf-8")
    return spans


def _exigir_mesmo_corpus(a: Path, b: Path) -> None:
    """Duas rodadas só podem ser avaliadas juntas se mediram o MESMO corpus.

    Juntar uma rodada do corpus completo com uma de subcorpus produziria uma
    tabela em que metade dos runs foi avaliada contra qrels que não são os
    seus — números plausíveis à vista e completamente errados. Melhor abortar
    com a diferença na tela.
    """
    import json as _json

    def resumo(d: Path) -> dict:
        mf = d / "manifest.json"
        if not mf.is_file():
            return {}
        m = _json.loads(mf.read_text(encoding="utf-8"))
        return {
            "n_docs": (m.get("corpus") or {}).get("n_docs"),
            "n_queries": (m.get("config") or {}).get("n_queries"),
            "corpus": (m.get("config") or {}).get("corpus"),
        }

    ra, rb = resumo(a), resumo(b)
    if not ra or not rb:
        print(f"  aviso: sem manifesto para comparar corpus entre {a.name} e {b.name}")
        return
    difs = [k for k in ("n_docs", "n_queries", "corpus")
            if ra.get(k) is not None and rb.get(k) is not None and ra[k] != rb[k]]
    if difs:
        detalhes = "\n".join(f"    {k}: {a.name}={ra[k]!r}  vs  {b.name}={rb[k]!r}" for k in difs)
        raise SystemExit(
            f"as rodadas {a.name} e {b.name} não mediram o mesmo corpus:\n{detalhes}\n"
            "  Avaliá-las juntas cruzaria runs com qrels que não são os deles."
        )


def _desambiguar_nomes(runs: list, caminhos: list[Path]) -> None:
    """Prefixa com a rodada os runs cujo nome se repete entre rodadas.

    `fixed_1024_512__bm25` pode existir em duas rodadas; sem prefixo, o
    `Report.comparisons` do ranx — indexado por `frozenset({a, b})` — colapsa
    o par em um conjunto de um elemento e estoura com KeyError.
    """
    from collections import Counter

    contagem = Counter(r.name for r in runs)
    for run, caminho in zip(runs, caminhos):
        if contagem[run.name] > 1:
            run.name = f"{caminho.parent.parent.name}/{run.name}"


def _experimento_mais_recente(experiments_dir: Path) -> Path | None:
    """A pasta datada mais recente que tenha runs. O nome começa com
    `AAAAMMDD-HHMM`, então a ordem alfabética já é a cronológica."""
    if not experiments_dir.is_dir():
        return None
    candidatos = [
        d for d in sorted(experiments_dir.iterdir(), reverse=True)
        if d.is_dir() and any((d / "runs").glob("*.trec"))
    ]
    return candidatos[0] if candidatos else None


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
    from datetime import datetime

    from .analysis import (
        slice_by_doc_length_tercile,
        slice_by_query_type,
        poder_de_todos_os_pares,
        slice_by_retriever,
        slice_by_section,
    )
    from .ingest import INTERIM_DIR

    from .experiment import EXPERIMENTS_DIR

    parser = argparse.ArgumentParser(
        description="Avalia os TREC runs de um experimento e grava as tabelas nele. "
        "Sem --experiment nem --runs-dir, usa a rodada mais recente."
    )
    parser.add_argument("--experiment", type=Path, default=None,
                        help="Pasta em results/experiments/ (default: a mais recente).")
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--tables-dir", type=Path, default=None)
    parser.add_argument("--incluir", type=Path, nargs="+", default=None, metavar="RODADA",
                        help="Rodadas adicionais cujos runs entram na mesma avaliação. "
                             "É como se comparam BM25 e denso lado a lado, já que cada "
                             "um roda em sua própria rodada: a significância pareada e "
                             "os recortes passam a cruzar os dois retrievers.")
    parser.add_argument("--qrels", type=Path, default=INTERIM_DIR / "qrels.trec")
    parser.add_argument("--queries", type=Path, default=INTERIM_DIR / "queries.jsonl")
    parser.add_argument("--corpus", type=Path, default=INTERIM_DIR / "corpus_docs.jsonl")
    parser.add_argument("--metric", default="ndcg@10", help="Métrica dos recortes/significância.")
    parser.add_argument("--section-top-k", type=int, default=10,
                        help="Profundidade do recorte por seção do acórdão.")
    args = parser.parse_args()

    exp_dir = args.experiment or _experimento_mais_recente(EXPERIMENTS_DIR)
    runs_dir = args.runs_dir or (exp_dir / "runs" if exp_dir else None)
    tables_dir = args.tables_dir or (exp_dir / "tables" if exp_dir else None)
    if runs_dir is None:
        raise SystemExit(
            f"nenhum experimento em {EXPERIMENTS_DIR} — rode "
            "`python -m src.run_experiments` antes, ou passe --runs-dir"
        )
    args.tables_dir = tables_dir

    run_paths = sorted(runs_dir.glob("*.trec"))
    if not run_paths:
        raise SystemExit(
            f"nenhum run em {runs_dir} — rode `python -m src.run_experiments` antes"
        )
    print(f"experimento: {runs_dir.parent.name}", flush=True)

    # Rodadas adicionais: os runs entram na mesma avaliação, mas os
    # `__chunks.jsonl` também — senão o recorte por seção cobriria só metade
    # dos runs da tabela.
    dirs_de_runs = [runs_dir]
    for extra in args.incluir or []:
        extra_runs = extra / "runs" if (extra / "runs").is_dir() else extra
        novos = sorted(extra_runs.glob("*.trec"))
        if not novos:
            raise SystemExit(f"nenhum run em {extra_runs}")
        _exigir_mesmo_corpus(runs_dir.parent, extra_runs.parent)
        run_paths += novos
        dirs_de_runs.append(extra_runs)
        print(f"  + {extra_runs.parent.name} ({len(novos)} runs)", flush=True)
    qrels = load_qrels(args.qrels)
    runs = [load_run(p) for p in run_paths]
    _desambiguar_nomes(runs, run_paths)
    print(f"{len(runs)} runs, qrels de {args.qrels.name}", flush=True)

    # 1. Tabela principal: estratégia x retriever x métricas.
    rows = evaluate_runs(qrels, runs)
    _write_csv(args.tables_dir / "main_results.csv", rows)
    for r in sorted(rows, key=lambda r: -r["ndcg@10"]):
        print(f"  {r['run']:<45} nDCG@10={r['ndcg@10']:.4f}  MAP@10={r['map@10']:.4f}")
    resumo_avaliacao = {
        "quando": datetime.now().isoformat(timespec="seconds"),
        "metrica_principal": "ndcg@10",
        "por_run": {r["run"]: {m: round(r[m], 4) for m in DEFAULT_METRICS} for r in rows},
        "melhor_run": max(rows, key=lambda r: r["ndcg@10"])["run"],
    }

    # 2. Significância pareada (só faz sentido com 2+ runs).
    if len(runs) > 1:
        report = paired_significance(qrels, runs, metric=args.metric)
        _write_csv(args.tables_dir / "significance.csv", significance_rows(report, args.metric))
        (args.tables_dir / "significance_report.txt").write_text(
            report_to_text(report), encoding="utf-8"
        )
        # Sem isso, um resultado não significativo fica ambíguo entre "não há
        # diferença" e "o teste não teria como vê-la".
        _write_csv(
            args.tables_dir / "power_analysis.csv",
            poder_de_todos_os_pares(qrels, runs, args.metric),
        )
        sig = significance_rows(report, args.metric)
        resumo_avaliacao["significancia"] = {
            "metrica": args.metric,
            "pares": len(sig),
            "pares_p_menor_0_05": sum(1 for s in sig if s["p_value"] < 0.05),
            "menor_p": round(min((s["p_value"] for s in sig), default=1.0), 4),
        }

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

    # 4. Recorte por seção do acórdão: de qual parte do documento veio o trecho
    #    que fez cada documento ser recuperado. Vale para as baselines também,
    #    via offset (plano_tecnico.md §1).
    chunks_top = []
    for d in dirs_de_runs:
        for p in sorted(d.glob("*__chunks.jsonl")):
            with p.open(encoding="utf-8") as f:
                chunks_top.extend(json.loads(line) for line in f)
    if chunks_top and args.corpus.exists():
        gold = load_gold_spans(args.corpus)
        _write_csv(
            args.tables_dir / "slices_section.csv",
            slice_by_section(chunks_top, gold, top_k=args.section_top_k),
        )

    # 5. O manifesto da rodada passa a carregar o resumo da avaliação: um
    #    arquivo só responde "o que foi rodado" E "o que deu". É o que o
    #    INDICE.md lê para mostrar o nDCG de cada rodada de relance.
    manifesto = runs_dir.parent / "manifest.json"
    if manifesto.is_file():
        try:
            m = json.loads(manifesto.read_text(encoding="utf-8"))
            m["avaliacao"] = resumo_avaliacao
            manifesto.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
            from .experiment import _atualizar_indice

            _atualizar_indice()
        except Exception as e:  # a avaliação já está nas tabelas; não abortar por isso
            print(f"  aviso: não atualizei o manifesto ({type(e).__name__}: {e})")

    print(f"tabelas gravadas em {args.tables_dir}")


if __name__ == "__main__":
    main()
