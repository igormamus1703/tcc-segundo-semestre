"""F4 — Runs: estratégia de chunking x retriever -> arquivo TREC.

Para cada par (estratégia, retriever): busca os top-N CHUNKS de cada consulta,
agrega chunk -> documento e grava o ranking de documentos no formato TREC
(`results/runs/{estrategia}__{retriever}[__{agregacao}].trec`).

A agregação é o ponto metodológico delicado: o índice é de chunks, mas os
qrels são de documentos. Buscamos fundo em chunks (`--top-chunks`, 2000 por
padrão) justamente para que documentos longos, cujos chunks se espalham pelo
ranking, não sejam truncados antes da agregação.

Uso:
    python -m src.run_experiments --strategy all --retriever bm25
    python -m src.run_experiments --strategy all --retriever bm25 --limit-queries 10
    python -m src.run_experiments --strategy structural_gold --retriever dense
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml

from .chunkers.base import Chunk
from .chunkers.run import PROCESSED_DIR
from .experiment import Experimento
from .ingest import INTERIM_DIR
from .retrieval import max_pooling, sum_top_k

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNS_DIR = REPO_ROOT / "results" / "runs"
MODELS_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "models.yaml"

AGGREGATIONS = {"max_pooling": max_pooling, "sum_top_k": sum_top_k}


def load_models_config(path: Path = MODELS_CONFIG) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_queries(path: Path, limit: int | None = None) -> list[dict]:
    queries = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                break
            queries.append(json.loads(line))
    return queries


def load_chunks(strategy: str, processed_dir: Path = PROCESSED_DIR) -> list[Chunk]:
    path = processed_dir / strategy / "chunks.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} nao existe. Rode antes: "
            f"python -m src.chunkers.run --strategy {strategy}"
        )
    chunks = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            chunks.append(
                Chunk(
                    chunk_id=d["chunk_id"],
                    doc_id=d["doc_id"],
                    text=d["text"],
                    section=d.get("section"),
                    start=d["start"],
                    end=d["end"],
                )
            )
    return chunks


def build_index(retriever: str, chunks: list[Chunk], models_cfg: dict, embedder: str | None):
    """Devolve um índice já construído, com a interface comum
    (`search_batch`, `chunk_ids`, `doc_ids`)."""
    if retriever == "bm25":
        from .indexing.lexical import BM25Index

        index = BM25Index(backend=models_cfg.get("lexical", {}).get("backend", "bm25s"))
        index.build(chunks)
        return index

    if retriever == "dense":
        from .indexing.dense import DenseIndex

        embedders = {e["name"]: e for e in models_cfg["embedders"]}
        name = embedder or models_cfg.get("dense", {}).get("default_embedder")
        if name not in embedders:
            raise SystemExit(f"embedder desconhecido: {name!r} (opcoes: {list(embedders)})")
        cfg = embedders[name]
        if cfg["hf_id"] == "PREENCHER":
            raise SystemExit(f"embedder {name!r} esta com hf_id 'PREENCHER' em models.yaml")
        return DenseIndex(
            model_name=cfg["hf_id"],
            query_prefix=cfg.get("query_prefix", ""),
            passage_prefix=cfg.get("passage_prefix", ""),
            batch_size=cfg.get("batch_size", 64),
            max_seq_length=cfg.get("max_seq_length"),
            dtype=cfg.get("dtype", "auto"),
        )

    raise SystemExit(f"retriever desconhecido: {retriever!r} (use 'bm25' ou 'dense')")


def write_trec_run(path: Path, ranked: dict[str, list[tuple[str, float]]], run_name: str) -> int:
    """`qid Q0 docid rank score nome` — uma linha por documento recuperado."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n_lines = 0
    with path.open("w", encoding="utf-8") as f:
        for qid, docs in ranked.items():
            for rank, (doc_id, score) in enumerate(docs, start=1):
                f.write(f"{qid} Q0 {doc_id} {rank} {score:.6f} {run_name}\n")
                n_lines += 1
    return n_lines


