"""F7 — Replicação: as mesmas comparações, em duas coleções de consultas.

Responde às hipóteses do pré-registro
(`docs/docsleo/branches/leo-f7-evolucao/00-preregistro.md`) a partir de um
arquivo de especificação versionado (`configs/f7_replicacao.json`), que diz
quais runs entram em cada coleção e quais pares comparar. Nada é escolhido
olhando o resultado: a especificação foi escrita junto com o pré-registro.

Três tabelas, três figuras:

1. **`replicacao.csv` / `forest`** — para cada comparação (A contra B), o
   efeito em cada coleção: Δ absoluto e relativo, IC 95% por bootstrap pareado,
   p do t pareado e p com Bonferroni *dentro da coleção*. A figura é um forest
   plot: uma linha por comparação, um ponto por coleção. Se os dois pontos
   caem do mesmo lado do zero com ICs que não o cruzam, o efeito replicou.
2. **`estratos.csv` / `estratos`** — as mesmas comparações recortadas pelo
   campo `source` das consultas. No JUÁ-Juris esse campo é a seção onde mora a
   resposta (`src/jua.py`), o que testa H4: o recorte prejudica quando a
   resposta está no relatório?
3. **`equivalencia.csv` / `equivalencia`** — teste de equivalência (TOST)
   entre as estratégias de chunking, com margem ±δ de nDCG@10. "Não deu
   diferença significativa" não prova igualdade; o TOST prova, quando o IC 90%
   da diferença cabe inteiro dentro de ±δ (Schuirmann 1987; Lakens 2017).

Toda figura carrega no rodapé a rodada, o commit e as coleções, como as do
`src.plots`.
"""

from __future__ import annotations

import csv
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy import stats

from .analysis import per_query_scores
from .evaluate import load_qrels, load_run
from .experiment import EXPERIMENTS_DIR, ultima_rodada

N_BOOT = 10_000
SEED = 42


# --- estatística (pura, testada) ---------------------------------------------

def efeito_pareado(a: dict[str, float], b: dict[str, float], qids: list[str]) -> dict:
    """Δ = A − B consulta a consulta, com IC 95% por bootstrap e t pareado."""
    x = np.array([a[q] for q in qids])
    y = np.array([b[q] for q in qids])
    d = x - y
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, d.size, size=(N_BOOT, d.size))
    medias_d = d[idx].mean(axis=1)
    lo, hi = np.percentile(medias_d, [2.5, 97.5])
    base = y.mean()
    p = float(stats.ttest_rel(x, y).pvalue) if d.size > 1 and d.std() > 0 else 1.0
    return {
        "n": int(d.size),
        "media_a": float(x.mean()),
        "media_b": float(base),
        "delta": float(d.mean()),
        "delta_rel": float(d.mean() / base) if base else float("nan"),
        "ic95_inf": float(lo),
        "ic95_sup": float(hi),
        "ic95_rel_inf": float(lo / base) if base else float("nan"),
        "ic95_rel_sup": float(hi / base) if base else float("nan"),
        "p": p,
        "vitorias": int((d > 0).sum()),
        "empates": int((d == 0).sum()),
        "derrotas": int((d < 0).sum()),
    }


def tost(a: dict[str, float], b: dict[str, float], qids: list[str], margem: float) -> dict:
    """Teste de equivalência por dois testes t unilaterais (TOST), pareado.

    H0: |μ_A − μ_B| ≥ margem. Rejeitar H0 (p < 0,05) é afirmar equivalência
    prática. O critério equivalente, e o que vai para a figura, é o IC 90% da
    diferença caber inteiro dentro de (−margem, +margem).
    """
    d = np.array([a[q] - b[q] for q in qids])
    n = d.size
    media = float(d.mean())
    ep = float(d.std(ddof=1) / np.sqrt(n)) if n > 1 else float("inf")
    if ep == 0:
        p = 0.0 if abs(media) < margem else 1.0
        return {"n": n, "delta": media, "ic90_inf": media, "ic90_sup": media,
                "margem": margem, "p_tost": p, "equivalente": p < 0.05}
    gl = n - 1
    p_inf = 1 - stats.t.cdf((media + margem) / ep, gl)   # H0: μ ≤ −margem
    p_sup = stats.t.cdf((media - margem) / ep, gl)       # H0: μ ≥ +margem
    t90 = stats.t.ppf(0.95, gl)
    p_tost = float(max(p_inf, p_sup))
    return {
        "n": n,
        "delta": media,
        "ic90_inf": media - t90 * ep,
        "ic90_sup": media + t90 * ep,
        "margem": margem,
        "p_tost": p_tost,
        "equivalente": p_tost < 0.05,
    }


