"""F7 — O mecanismo, consulta a consulta: o recorte dói onde a consulta "é" a ementa?

A explicação do [03](../../docs/docsleo/branches/leo-f7-evolucao/03-fronteira-e-criterio-toca.md)
é que o recorte da F6 joga fora a ementa junto com o chunk de fronteira, e que
isso dói quando a consulta se parece com a ementa. Se for isso, o dano deve
**crescer com a sobreposição lexical entre a consulta e a ementa do acórdão
certo**, e o critério `toca` deve neutralizá-lo justamente onde ele é maior.

Medida: fração dos termos da consulta (sem acento, sem caixa, ≥ 3 letras,
sem stopwords) que aparecem na ementa do acórdão relevante. As consultas são
divididas em quartis dessa medida, e o efeito de cada recorte é calculado por
quartil, com IC 95% por bootstrap.

Saídas: `tables/mecanismo.csv` e a figura `mecanismo`.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import numpy as np

from .analysis import per_query_scores
from .evaluate import load_qrels, load_run
from .experiment import ultima_rodada
from .jua import dobrar

STOP = set("""
a o as os um uma uns umas de do da dos das no na nos nas em por para pelo pela pelos pelas
com sem sob sobre entre ate que se ao aos e ou nao mais menos como quando onde qual quais
seu sua seus suas ser ter ha sao foi pode deve devem tal tais este esta estes estas esse essa
""".split())
_TOKEN = re.compile(r"[a-z0-9]{3,}")


def termos(texto: str) -> set[str]:
    return {t for t in _TOKEN.findall(dobrar(texto)) if t not in STOP}


def cobertura(consulta: str, ementa: str) -> float:
    """Fração dos termos da consulta presentes na ementa (0 a 1)."""
    q = termos(consulta)
    return len(q & termos(ementa)) / len(q) if q else 0.0


def main() -> None:
    import argparse

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .analysis import bootstrap_ci
    from .experiment import Experimento
    from .ingest import INTERIM_DIR

    p = argparse.ArgumentParser(description="Efeito do recorte por quartil de sobreposicao consulta x ementa.")
    p.add_argument("--estrategia", default="fixed_512_256")
    p.add_argument("--label", default="f7_mecanismo")
    args = p.parse_args()
    st = args.estrategia

    colecoes = {
        "JUÁ difícil (1.567)": ("jua/qrels_test.trec", "jua/queries_test.jsonl", "jua_"),
        "JUÁ natural (6.000)": ("jua/qrels_train_amostra.trec", "jua/queries_train_amostra.jsonl", "juanat_"),
    }
    with Experimento(args.label, config={"estrategia": st}) as exp:
        rel_docs: dict[str, str] = {}
        textos: dict[str, str] = {}
        for qrels, queries, _ in colecoes.values():
            with (INTERIM_DIR / qrels).open(encoding="utf-8") as f:
                for l in f:
                    q, _z, d, _s = l.split()
                    rel_docs[q] = d
            with (INTERIM_DIR / queries).open(encoding="utf-8") as f:
                for l in f:
                    r = json.loads(l)
                    textos[r["query_id"]] = r["text"]
        alvo = set(rel_docs.values())
        ementa: dict[str, str] = {}
        with (INTERIM_DIR / "corpus_docs.jsonl").open(encoding="utf-8") as f:
            for l in f:
                r = json.loads(l)
                if r["doc_id"] in alvo:
                    s = next((s for s in r["gold_spans"] if s["section"] == "ementa"), None)
                    ementa[r["doc_id"]] = r["text"][s["start"]:s["end"]] if s else ""

        linhas = []
        fig, axes = plt.subplots(1, len(colecoes), figsize=(6.2 * len(colecoes), 3.8), squeeze=False,
                                 sharey=False)
        for ax, (nome, (qrels_p, _qp, pre)) in zip(axes[0], colecoes.items()):
            qrels = load_qrels(INTERIM_DIR / qrels_p)
            run = lambda rot, arq: per_query_scores(  # noqa: E731
                qrels, load_run(ultima_rodada(pre + rot) / "runs" / arq, name=rot))
            base = run("bm25", f"{st}__bm25.trec")
            maioria = run("bm25_sec_sem_relatorio", f"{st}__bm25__sec-sem_relatorio.trec")
            toca = run("bm25_sec_sem_relatorio_toca", f"{st}__bm25__sec-sem_relatorio__crit-toca.trec")
            qids = sorted(base)
            cob = np.array([cobertura(textos[q], ementa.get(rel_docs[q], "")) for q in qids])
            cortes = np.quantile(cob, [0.25, 0.5, 0.75])
            quartil = np.searchsorted(cortes, cob, side="right")
            for k in range(4):
                qs = [q for q, qq in zip(qids, quartil) if qq == k]
                b = np.array([base[q] for q in qs])
                for crit, sc in (("maioria (F6)", maioria), ("toca", toca)):
                    d = np.array([sc[q] for q in qs]) - b
                    m, lo, hi = bootstrap_ci(list(d))
                    linhas.append({"colecao": nome, "quartil": k + 1, "n": len(qs),
                                   "cobertura_min": float(cob[quartil == k].min()),
                                   "cobertura_max": float(cob[quartil == k].max()),
                                   "criterio": crit, "ndcg_base": float(b.mean()),
                                   "delta": m, "ic95_inf": lo, "ic95_sup": hi,
                                   "delta_rel": m / b.mean() if b.mean() else float("nan")})
            for j, (crit, cor) in enumerate((("maioria (F6)", "#bc4749"), ("toca", "#1b4965"))):
                ls = [l for l in linhas if l["colecao"] == nome and l["criterio"] == crit]
                x = np.arange(4) + (j - 0.5) * 0.36
                v = [100 * l["delta_rel"] for l in ls]
                err = [[100 * (l["delta"] - l["ic95_inf"]) / l["ndcg_base"] for l in ls],
                       [100 * (l["ic95_sup"] - l["delta"]) / l["ndcg_base"] for l in ls]]
                ax.bar(x, v, width=0.34, color=cor, alpha=0.88, label=crit)
                ax.errorbar(x, v, yerr=err, fmt="none", ecolor="#222", capsize=2.5, lw=1)
            ax.axhline(0, color="#555", lw=1)
            rot = [f"Q{k + 1}\n{l['cobertura_min']:.0%}–{l['cobertura_max']:.0%}"
                   for k, l in enumerate(x for x in linhas if x["colecao"] == nome and x["criterio"] == "toca")]
            ax.set_xticks(range(4))
            ax.set_xticklabels(rot, fontsize=8)
            ax.set_title(nome, fontsize=10)
            ax.set_xlabel("quartil da fração dos termos da consulta que estão na ementa do acórdão certo",
                          fontsize=8)
            ax.spines[["top", "right"]].set_visible(False)
            ax.grid(axis="y", alpha=0.25)
        axes[0][0].set_ylabel(f"Δ nDCG@10 contra o completo (%), IC 95%\n({st}, BM25)")
        axes[0][0].legend(frameon=False, fontsize=9)
        fig.suptitle("O recorte da F6 dói onde a consulta “é” a ementa — e o critério “toca” conserta ali",
                     fontsize=12, y=1.03)
        git = exp.manifest.get("git") or {}
        fig.text(0.01, -0.08, f"Rodada {exp.dir.name}  ·  corpus: 12.880 acórdãos do TCU  ·  commit "
                 f"{(git.get('commit') or '?')[:8]}", fontsize=7, color="#444")
        destino = exp.dir / "figuras"
        destino.mkdir(parents=True, exist_ok=True)
        for ext in ("pdf", "png"):
            fig.savefig(destino / f"{exp.dir.name}__mecanismo.{ext}", bbox_inches="tight", dpi=200)
        plt.close(fig)
        with (exp.tables_dir / "mecanismo.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
            w.writeheader()
            w.writerows(linhas)
        for l in linhas:
            exp.log(f"[{l['colecao']}] Q{l['quartil']} ({l['cobertura_min']:.2f}-{l['cobertura_max']:.2f}, "
                    f"n={l['n']}) {l['criterio']:13s} {100 * l['delta_rel']:+.1f}% "
                    f"[{l['ic95_inf']:+.4f}, {l['ic95_sup']:+.4f}]")


if __name__ == "__main__":
    main()
