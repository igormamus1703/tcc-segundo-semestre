"""F7 — Painel configuração × coleção: qual receita funciona nas duas tarefas?

A F6 recomendou uma receita olhando uma coleção. A F7 tem duas, e elas medem
tarefas diferentes (`01-colecao-jua.md`): achar *os* acórdãos de uma tese
(JurisTCU) e achar *o* acórdão de um enunciado (JUÁ-Juris). Uma recomendação
para o artigo precisa valer nas duas.

Este módulo cruza estratégia × condição × coleção num quadro só:

- `painel.csv`: nDCG@10 médio, IC 95% por bootstrap e Δ relativo ao BM25
  completo **da mesma estratégia**, para cada célula;
- figura `painel`: um heatmap por coleção, linhas = condições, colunas =
  estratégias, cor = Δ% contra o BM25 completo da mesma estratégia, número =
  nDCG@10 absoluto. Ler na horizontal responde "a estratégia importa?"; na
  vertical, "a condição importa?"; e comparar os painéis, "a coleção importa?".

A especificação (`configs/f7_painel.json`) dá, por coleção, o rótulo da rodada
de cada condição e o molde do nome do arquivo com `{st}` no lugar da
estratégia. Célula sem run vira vazia na figura, nunca um erro.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from .analysis import bootstrap_ci, per_query_scores
from .evaluate import load_qrels, load_run
from .experiment import ultima_rodada

ESTRATEGIAS = ["structural_gold", "structural_pred", "recursive_default",
               "fixed_1024_512", "fixed_512_256"]
ROTULO_EST = {"structural_gold": "estrutural\n(ouro)", "structural_pred": "estrutural\n(predito)",
              "recursive_default": "recursivo", "fixed_1024_512": "fixo\n1024/512",
              "fixed_512_256": "fixo\n512/256"}


def celulas(spec: dict, raiz_repo: Path) -> list[dict]:
    out = []
    for colecao, c in spec["colecoes"].items():
        qrels = load_qrels(raiz_repo / c["qrels"])
        base: dict[str, float] = {}
        for cond in spec["condicoes"]:
            ref = c["condicoes"].get(cond)
            if not ref:
                continue
            rotulo, _, molde = ref.partition("/")
            rodada = ultima_rodada(rotulo)
            for st in ESTRATEGIAS:
                # o molde aceita curinga: o controle carrega a fração sorteada
                # no nome (`amostra-0.3324s42`), que muda por estratégia
                achados = sorted((rodada / "runs").glob(molde.format(st=st))) if rodada else []
                achados = [p for p in achados if not p.name.endswith("__chunks.jsonl")]
                if len(achados) != 1:
                    continue
                path = achados[0]
                s = per_query_scores(qrels, load_run(path, name=f"{st}:{cond}"))
                media, lo, hi = bootstrap_ci(list(s.values()))
                if cond == spec["condicoes"][0]:
                    base[st] = media
                out.append({"colecao": colecao, "condicao": cond, "estrategia": st,
                            "n": len(s), "ndcg10": media, "ic95_inf": lo, "ic95_sup": hi,
                            "delta_rel_vs_completo": (media / base[st] - 1) if base.get(st) else None})
    return out


def fig_painel(linhas: list[dict], condicoes: list[str], rotulos: dict[str, str],
               destino: Path, rodape: str, nome_base: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    colecoes = list(dict.fromkeys(l["colecao"] for l in linhas))
    fig, axes = plt.subplots(1, len(colecoes), figsize=(5.4 * len(colecoes), 0.55 * len(condicoes) + 2.2),
                             squeeze=False, sharey=True)
    lim = max(0.05, max(abs(l["delta_rel_vs_completo"] or 0) for l in linhas))
    norma = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)
    for ax, col in zip(axes[0], colecoes):
        m = np.full((len(condicoes), len(ESTRATEGIAS)), np.nan)
        absoluto = np.full_like(m, np.nan)
        txt = [["" for _ in ESTRATEGIAS] for _ in condicoes]
        for l in (x for x in linhas if x["colecao"] == col):
            i, j = condicoes.index(l["condicao"]), ESTRATEGIAS.index(l["estrategia"])
            m[i, j] = l["delta_rel_vs_completo"] if l["delta_rel_vs_completo"] is not None else np.nan
            absoluto[i, j] = l["ndcg10"]
            txt[i][j] = f"{l['ndcg10']:.3f}"
        im = ax.imshow(m, cmap="RdBu", norm=norma, aspect="auto")
        for i in range(len(condicoes)):
            for j in range(len(ESTRATEGIAS)):
                if txt[i][j]:
                    d = m[i, j]
                    extra = "" if i == 0 or np.isnan(d) else f"\n{100 * d:+.0f}%"
                    ax.text(j, i, txt[i][j] + extra, ha="center", va="center", fontsize=7.6,
                            color="white" if not np.isnan(d) and abs(d) > lim * 0.55 else "#111")
        # melhor célula da coleção, contornada
        bi, bj = np.unravel_index(np.nanargmax(absoluto), absoluto.shape)
        ax.add_patch(plt.Rectangle((bj - 0.5, bi - 0.5), 1, 1, fill=False, ec="#111", lw=2.4))
        ax.set_xticks(range(len(ESTRATEGIAS)))
        ax.set_xticklabels([ROTULO_EST[e] for e in ESTRATEGIAS], fontsize=8)
        ax.set_yticks(range(len(condicoes)))
        ax.set_yticklabels([rotulos.get(c, c) for c in condicoes], fontsize=8.5)
        n = next(l["n"] for l in linhas if l["colecao"] == col)
        ax.set_title(f"{col}  (n = {n} consultas)", fontsize=10.5)
    cbar = fig.colorbar(im, ax=axes[0].tolist(), shrink=0.8, pad=0.015)
    cbar.set_label("Δ nDCG@10 contra o BM25 completo da mesma estratégia")
    cbar.ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    fig.suptitle("Qual receita funciona nas duas tarefas?  (número = nDCG@10; contorno = melhor da coleção)",
                 fontsize=12, y=1.02)
    fig.text(0.01, -0.03, rodape, ha="left", va="top", fontsize=7.2, color="#444")
    destino.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(destino / f"{nome_base}__painel.{ext}", bbox_inches="tight", dpi=200)
    plt.close(fig)


def main() -> None:
    import argparse

    from .experiment import Experimento

    parser = argparse.ArgumentParser(description="Painel configuracao x colecao (F7).")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--label", default="f7_painel")
    args = parser.parse_args()
    raiz_repo = Path(__file__).resolve().parent.parent
    spec = json.loads(args.spec.read_text(encoding="utf-8"))

    with Experimento(args.label, config={"spec": spec}) as exp:
        linhas = celulas(spec, raiz_repo)
        with (exp.tables_dir / "painel.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
            w.writeheader()
            w.writerows(linhas)
        for l in linhas:
            d = l["delta_rel_vs_completo"]
            exp.log(f"[{l['colecao']}] {l['condicao']:28s} {l['estrategia']:18s} "
                    f"{l['ndcg10']:.4f}" + ("" if d is None else f" ({100 * d:+.1f}%)"))
        git = exp.manifest.get("git") or {}
        rodape = (f"Rodada {exp.dir.name}  ·  corpus: 12.880 acórdãos do TCU  ·  BM25 (bm25s) e denso "
                  f"BAAI/bge-m3  ·  IC e Δ por consulta em tables/painel.csv  ·  commit "
                  f"{(git.get('commit') or '?')[:8]}")
        fig_painel(linhas, spec["condicoes"], spec.get("rotulos", {}), exp.dir / "figuras",
                   rodape, exp.dir.name)
        exp.log(f"figura em {exp.dir / 'figuras'}")


if __name__ == "__main__":
    main()