def bonferroni(ps: list[float]) -> list[float]:
    m = len(ps)
    return [min(1.0, p * m) for p in ps]


# --- leitura da especificação ------------------------------------------------

def resolver(ref: str, raiz: Path = EXPERIMENTS_DIR) -> Path:
    """`rotulo/arquivo.trec` -> caminho, pela rodada mais recente com o rótulo.

    O rótulo é casado EXATAMENTE (`ultima_rodada`), então a especificação
    sobrevive a uma reexecução: a rodada nova, com outro carimbo de data, é
    encontrada sem editar o JSON.
    """
    rotulo, _, arquivo = ref.partition("/")
    rodada = ultima_rodada(rotulo, raiz=raiz)
    if rodada is None:
        raise SystemExit(f"nenhuma rodada com runs para o rotulo {rotulo!r}")
    path = rodada / "runs" / arquivo
    if not path.is_file():
        raise SystemExit(f"{path} nao existe")
    return path


def carregar_colecao(spec: dict, raiz_repo: Path) -> tuple[dict, dict[str, dict], dict[str, str]]:
    """(scores por condição, fonte por consulta) de uma coleção."""
    qrels = load_qrels(raiz_repo / spec["qrels"])
    fonte: dict[str, str] = {}
    with (raiz_repo / spec["queries"]).open(encoding="utf-8") as f:
        for linha in f:
            r = json.loads(linha)
            fonte[r["query_id"]] = r.get("source", "")
    scores, caminhos = {}, {}
    for nome, ref in spec["runs"].items():
        # Condição sem run vira ausência, com aviso, e não aborta a análise:
        # nem toda condição existe em toda coleção (o reranker não roda na
        # amostra natural, por exemplo), e as comparações que a usam são puladas.
        try:
            path = resolver(ref)
        except SystemExit as e:
            print(f"  [aviso] {nome}: {e}", flush=True)
            continue
        scores[nome] = per_query_scores(qrels, load_run(path, name=nome))
        caminhos[nome] = str(path)
    return scores, fonte, caminhos


# --- figuras -----------------------------------------------------------------

CORES_COLECAO = ["#1b4965", "#e09f3e", "#6a994e", "#bc4749"]
NOME_SECAO = {"fundamentacao": "fundamentação", "relatorio": "relatório", "dispositivo": "dispositivo",
              "ementa": "ementa", "nao_localizado": "não localizada"}


def _rodape(fig, texto: str) -> None:
    fig.text(0.01, -0.02, texto, ha="left", va="top", fontsize=7.2, color="#444")


