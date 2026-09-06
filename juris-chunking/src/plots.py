"""Figuras do artigo, geradas a partir das tabelas de uma rodada.

Só consome `results/experiments/<rodada>/tables/*.csv` — não recalcula nada.
Cada figura sai em PDF (para o LaTeX) e PNG (para olhar rápido e para o pôster).

Uso:
    python -m src.plots                        # usa a rodada mais recente
    python -m src.plots --experiment results/experiments/20260906-0515_bm25
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sem display: o script roda em terminal
import matplotlib.pyplot as plt  # noqa: E402

# Paleta sóbria e legível em impressão P&B (o pôster pode sair impresso).
CORES = {
    "structural_gold": "#1b4965",
    "structural_pred": "#5fa8d3",
    "fixed_1024_512": "#bc4749",
    "fixed_512_256": "#e09f3e",
    "recursive_default": "#6a994e",
}
ROTULOS = {
    "structural_gold": "estrutural (ouro)",
    "structural_pred": "estrutural (predito)",
    "fixed_1024_512": "fixo 1024/512",
    "fixed_512_256": "fixo 512/256",
    "recursive_default": "recursivo",
}


def ler_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _salvar(fig, destino: Path, nome: str) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(destino / f"{nome}.{ext}", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  {nome}.pdf / .png")


def _estilo(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.7)
    ax.set_axisbelow(True)


def fig_principal(rows: list[dict], destino: Path) -> None:
    """Métricas por estratégia, agrupadas por retriever."""
    if not rows:
        return
    metricas = ["ndcg@10", "mrr@10", "map@10", "recall@100"]
    retrievers = sorted({r["retriever"] for r in rows})

    fig, axes = plt.subplots(1, len(metricas), figsize=(4.2 * len(metricas), 4.2))
    if len(metricas) == 1:
        axes = [axes]
    for ax, met in zip(axes, metricas):
        estrategias = sorted({r["estrategia"] for r in rows})
        largura = 0.8 / max(len(retrievers), 1)
        for i, ret in enumerate(retrievers):
            valores, posicoes = [], []
            for j, est in enumerate(estrategias):
                achado = [r for r in rows if r["estrategia"] == est and r["retriever"] == ret]
                if achado:
                    valores.append(float(achado[0][met]))
                    posicoes.append(j + i * largura)
            ax.bar(posicoes, valores, largura * 0.9,
                   label=ret, alpha=0.85 if i == 0 else 0.6,
                   color=[CORES.get(e, "#888") for e in estrategias][: len(valores)],
                   edgecolor="white", linewidth=0.8,
                   hatch="" if i == 0 else "//")
        ax.set_xticks([j + largura * (len(retrievers) - 1) / 2 for j in range(len(estrategias))])
        ax.set_xticklabels([ROTULOS.get(e, e) for e in estrategias], rotation=35, ha="right")
        ax.set_title(met.upper())
        _estilo(ax)
    axes[0].set_ylabel("valor da métrica")
    if len(retrievers) > 1:
        from matplotlib.patches import Patch
        axes[-1].legend(handles=[Patch(facecolor="#888", hatch="" if i == 0 else "//",
                                       label=r) for i, r in enumerate(retrievers)],
                        loc="upper right", frameon=False)
    fig.suptitle("Estratégias de chunking por retriever", y=1.02, fontsize=13)
    _salvar(fig, destino, "fig_resultados_principais")


def fig_recorte(rows: list[dict], destino: Path, nome: str, titulo: str,
                ordem: list[str] | None = None) -> None:
    """Recorte com barras e intervalo de confiança de 95%."""
    if not rows:
        return
    valores = ordem or sorted({r["valor"] for r in rows})
    runs = sorted({r["run"] for r in rows})

    fig, ax = plt.subplots(figsize=(1.9 * len(valores) + 4, 4.4))
    largura = 0.8 / max(len(runs), 1)
    for i, run in enumerate(runs):
        est = run.split("__")[0]
        medias, erros, pos = [], [], []
        for j, val in enumerate(valores):
            achado = [r for r in rows if r["run"] == run and r["valor"] == val]
            if not achado:
                continue
            m = float(achado[0]["media"])
            lo, hi = float(achado[0]["ic95_inf"]), float(achado[0]["ic95_sup"])
            medias.append(m)
            erros.append([m - lo, hi - m])
            pos.append(j + i * largura)
        if not medias:
            continue
        err = list(zip(*erros))
        ax.bar(pos, medias, largura * 0.88, label=ROTULOS.get(est, est),
               color=CORES.get(est, "#888"), edgecolor="white", linewidth=0.7)
        ax.errorbar(pos, medias, yerr=err, fmt="none", ecolor="#333",
                    elinewidth=1.1, capsize=3)
    ax.set_xticks([j + largura * (len(runs) - 1) / 2 for j in range(len(valores))])
    ax.set_xticklabels(valores)
    ax.set_ylabel("nDCG@10 (IC 95%)")
    ax.set_title(titulo)
    ax.legend(frameon=False, fontsize=9, ncol=2)
    _estilo(ax)
    _salvar(fig, destino, nome)


def fig_secoes(rows: list[dict], destino: Path) -> None:
    """De qual seção do acórdão vem o chunk que fez o documento ser recuperado."""
    if not rows:
        return
    ordem_sec = ["ementa", "relatorio", "fundamentacao", "dispositivo", "indefinido"]
    por_run: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        por_run[r["run"]][r["valor"]] = float(r["fracao"])
    runs = sorted(por_run)

    fig, ax = plt.subplots(figsize=(9, 4.6))
    fundo = [0.0] * len(runs)
    cores_sec = ["#e09f3e", "#6a994e", "#1b4965", "#bc4749", "#adb5bd"]
    for sec, cor in zip(ordem_sec, cores_sec):
        vals = [por_run[r].get(sec, 0.0) for r in runs]
        if not any(vals):
            continue
        ax.barh(range(len(runs)), vals, left=fundo, label=sec, color=cor,
                edgecolor="white", linewidth=0.7)
        fundo = [f + v for f, v in zip(fundo, vals)]
    ax.set_yticks(range(len(runs)))
    ax.set_yticklabels([ROTULOS.get(r.split("__")[0], r.split("__")[0]) for r in runs])
    ax.set_xlabel("fração dos chunks recuperados no top-10")
    ax.set_title("Seção do acórdão de onde vem o trecho recuperado")
    ax.legend(frameon=False, ncol=5, fontsize=9, loc="lower center",
              bbox_to_anchor=(0.5, -0.28))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    _salvar(fig, destino, "fig_secoes_recuperadas")


def fig_significancia(rows: list[dict], destino: Path) -> None:
    """Matriz de p-valores entre os runs, com o limiar de 0,05 destacado."""
    if not rows:
        return
    import numpy as np

    runs = sorted({r["run_a"] for r in rows} | {r["run_b"] for r in rows})
    idx = {r: i for i, r in enumerate(runs)}
    m = np.full((len(runs), len(runs)), np.nan)
    for r in rows:
        i, j = idx[r["run_a"]], idx[r["run_b"]]
        p = float(r["p_value"])
        m[i, j] = m[j, i] = p

    fig, ax = plt.subplots(figsize=(1.1 * len(runs) + 4, 1.0 * len(runs) + 3))
    im = ax.imshow(m, cmap="RdYlGn_r", vmin=0, vmax=1)
    for i in range(len(runs)):
        for j in range(len(runs)):
            if not np.isnan(m[i, j]):
                marca = "*" if m[i, j] < 0.05 else ""
                ax.text(j, i, f"{m[i, j]:.3f}{marca}", ha="center", va="center",
                        fontsize=8, color="#111")
    rot = [ROTULOS.get(r.split("__")[0], r) for r in runs]
    ax.set_xticks(range(len(runs)), rot, rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(len(runs)), rot, fontsize=8)
    ax.set_title("p-valores pareados (nDCG@10)\n* = p < 0,05 após correção", fontsize=11)
    fig.colorbar(im, ax=ax, shrink=0.75, label="p-valor")
    _salvar(fig, destino, "fig_significancia")


def main() -> None:
    from .experiment import EXPERIMENTS_DIR

    ap = argparse.ArgumentParser(description="Gera as figuras a partir das tabelas.")
    ap.add_argument("--experiment", type=Path, default=None)
    args = ap.parse_args()

    exp = args.experiment
    if exp is None:
        candidatos = [d for d in sorted(EXPERIMENTS_DIR.iterdir(), reverse=True)
                      if d.is_dir() and (d / "tables" / "main_results.csv").is_file()]
        if not candidatos:
            raise SystemExit("nenhuma rodada com tabelas; rode `python -m src.evaluate` antes")
        exp = candidatos[0]

    tabelas, figuras = exp / "tables", exp / "figuras"
    print(f"rodada: {exp.name}")
    fig_principal(ler_csv(tabelas / "main_results.csv"), figuras)
    fig_recorte(ler_csv(tabelas / "slices_query_type.csv"), figuras,
                "fig_recorte_tipo_consulta", "Desempenho por tipo de consulta")
    fig_recorte(ler_csv(tabelas / "slices_doc_length.csv"), figuras,
                "fig_recorte_tamanho_doc", "Desempenho por tamanho de documento",
                ordem=["curto", "medio", "longo"])
    fig_secoes(ler_csv(tabelas / "slices_section.csv"), figuras)
    fig_significancia(ler_csv(tabelas / "significance.csv"), figuras)
    print(f"figuras em {figuras}")


if __name__ == "__main__":
    main()
