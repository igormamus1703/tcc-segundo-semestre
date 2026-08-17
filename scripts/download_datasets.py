#!/usr/bin/env python3
"""
Baixa os datasets do projeto a partir do Hugging Face Hub e os organiza em
data/<nome_do_dataset>/.

Uso:
    python scripts/download_datasets.py                # baixa todos os datasets
    python scripts/download_datasets.py juristcu        # baixa só um dataset
    python scripts/download_datasets.py --force         # rebaixa mesmo se já existir

Não requer dependências externas (usa apenas a stdlib).
"""

import argparse
import sys
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATASETS = {
    "juristcu": {
        "base_url": "https://huggingface.co/datasets/LeandroRibeiro/JurisTCU/resolve/main",
        "files": ["doc.csv", "qrel.csv", "query.csv"],
    },
    "jurisprudencias_stj": {
        "base_url": "https://huggingface.co/datasets/celsowm/jurisprudencias_stj/resolve/main",
        "files": ["jurisprudencias_stj.parquet"],
    },
    "brazilian_court_decisions": {
        "base_url": "https://huggingface.co/datasets/joelniklaus/brazilian_court_decisions/resolve/main",
        "files": ["train.jsonl", "test.jsonl", "validation.jsonl"],
    },
}


def format_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"


def download_file(url: str, dest: Path, force: bool) -> None:
    if dest.exists() and not force:
        print(f"  [skip] {dest.name} já existe ({format_size(dest.stat().st_size)})")
        return

    print(f"  [down] {dest.name}")

    def report(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(downloaded / total_size * 100, 100)
            sys.stdout.write(
                f"\r        {format_size(downloaded)} / {format_size(total_size)} ({pct:5.1f}%)"
            )
        else:
            sys.stdout.write(f"\r        {format_size(downloaded)}")
        sys.stdout.flush()

    tmp_dest = dest.with_suffix(dest.suffix + ".part")
    try:
        urllib.request.urlretrieve(url, tmp_dest, reporthook=report)
        tmp_dest.rename(dest)
    finally:
        sys.stdout.write("\n")
        if tmp_dest.exists():
            tmp_dest.unlink()


def download_dataset(name: str, force: bool) -> None:
    spec = DATASETS[name]
    dest_dir = DATA_DIR / name
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {name} ===")
    for filename in spec["files"]:
        url = f"{spec['base_url']}/{filename}"
        download_file(url, dest_dir / filename, force)


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa os datasets do projeto.")
    parser.add_argument(
        "datasets",
        nargs="*",
        choices=list(DATASETS.keys()),
        default=[],
        help="Nomes dos datasets a baixar (padrão: todos).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebaixa os arquivos mesmo que já existam localmente.",
    )
    args = parser.parse_args()

    names = args.datasets if args.datasets else list(DATASETS.keys())
    for name in names:
        download_dataset(name, args.force)

    print("\nConcluído.")


if __name__ == "__main__":
    main()