def fig_forest(linhas: list[dict], colecoes: list[str], destino: Path, rodape: str,
               titulo: str = "", nome: str = "forest") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    comps = list(dict.fromkeys(l["comparacao"] for l in linhas))
    # cada coleção ganha sua "faixa" dentro da linha da comparação: com 3 ou 4
    # coleções, rótulos de 0,1 unidade de distância se sobreporiam
    altura_linha = 0.42 + 0.22 * len(colecoes)
    fig, ax = plt.subplots(figsize=(10.5, altura_linha * len(comps) + 1.8))
    passo = (0.32 if len(colecoes) <= 2 else 0.66) / max(len(colecoes) - 1, 1)
    for ci, col in enumerate(colecoes):
        for yi, comp in enumerate(comps):
            l = next((x for x in linhas if x["comparacao"] == comp and x["colecao"] == col), None)
            if not l:
                continue
            y = len(comps) - 1 - yi + (ci - (len(colecoes) - 1) / 2) * passo
            v, lo, hi = (100 * l[k] for k in ("delta_rel", "ic95_rel_inf", "ic95_rel_sup"))
            sig = l["p_bonf"] < 0.05
            ax.errorbar(v, y, xerr=[[v - lo], [hi - v]], fmt="o", ms=6.5,
                        color=CORES_COLECAO[ci], mfc=CORES_COLECAO[ci] if sig else "white",
                        capsize=3, lw=1.6, label=col if yi == 0 else None)
            # Coluna fixa à direita do eixo: o rótulo nunca cruza a linha do
            # zero nem a barra da outra coleção.
            ax.text(1.01, y, f"{v:+.1f}%  p={l['p_bonf']:.2g}",
                    transform=ax.get_yaxis_transform(), va="center", fontsize=7.8,
                    color=CORES_COLECAO[ci], fontweight="bold" if sig else "normal")
    ax.axvline(0, color="#555", lw=1, ls="--")
    ax.set_yticks(range(len(comps)))
    ax.set_yticklabels(list(reversed(comps)), fontsize=9)
    ax.set_xlabel("Δ nDCG@10 relativo a B (%) — IC 95% por bootstrap pareado de consultas")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.25)
    ax.set_ylim(-0.6, len(comps) - 0.4)
    from matplotlib.lines import Line2D
    # legenda fixa: a cor identifica a coleção; o preenchimento é a significância
    # e não pode depender de qual comparação calhou de vir primeiro
    alcas = [Line2D([], [], marker="o", ls="", ms=7, color=CORES_COLECAO[i], label=c)
             for i, c in enumerate(colecoes)]
    ax.legend(handles=alcas, title="marcador cheio = p < 0,05 com Bonferroni dentro da coleção",
              loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=len(colecoes),
              fontsize=9, title_fontsize=8.5, frameon=False)
    # título logo acima da legenda (que fica fora do eixo): em figuras altas, um y
    # fixo deixava um vão grande no topo
    fig.suptitle(titulo or "O efeito replica numa segunda coleção de consultas?", fontsize=12.5,
                 y=1.0 + 0.55 / fig.get_size_inches()[1])
    _rodape(fig, rodape)
    _salvar(fig, destino, nome)


