"""CLI da F3: gera chunks para as estratégias configuradas em
`configs/chunkers.yaml` e grava `data/processed/{estrategia}/chunks.jsonl`
(contrato de dados — seção 2 do plano_implementacao.md).

Uso:
    python -m src.chunkers.run --strategy all
    python -m src.chunkers.run --strategy fixed_512_256
    python -m src.chunkers.run --strategy all --limit-docs 500   # smoke test
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

import yaml

from ..ingest import INTERIM_DIR
from ..segmenter.segment import Segmenter
from .base import Chunker, Document
from .fixed import FixedChunker
from .recursive import RecursiveChunker
from .structural import StructuralChunker

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "chunkers.yaml"
PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_chunkers(config: dict) -> dict[str, Chunker]:
    chunkers: dict[str, Chunker] = {}

    for cfg in config["fixed"]:
        chunkers[cfg["name"]] = FixedChunker(size=cfg["size"], stride=cfg["stride"], name=cfg["name"])

    rcfg = config["recursive"]
    chunkers[rcfg["name"]] = RecursiveChunker(
        chunk_size=rcfg["chunk_size"],
        chunk_overlap=rcfg["chunk_overlap"],
        separators=rcfg["separators"],
        name=rcfg["name"],
    )

    segmenter = Segmenter()
    for cfg in config["structural"]:
        chunkers[cfg["name"]] = StructuralChunker(
            max_section_tokens=cfg["max_section_tokens"],
            overlap=cfg["overlap"],
            span_source=cfg["span_source"],
            segmenter=segmenter if cfg["span_source"] == "pred" else None,
            name=cfg["name"],
        )

    return chunkers


def iter_corpus_docs(path: Path, limit: int | None = None) -> Iterator[Document]:
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                break
            doc = json.loads(line)
            yield Document(doc_id=doc["doc_id"], text=doc["text"], gold_spans=doc["gold_spans"])


def run_strategy(name: str, chunker: Chunker, corpus_path: Path, out_dir: Path, limit: int | None) -> int:
    strategy_dir = out_dir / name
    strategy_dir.mkdir(parents=True, exist_ok=True)
    n_chunks = 0
    with (strategy_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for doc in iter_corpus_docs(corpus_path, limit):
            for chunk in chunker.chunk(doc):
                f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
                n_chunks += 1
    return n_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera chunks para as estratégias configuradas.")
    parser.add_argument("--strategy", default="all", help="Nome da estratégia ou 'all'.")
    parser.add_argument("--limit-docs", type=int, default=None, help="Smoke test: limita nº de docs lidos.")
    parser.add_argument("--corpus", type=Path, default=INTERIM_DIR / "corpus_docs.jsonl")
    parser.add_argument("--out-dir", type=Path, default=PROCESSED_DIR)
    args = parser.parse_args()

    chunkers = build_chunkers(load_config())
    names = list(chunkers.keys()) if args.strategy == "all" else [args.strategy]
    for name in names:
        if name not in chunkers:
            raise SystemExit(f"estratégia desconhecida: {name!r} (opções: {list(chunkers.keys())})")
        n_chunks = run_strategy(name, chunkers[name], args.corpus, args.out_dir, args.limit_docs)
        print(f"{name}: {n_chunks} chunks")


if __name__ == "__main__":
    main()