def write_chunks_top(
    path: Path,
    ranked: dict[str, list[tuple[str, float]]],
    vencedores: dict[str, dict[str, tuple[str, float]]],
    por_id: dict[str, Chunk],
    run_name: str,
    top_k: int = 50,
) -> int:
    """Grava o chunk que "ganhou" cada documento recuperado, com seu offset.

    Só os `top_k` primeiros documentos de cada consulta — é o que a análise por
    seção usa, e guardar os 1000 multiplicaria o arquivo sem serventia.
    """
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for qid, docs in ranked.items():
            for rank, (doc_id, score) in enumerate(docs[:top_k], start=1):
                venc = vencedores.get(qid, {}).get(doc_id)
                if not venc:
                    continue
                chunk = por_id.get(venc[0])
                if chunk is None:
                    continue
                f.write(json.dumps({
                    "run": run_name, "query_id": qid, "rank": rank,
                    "doc_id": doc_id, "chunk_id": chunk.chunk_id,
                    "section": chunk.section, "start": chunk.start, "end": chunk.end,
                    "score": round(float(score), 6),
                }, ensure_ascii=False) + "\n")
                n += 1
    return n


def run_one(
    strategy: str,
    retriever: str,
    queries: list[dict],
    models_cfg: dict,
    top_chunks: int = 2000,
    top_docs: int = 1000,
    aggregation: str = "max_pooling",
    embedder: str | None = None,
    processed_dir: Path = PROCESSED_DIR,
    runs_dir: Path = RUNS_DIR,
    log=None,
    bloco: int = 25_000,
) -> dict:
    t0 = time.time()
    chunks = load_chunks(strategy, processed_dir)
    index = build_index(retriever, chunks, models_cfg, embedder)

    # O nome do retriever no run carrega o modelo denso usado: sem isso, rodar
    # dois embedders sobrescreveria o run do outro, silenciosamente.
    if retriever == "dense":
        nome_embedder = embedder or models_cfg.get("dense", {}).get("default_embedder")
        retriever_tag = f"dense-{nome_embedder}"
        (log or print)(f"  [{strategy}] {index.describe()}")
        # Cache dos embeddings junto dos chunks da estratégia (contrato da
        # secao 2 do plano_implementacao.md).
        index.build(chunks, cache_dir=processed_dir / strategy,
                    show_progress=False, log=log or print, bloco=bloco)
    else:
        retriever_tag = retriever

    chunk_to_doc = dict(zip(index.chunk_ids, index.doc_ids))
    por_id = {c.chunk_id: c for c in chunks}
    agg_fn = AGGREGATIONS[aggregation]

    results = index.search_batch([q["text"] for q in queries], top_k=top_chunks)

    suffix = "" if aggregation == "max_pooling" else f"__{aggregation}"
    run_name = f"{strategy}__{retriever_tag}{suffix}"

    ranked: dict[str, list[tuple[str, float]]] = {}
    # Qual CHUNK deu o score de cada documento? É o que permite depois dizer de
    # qual macro-seção do acórdão veio o trecho que fez o documento ser
    # recuperado (`analysis.slice_by_section`) — inclusive nas baselines, que
    # não carregam rótulo de seção, mas carregam offset.
    vencedores: dict[str, dict[str, tuple[str, float]]] = {}
    for q, hits in zip(queries, results):
        scored = [(cid, chunk_to_doc[cid], score) for cid, score in hits]
        doc_scores = agg_fn(scored)
        ranked[q["query_id"]] = sorted(doc_scores.items(), key=lambda kv: -kv[1])[:top_docs]
        melhor: dict[str, tuple[str, float]] = {}
        for cid, doc_id, score in scored:
            if doc_id not in melhor or score > melhor[doc_id][1]:
                melhor[doc_id] = (cid, score)
        vencedores[q["query_id"]] = melhor

    n_lines = write_trec_run(runs_dir / f"{run_name}.trec", ranked, run_name)
    write_chunks_top(runs_dir / f"{run_name}__chunks.jsonl", ranked, vencedores,
                     por_id, run_name)

    return {
        "run": run_name,
        "n_chunks": len(chunks),
        "n_queries": len(queries),
        "n_linhas_run": n_lines,
        "segundos": round(time.time() - t0, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera TREC runs por estrategia x retriever.")
    parser.add_argument("--strategy", nargs="+", default=["all"],
                        help="Estrategias na ORDEM de execucao, ou 'all'. A ordem importa "
                             "numa rodada longa: o que roda primeiro e o que estara pronto "
                             "se algo interromper.")
    parser.add_argument("--retriever", default="bm25", choices=["bm25", "dense", "all"])
    parser.add_argument("--embedder", default=None, help="Nome em models.yaml (so para dense).")
    parser.add_argument("--aggregation", default="max_pooling", choices=list(AGGREGATIONS))
    parser.add_argument("--top-chunks", type=int, default=2000)
    parser.add_argument("--bloco", type=int, default=25_000,
                        help="Chunks por bloco de checkpoint no encode denso.")
    parser.add_argument("--top-docs", type=int, default=1000)
    parser.add_argument("--limit-queries", type=int, default=None, help="Smoke test.")
    parser.add_argument("--queries", type=Path, default=INTERIM_DIR / "queries.jsonl")
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--runs-dir", type=Path, default=None,
                        help="Se omitido, cria results/experiments/<data-hora>_<rotulo>/runs/.")
    parser.add_argument("--label", default=None, help="Rótulo da rodada (nome da pasta).")
    args = parser.parse_args()

    models_cfg = load_models_config()
    queries = load_queries(args.queries, args.limit_queries)
    if not queries:
        raise SystemExit(f"nenhuma consulta lida de {args.queries}")

    if args.strategy == ["all"]:
        # Ordem deliberada: as estrategias estruturais primeiro, porque sao as
        # que respondem a pergunta de pesquisa; as fixas, mais caras, por
        # ultimo. Numa rodada de ~10 h, se algo interromper, o que ja terminou
        # e o que mais importa.
        disponiveis = {p.name for p in args.processed_dir.iterdir() if p.is_dir()}
        preferencia = ["structural_gold", "structural_pred", "recursive_default",
                       "fixed_1024_512", "fixed_512_256"]
        strategies = [e for e in preferencia if e in disponiveis]
        strategies += sorted(disponiveis - set(strategies))
        if not strategies:
            raise SystemExit(
                f"nenhuma estrategia em {args.processed_dir} — rode "
                "`python -m src.chunkers.run` antes"
            )
    else:
        strategies = list(args.strategy)
        faltando = [e for e in strategies if not (args.processed_dir / e).is_dir()]
        if faltando:
            raise SystemExit(f"estrategia(s) sem chunks gerados: {faltando}")

    retrievers = ["bm25", "dense"] if args.retriever == "all" else [args.retriever]

    rotulo = args.label or _rotulo_automatico(args, retrievers, models_cfg)
    config = {
        "estrategias": strategies,
        "retrievers": retrievers,
        "embedder": args.embedder or models_cfg.get("dense", {}).get("default_embedder"),
        "agregacao": args.aggregation,
        "top_chunks": args.top_chunks,
        "top_docs": args.top_docs,
        "n_queries": len(queries),
        "limite_queries": args.limit_queries,
        "corpus": str(args.queries),
    }
    if "dense" in retrievers:
        nome = config["embedder"]
        cfg_emb = next((e for e in models_cfg["embedders"] if e["name"] == nome), {})
        config["modelo_denso"] = {k: cfg_emb.get(k) for k in
                                  ("hf_id", "max_seq_length", "batch_size", "dtype")}

    with Experimento(rotulo, config=config) as exp:
        runs_dir = args.runs_dir or exp.runs_dir
        for retriever in retrievers:
            for strategy in strategies:
                info = run_one(
                    strategy,
                    retriever,
                    queries,
                    models_cfg,
                    top_chunks=args.top_chunks,
                    top_docs=args.top_docs,
                    aggregation=args.aggregation,
                    embedder=args.embedder,
                    processed_dir=args.processed_dir,
                    runs_dir=runs_dir,
                    log=exp.log,
                    bloco=args.bloco,
                )
                exp.registrar(info["run"], info)
                exp.log(
                    f"{info['run']}: {info['n_chunks']:,} chunks, "
                    f"{info['n_linhas_run']:,} linhas, {info['segundos']}s"
                )


def _rotulo_automatico(args, retrievers, models_cfg) -> str:
    """Nome legível da pasta: diz o retriever, o modelo e se foi smoke test."""
    partes = ["-".join(retrievers)]
    if "dense" in retrievers:
        partes.append(args.embedder or models_cfg.get("dense", {}).get("default_embedder", ""))
    if args.strategy != ["all"]:
        partes.append("-".join(args.strategy))
    if args.limit_queries:
        partes.append(f"smoke{args.limit_queries}q")
    if args.aggregation != "max_pooling":
        partes.append(args.aggregation)
    return "_".join(p for p in partes if p)


if __name__ == "__main__":
    main()