def fig_estratos(linhas: list[dict], destino: Path, rodape: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    comps = list(dict.fromkeys(l["comparacao"] for l in linhas))
    # Ordem do gênero (onde a tese costuma estar primeiro) e só estratos com
    # n suficiente para um IC legível: uma barra com n = 8 só faz ruído.
    ordem = ["fundamentacao", "dispositivo", "relatorio", "ementa", "nao_localizado"]

    def chave(estrato: str) -> int:
        nome = estrato.replace("resposta em ", "")
        return ordem.index(nome) if nome in ordem else len(ordem)

    linhas = [l for l in linhas if l["n"] >= 30]
    estratos = sorted({l["estrato"] for l in linhas}, key=chave)
    n_por_estrato = {l["estrato"]: l["n"] for l in linhas}
    fig, axes = plt.subplots(1, len(comps), figsize=(3.9 * len(comps) + 1.6, 0.62 * len(estratos) + 1.6),
                             sharey=True, squeeze=False)
    for ax, comp in zip(axes[0], comps):
        for l in (x for x in linhas if x["comparacao"] == comp):
            i = len(estratos) - 1 - estratos.index(l["estrato"])
            v, lo, hi = (100 * l[k] for k in ("delta_rel", "ic95_rel_inf", "ic95_rel_sup"))
            cor = "#6a994e" if lo > 0 else "#bc4749" if hi < 0 else "#9a9a9a"
            ax.barh(i, v, color=cor, alpha=0.85, height=0.6)
            ax.errorbar(v, i, xerr=[[v - lo], [hi - v]], fmt="none", ecolor="#222", capsize=3)
            ax.annotate(f"{v:+.0f}%", (v, i), xytext=(0, 9), textcoords="offset points",
                        ha="center", fontsize=8, color="#222")
        ax.axvline(0, color="#555", lw=1)
        ax.set_title(comp, fontsize=9.5)
        ax.set_xlabel("Δ nDCG@10 (%), IC 95%", fontsize=8.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", alpha=0.25)
    axes[0][0].set_yticks(range(len(estratos)))
    axes[0][0].set_yticklabels(
        [f"resposta: {NOME_SECAO.get(e.replace('resposta em ', ''), e)}\n(n = {n_por_estrato[e]})"
         for e in reversed(estratos)], fontsize=8.5)
    fig.suptitle("Onde mora a resposta decide o sinal do efeito?\n"
                 "verde: IC 95% acima de zero · vermelho: abaixo · cinza: inclui zero",
                 fontsize=11.5, y=1.08)
    _rodape(fig, rodape)
    _salvar(fig, destino, "estratos")


def fig_equivalencia(linhas: list[dict], colecoes: list[str], destino: Path, rodape: str,
                     titulo: str = "", nome: str = "estrategias") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pares = list(dict.fromkeys(l["par"] for l in linhas))
    margem = linhas[0]["margem"]
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(pares) + 1.8))
    ax.axvspan(-margem, margem, color="#6a994e", alpha=0.12, lw=0)
    passo = 0.3 / max(len(colecoes) - 1, 1)
    for ci, col in enumerate(colecoes):
        for yi, par in enumerate(pares):
            l = next((x for x in linhas if x["par"] == par and x["colecao"] == col), None)
            if not l:
                continue
            y = len(pares) - 1 - yi + (ci - (len(colecoes) - 1) / 2) * passo
            ax.errorbar(l["delta"], y, xerr=[[l["delta"] - l["ic90_inf"]],
                                              [l["ic90_sup"] - l["delta"]]],
                        fmt="s" if l["equivalente"] else "o", ms=5.5, capsize=2.5,
                        color=CORES_COLECAO[ci],
                        mfc=CORES_COLECAO[ci] if l["equivalente"] else "white",
                        label=col if yi == 0 else None)
    ax.axvline(0, color="#555", lw=0.8)
    ax.set_yticks(range(len(pares)))
    ax.set_yticklabels(list(reversed(pares)), fontsize=8.5)
    ax.set_xlabel(f"Δ nDCG@10 (A − B), IC 90% — faixa verde: equivalência prática (±{margem})")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(-0.6, len(pares) - 0.4)
    from matplotlib.lines import Line2D
    alcas = [Line2D([], [], marker="s", ls="", ms=7, color=CORES_COLECAO[i], label=c)
             for i, c in enumerate(colecoes)]
    ax.legend(handles=alcas, title="quadrado cheio = equivalente pelo TOST (p < 0,05)", fontsize=9,
              title_fontsize=8.5, frameon=False, loc="lower center",
              bbox_to_anchor=(0.5, 1.0), ncol=len(colecoes))
    fig.suptitle(titulo or "As estratégias de chunking são equivalentes? (teste de equivalência, TOST)",
                 fontsize=12.5, y=1.04)
    _rodape(fig, rodape)
    _salvar(fig, destino, f"equivalencia_{nome}")


def _salvar(fig, destino: Path, nome: str) -> None:
    import matplotlib.pyplot as plt

    destino.mkdir(parents=True, exist_ok=True)
    base = f"{destino.parent.name}__{nome}"
    for ext in ("pdf", "png"):
        fig.savefig(destino / f"{base}.{ext}", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  {base}.pdf / .png")


# --- CLI ---------------------------------------------------------------------

def _gravar(path: Path, linhas: list[dict]) -> None:
    if not linhas:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)


