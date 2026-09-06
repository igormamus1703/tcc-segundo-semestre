"""Rastreabilidade das rodadas: pasta datada + manifesto + log.

Toda rodada de experimento grava numa pasta própria, nomeada com data e hora,
contendo tudo o que é preciso para responder "de onde veio este número?" —
que é a pergunta que a banca faz e que a gente não quer estar tentando lembrar
em novembro.

O manifesto registra o commit, o hardware, as versões das bibliotecas, a
configuração do modelo e os tempos. Sem isso, dois resultados diferentes
gerados com semanas de distância viram um mistério insolúvel.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_ROOT = REPO_ROOT / "results"
EXPERIMENTS_DIR = RESULTS_ROOT / "experiments"


def timestamp_slug(quando: datetime | None = None) -> str:
    """`20260906-1435` — ordenável alfabeticamente, legível, sem caractere que
    o Windows recuse em nome de pasta (por isso não é ISO com ':')."""
    return (quando or datetime.now()).strftime("%Y%m%d-%H%M")


def _git_info() -> dict:
    def git(*args):
        try:
            return subprocess.run(
                ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
            ).stdout.strip()
        except Exception:
            return ""

    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "sujo": bool(git("status", "--porcelain")),
    }


def _versoes() -> dict:
    v = {"python": sys.version.split()[0]}
    for mod in ("torch", "sentence_transformers", "faiss", "bm25s", "ranx", "tiktoken", "numpy"):
        try:
            v[mod] = __import__(mod).__version__
        except Exception:
            v[mod] = None
    return v


def _hardware() -> dict:
    info = {
        "so": f"{platform.system()} {platform.release()}",
        "cpu": platform.processor(),
        "gpu": None,
        "vram_gb": None,
    }
    try:
        import torch

        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
            info["vram_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / 1024**3, 1
            )
    except Exception:
        pass
    return info


class Experimento:
    """Uma rodada. Cria `results/experiments/<data>-<hora>_<rotulo>/` com
    `runs/`, `tables/`, `execucao.log` e `manifest.json`.

    Uso:
        with Experimento("bm25", config={...}) as exp:
            ...
            exp.registrar("fixed_512_256", {"chunks": 907914, "segundos": 426})
    """

    def __init__(self, rotulo: str, config: dict | None = None, raiz: Path | None = None):
        self.rotulo = rotulo
        self.inicio = datetime.now()
        base = raiz or EXPERIMENTS_DIR
        self.dir = base / f"{timestamp_slug(self.inicio)}_{rotulo}"
        self.runs_dir = self.dir / "runs"
        self.tables_dir = self.dir / "tables"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "execucao.log"
        self._t0 = time.time()
        self.manifest = {
            "rotulo": rotulo,
            "inicio": self.inicio.isoformat(timespec="seconds"),
            "fim": None,
            "duracao_s": None,
            "comando": " ".join(sys.argv),
            "config": config or {},
            "git": _git_info(),
            "versoes": _versoes(),
            "hardware": _hardware(),
            "etapas": [],
        }
        self._gravar_manifest()

    # -- log --
    def log(self, msg: str, echo: bool = True) -> None:
        linha = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(linha + "\n")
        if echo:
            print(msg, flush=True)

    def registrar(self, nome: str, dados: dict) -> None:
        """Uma etapa concluída (uma estratégia, por exemplo)."""
        self.manifest["etapas"].append({"nome": nome, **dados})
        self._gravar_manifest()

    def _gravar_manifest(self) -> None:
        self.manifest["duracao_s"] = round(time.time() - self._t0, 1)
        with (self.dir / "manifest.json").open("w", encoding="utf-8") as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)

    # -- ciclo de vida --
    def __enter__(self) -> "Experimento":
        self.log(f"experimento {self.dir.name}")
        hw = self.manifest["hardware"]
        self.log(f"  hardware: {hw['gpu'] or hw['cpu']}" + (f" ({hw['vram_gb']}G)" if hw["vram_gb"] else ""))
        g = self.manifest["git"]
        self.log(f"  commit: {g['commit'][:8]}{' (arvore suja)' if g['sujo'] else ''} em {g['branch']}")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.manifest["fim"] = datetime.now().isoformat(timespec="seconds")
        self.manifest["erro"] = f"{exc_type.__name__}: {exc}" if exc_type else None
        self._gravar_manifest()
        dur = self.manifest["duracao_s"]
        self.log(f"fim em {dur/60:.1f} min -> {self.dir}", echo=True)
        _atualizar_indice()


def _atualizar_indice() -> None:
    """Reescreve `results/experiments/INDICE.md` a partir dos manifestos —
    a lista sempre reflete o que está no disco, sem edição manual."""
    if not EXPERIMENTS_DIR.exists():
        return
    linhas = [
        "# Índice de experimentos",
        "",
        "Gerado automaticamente por `src/experiment.py` ao fim de cada rodada.",
        "Não editar à mão.",
        "",
        "| Rodada | Início | Duração | Commit | Hardware | Etapas |",
        "|---|---|---|---|---|---|",
    ]
    for d in sorted(EXPERIMENTS_DIR.iterdir(), reverse=True):
        mf = d / "manifest.json"
        if not mf.is_file():
            continue
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        dur = m.get("duracao_s") or 0
        hw = m.get("hardware", {})
        linhas.append(
            f"| [`{d.name}`]({d.name}/) | {m.get('inicio','')} | {dur/60:.0f} min "
            f"| `{(m.get('git') or {}).get('commit','')[:8]}` "
            f"| {hw.get('gpu') or hw.get('cpu') or '?'} | {len(m.get('etapas', []))} |"
        )
    (EXPERIMENTS_DIR / "INDICE.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