def main() -> None:
    import argparse

    from .experiment import Experimento

    parser = argparse.ArgumentParser(description="Replicacao das comparacoes entre colecoes.")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--label", default="f7_replicacao")
    args = parser.parse_args()

    raiz_repo = Path(__file__).resolve().parent.parent
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    colecoes = list(spec["colecoes"])

    with Experimento(args.label, config={"spec": spec}) as exp:
        dados = {}
        for nome, cspec in spec["colecoes"].items():
            scores, fonte, caminhos = carregar_colecao(cspec, raiz_repo)
            dados[nome] = (scores, fonte)
            exp.registrar(nome, {"runs": caminhos})
            exp.log(f"{nome}: {len(fonte)} consultas, {len(scores)} condicoes")

        linhas, estratos = [], []
        for nome, (scores, fonte) in dados.items():
            qids = sorted(fonte)
            bloco = []
            for a, b, rotulo in spec["comparacoes"]:
                if a not in scores or b not in scores:
                    continue
                e = efeito_pareado(scores[a], scores[b], qids)
                bloco.append({"colecao": nome, "comparacao": rotulo, "a": a, "b": b, **e})
                for estrato in sorted(set(fonte.values())):
                    qs = [q for q in qids if fonte[q] == estrato]
                    if len(qs) >= 5:
                        estratos.append({"colecao": nome, "comparacao": rotulo,
                                         "estrato": estrato,
                                         **efeito_pareado(scores[a], scores[b], qs)})
            for l, pb in zip(bloco, bonferroni([l["p"] for l in bloco])):
                l["p_bonf"] = pb
            linhas += bloco

        equiv = []
        conjuntos = spec.get("equivalencia") or []
        if isinstance(conjuntos, dict):  # formato antigo: um conjunto só
            conjuntos = [{"nome": "estrategias", **conjuntos}]
        for eq in conjuntos:
            rotulos = eq.get("rotulos", {})
            for nome, (scores, fonte) in dados.items():
                qids = sorted(fonte)
                for a, b in combinations(eq["condicoes"], 2):
                    if a in scores and b in scores:
                        equiv.append({"conjunto": eq["nome"], "colecao": nome,
                                      "par": f"{rotulos.get(a, a)} × {rotulos.get(b, b)}",
                                      "a": a, "b": b,
                                      **tost(scores[a], scores[b], qids, eq["margem"])})

        _gravar(exp.tables_dir / "replicacao.csv", linhas)
        _gravar(exp.tables_dir / "estratos.csv", estratos)
        _gravar(exp.tables_dir / "equivalencia.csv", equiv)
        for l in linhas:
            exp.log(f"[{l['colecao']}] {l['comparacao']}: {l['media_a']:.4f} vs {l['media_b']:.4f} "
                    f"({100 * l['delta_rel']:+.1f}%, p_bonf={l['p_bonf']:.2g}, "
                    f"V/E/D={l['vitorias']}/{l['empates']}/{l['derrotas']})")

        git = exp.manifest.get("git") or {}
        rodape = (f"Rodada {exp.dir.name}  ·  corpus: 12.880 acórdãos do TCU  ·  coleções: "
                  + "; ".join(f"{c} ({len(dados[c][1])} consultas)" for c in colecoes)
                  + f"  ·  commit {(git.get('commit') or '?')[:8]}")
        destino = exp.dir / "figuras"
        blocos = spec.get("blocos_forest")
        if blocos:
            for b in blocos:
                ls = [l for l in linhas if l["comparacao"] in b["comparacoes"]]
                if ls:
                    fig_forest(ls, [c for c in colecoes if any(l["colecao"] == c for l in ls)],
                               destino, rodape, b["titulo"], f"forest_{b['nome']}")
        else:
            fig_forest(linhas, colecoes, destino, rodape)
        estr_jua = [l for l in estratos if l["colecao"] == spec.get("colecao_estratos", colecoes[-1])
                    and l["comparacao"] in spec.get("comparacoes_estratos", [])]
        if estr_jua:
            fig_estratos(estr_jua, destino, rodape)
        for eq in conjuntos:
            linhas_eq = [l for l in equiv if l["conjunto"] == eq["nome"]]
            if linhas_eq:
                fig_equivalencia(linhas_eq, [c for c in colecoes if any(l["colecao"] == c for l in linhas_eq)],
                                 destino, rodape, eq.get("titulo", ""), eq["nome"])


if __name__ == "__main__":
    main()
