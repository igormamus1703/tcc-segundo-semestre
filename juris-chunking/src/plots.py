"""Figuras do artigo, geradas a partir das tabelas de uma rodada.

Só consome `results/experiments/<rodada>/tables/*.csv` e o `manifest.json` da
rodada — não recalcula nada. Cada figura sai em PDF (para o LaTeX) e PNG (para
o pôster e para olhar rápido).

**Toda figura é autocontida.** O rodapé carrega rodada, data, corpus,
retriever/modelo e commit, lidos do manifesto. Uma imagem copiada para o
artigo, para o pôster ou para uma mensagem continua dizendo de onde veio — sem
isso, três semanas depois ninguém sabe se aquele gráfico é do corpus de 12.880
ou do de 113.827, do BM25 ou do denso, de antes ou depois de uma correção.

Uso:
    python -m src.plots                        # usa a rodada mais recente
    python -m src.plots --experiment results/experiments/20260906-0515_bm25
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
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
ROTULO_RETRIEVER = {"bm25": "BM25 (bm25s)"}

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# --- contexto da rodada (o que vai estampado em toda figura) ------------------

def contexto_da_rodada(exp_dir: Path) -> dict:
    """Lê manifesto + caracterização do corpus e devolve o que o rodapé precisa.

    Tolerante a manifestos antigos (sem `corpus`) e a rodadas sem `git`: um
    campo ausente vira "?" no rodapé, nunca uma exceção — a figura tem que sair.
    """
    m: dict = {}
    mf = exp_dir / "manifest.json"
    if mf.is_file():
        m = json.loads(mf.read_text(encoding="utf-8"))
    cfg = m.get("config", {}) or {}

    # corpus: do manifesto se houver, senão da caracterização versionada
    corpus = m.get("corpus") or {}
    if not corpus:
        eda = REPO_ROOT / "results" / "corpus" / "eda_stats.json"
        if eda.is_file():
            e = json.loads(eda.read_text(encoding="utf-8"))
            corpus = {"n_docs": e.get("n_docs"),
                      "mediana_tokens_doc": (e.get("tokens_por_doc") or {}).get("mediana")}
    n_qrels = corpus.get("n_qrel_pares")
    if n_qrels is None:
        qrels = REPO_ROOT / "juris-chunking" / "data" / "interim" / "qrels.trec"
        if qrels.is_file():
            with qrels.open("rb") as f:
                n_qrels = sum(1 for _ in f)

    # retriever(s) e modelo denso
    retrievers = cfg.get("retrievers") or []
    partes = []
    for r in retrievers:
        if r == "dense":
            md = cfg.get("modelo_denso") or {}
            partes.append(
                f"denso {md.get('hf_id', cfg.get('embedder', '?'))}"
                f" ({md.get('dtype', '?')}, janela {md.get('max_seq_length', '?')},"
                f" batch {md.get('batch_size', '?')})"
            )
        else:
            partes.append(ROTULO_RETRIEVER.get(r, r))
    retriever_txt = " + ".join(partes) if partes else "?"

    inicio = m.get("inicio", "")
    try:
        data_txt = datetime.fromisoformat(inicio).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        data_txt = inicio or "?"

    git = m.get("git") or {}
    commit = (git.get("commit") or "?")[:8]
    if git.get("sujo"):
        commit += " (árvore suja)"

    hw = m.get("hardware") or {}
    return {
        "rodada": exp_dir.name,
        "data": data_txt,
        "n_docs": corpus.get("n_docs"),
        "mediana_tokens": corpus.get("mediana_tokens_doc"),
        "n_queries": cfg.get("n_queries"),
        "n_qrels": n_qrels,
        "retriever": retriever_txt,
        "agregacao": cfg.get("agregacao", "?"),
        "top_chunks": cfg.get("top_chunks", "?"),
        "top_docs": cfg.get("top_docs", "?"),
        "commit": commit,
        "branch": git.get("branch", "?"),
        "hardware": hw.get("gpu") or hw.get("cpu") or "?",
        "retroativo": bool(m.get("reconstruido_retroativamente")),
    }


def _fmt(n) -> str:
    return f"{n:,}".replace(",", ".") if isinstance(n, int) else str(n if n is not None else "?")


def _rodape(fig, ctx: dict, extra: str = "", y0: float = -0.02) -> None:
    """Estampa o contexto da rodada no pé da figura.

    `y0` é a altura da primeira linha, em fração da figura. Figuras com
    rótulos rotacionados no eixo X (`fig_principal`) empurram o conteúdo para
    baixo e precisam de um `y0` mais negativo, senão o rodapé cai por cima dos
    rótulos — o `bbox_inches="tight"` inclui tudo, mas não separa nada.
    """
    l1 = (f"Rodada {ctx['rodada']}  ·  {ctx['data']}  ·  "
          f"corpus: {_fmt(ctx['n_docs'])} acórdãos do TCU (2003–2023), "
          f"{_fmt(ctx['n_queries'])} consultas JurisTCU, {_fmt(ctx['n_qrels'])} qrels")
    l2 = (f"Retriever: {ctx['retriever']}  ·  agregação {ctx['agregacao']}  ·  "
          f"top-{_fmt(ctx['top_chunks'])} chunks → top-{_fmt(ctx['top_docs'])} docs  ·  "
          f"commit {ctx['commit']} ({ctx['branch']})")
    if extra:
        l2 += f"  ·  {extra}"
    if ctx["retroativo"]:
        l2 += "  ·  manifesto reconstruído retroativamente"
    fig.text(0.01, y0, l1, ha="left", va="top", fontsize=7.2, color="#444")
    fig.text(0.01, y0 - 0.035, l2, ha="left", va="top", fontsize=7.2, color="#444")


def _titulo(fig, texto: str, ctx: dict, y: float = 1.02) -> None:
    fig.suptitle(f"{texto}\n{ctx['retriever']}", y=y, fontsize=12.5, linespacing=1.4)


# --- utilidades ----------------------------------------------------------------

ROTULO_VARIANTE = {
    "sem_relatorio": "sem relatório",
    "completo": "índice completo",
}


def partes_do_run(nome: str) -> tuple[str, str]:
    """`<rodada>/`?`estrategia__retriever[__variantes]` -> (estrategia, condição).

    O prefixo de rodada aparece quando `src.evaluate --incluir` desambigua runs
    de mesmo nome vindos de rodadas diferentes; sem descartá-lo aqui, o rótulo
    da figura viraria o caminho inteiro. O `--runs` usa `--` em vez de `/`,
    porque a barra não vale em nome de arquivo.

    A segunda componente é a **condição experimental**, não só o retriever: as
    variantes da F6 (`__sec-…`, `__peso-…`, `__amostra-…`) entram nela. Todas
    as figuras agrupam por essa componente, então incluí-la aqui é o que faz o
    BM25 do índice completo e o BM25 sem o relatório aparecerem como barras
    distintas. Sem isso, as duas condições caem na mesma barra e uma delas
    some do gráfico sem nenhum erro — a figura fica *errada*, não incompleta.
    """
    sem_rodada = nome.split("/")[-1]
    # O prefixo `<rodada>--` do `--runs` só existe quando dois runs escolhidos
    # tinham o MESMO nome de arquivo. Descartá-lo colapsaria de volta as duas
    # condições que ele foi criado para separar — o mesmo bug, uma camada
    # acima. Então ele entra no rótulo, sem o carimbo de data, que não
    # distingue nada para quem lê a figura.
    discriminador = ""
    if "--" in sem_rodada and "__" in sem_rodada.split("--")[-1]:
        rodada, _, sem_rodada = sem_rodada.rpartition("--")
        _ts, _, resto = rodada.partition("_")
        discriminador = " · " + (resto or rodada).replace("_", " ")
    partes = sem_rodada.split("__")
    if len(partes) < 2:
        return partes[0], discriminador.removeprefix(" · ")
    condicao = partes[1] + discriminador
    for p in partes[2:]:
        if p.startswith("sec-"):
            v = p[len("sec-"):]
            condicao += f" · {ROTULO_VARIANTE.get(v, v)}"
        elif p.startswith("peso-"):
            condicao += f" · peso {p[len('peso-'):]}"
        elif p.startswith("amostra-"):
            condicao += " · amostra aleatória"
        else:
            condicao += f" · {p}"
    return partes[0], condicao


ROTULO_CURTO_RETRIEVER = {"bm25": "BM25"}

# Com sete condicoes numa figura, alternar so entre dois estilos faria duas
# barras diferentes ficarem visualmente identicas na legenda.
_HACHURAS = ("", "//", "..", "xx", "\\\\", "++", "oo")
_ALPHAS = (0.95, 0.65, 0.85, 0.55, 0.9, 0.6, 0.8)


def rotulo_do_run(nome: str, com_retriever: bool = False) -> str:
    """Rótulo da estratégia, opcionalmente com o retriever.

    Numa figura que cruza retrievers (`--incluir`), o rótulo precisa dizer
    qual é qual: sem isso, "recursivo" apareceria duas vezes nos eixos, uma
    para o BM25 e outra para o denso, e a matriz de p-valores viraria um
    quebra-cabeça.
    """
    est, ret = partes_do_run(nome)
    base = ROTULOS.get(est, est)
    if not com_retriever or not ret:
        return base
    curto = ROTULO_CURTO_RETRIEVER.get(ret, ret.replace("dense-", "denso "))
    return f"{base}\n{curto}"


def mais_de_um_retriever(nomes: list[str]) -> bool:
    return len({partes_do_run(n)[1] for n in nomes}) > 1


def ler_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _salvar(fig, destino: Path, ctx: dict, nome: str) -> None:
    """`<rodada>__<nome>.{pdf,png}` — o arquivo nunca perde a origem, mesmo
    copiado sozinho para outra pasta."""
    destino.mkdir(parents=True, exist_ok=True)
    base = f"{ctx['rodada']}__{nome}"
    for ext in ("pdf", "png"):
        fig.savefig(destino / f"{base}.{ext}", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  {base}.pdf / .png")


def _estilo(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.7)
    ax.set_axisbelow(True)


# --- figuras ---------------------------------------------------------------------

def fig_principal(rows: list[dict], destino: Path, ctx: dict) -> None:
    """Métricas por estratégia, agrupadas por retriever."""
    if not rows:
        return
    metricas = ["ndcg@10", "mrr@10", "map@10", "recall@100"]
    # A condição vem de `partes_do_run`, não da coluna `retriever` do CSV: a
    # coluna diz só "bm25", e o BM25 do índice completo e o BM25 sem o
    # relatório colapsariam na mesma barra, escondendo justamente o efeito que
    # a figura existe para mostrar.
    condicao = {r["run"]: partes_do_run(r["run"]) for r in rows}
    retrievers = sorted({c for _e, c in condicao.values()})
    estrategias = sorted({e for e, _c in condicao.values()})

    fig, axes = plt.subplots(1, len(metricas), figsize=(4.2 * len(metricas), 4.4))
    largura = 0.8 / max(len(retrievers), 1)
    for ax, met in zip(axes, metricas):
        for i, ret in enumerate(retrievers):
            for j, est in enumerate(estrategias):
                achado = [r for r in rows if condicao[r["run"]] == (est, ret)]
                if not achado:
                    continue
                v = float(achado[0][met])
                x = j + i * largura
                ax.bar(x, v, largura * 0.9, color=CORES.get(est, "#888"),
                       alpha=_ALPHAS[i % len(_ALPHAS)], hatch=_HACHURAS[i % len(_HACHURAS)],
                       edgecolor="white", linewidth=0.8)
                ax.text(x, v, f"{v:.3f}", ha="center", va="bottom", fontsize=6.5, color="#333")
        ax.set_xticks([j + largura * (len(retrievers) - 1) / 2 for j in range(len(estrategias))])
        ax.set_xticklabels([ROTULOS.get(e, e) for e in estrategias], rotation=35, ha="right")
        ax.set_title(met.upper())
        _estilo(ax)
    axes[0].set_ylabel("valor da métrica")
    if len(retrievers) > 1:
        from matplotlib.patches import Patch
        # abaixo dos eixos: dentro do gráfico a legenda cobria as barras
        fig.legend(
            handles=[Patch(facecolor="#888", alpha=_ALPHAS[i % len(_ALPHAS)],
                           hatch=_HACHURAS[i % len(_HACHURAS)],
                           label=ROTULO_CURTO_RETRIEVER.get(r, r.replace("dense-", "denso ")))
                     for i, r in enumerate(retrievers)],
            loc="lower center", bbox_to_anchor=(0.5, -0.30),
            ncol=min(len(retrievers), 4), frameon=False, fontsize=8)
    if len(retrievers) > 1:
        ctx = {**ctx, "retriever": " × ".join(
            ROTULO_CURTO_RETRIEVER.get(r, r.replace("dense-", "denso ")) for r in retrievers)}
    _titulo(fig, "Estratégias de chunking — quatro métricas de recuperação", ctx, y=1.06)
    # rótulos rotacionados a 35° ocupam ~0.18 da altura abaixo do eixo
    _rodape(fig, ctx, y0=-0.22)
    _salvar(fig, destino, ctx, "resultados_principais")


def fig_recorte(rows: list[dict], destino: Path, ctx: dict, nome: str, titulo: str,
                ordem: list[str] | None = None, rotulos_x: dict | None = None) -> None:
    """Recorte com barras e intervalo de confiança de 95% (bootstrap, 10k)."""
    if not rows:
        return
    valores = ordem or sorted({r["valor"] for r in rows})
    runs = sorted({r["run"] for r in rows})
    com_ret = mais_de_um_retriever(runs)
    n_por_valor = {v: next((r["n_queries"] for r in rows if r["valor"] == v), "?") for v in valores}

    fig, ax = plt.subplots(figsize=(2.1 * len(valores) + 4, 4.6))
    largura = 0.8 / max(len(runs), 1)
    for i, run in enumerate(runs):
        est, _ = partes_do_run(run)
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
        # na legenda o rótulo fica numa linha só; nos eixos é que a quebra ajuda
        ax.bar(pos, medias, largura * 0.88,
               label=rotulo_do_run(run, com_ret).replace("\n", " · "),
               color=CORES.get(est, "#888"), edgecolor="white", linewidth=0.7)
        ax.errorbar(pos, medias, yerr=list(zip(*erros)), fmt="none", ecolor="#333",
                    elinewidth=1.1, capsize=3)
    ax.set_xticks([j + largura * (len(runs) - 1) / 2 for j in range(len(valores))])
    ax.set_xticklabels([f"{(rotulos_x or {}).get(v, v)}\n(n={n_por_valor[v]})" for v in valores])
    ax.set_ylabel("nDCG@10  (barras de erro: IC 95%, bootstrap 10k)")
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper right")
    _estilo(ax)
    _titulo(fig, titulo, ctx, y=1.04)
    _rodape(fig, ctx, extra="n = consultas em cada grupo")
    _salvar(fig, destino, ctx, nome)


def fig_secoes(rows: list[dict], destino: Path, ctx: dict) -> None:
    """De qual seção do acórdão vem o chunk que fez o documento ser recuperado."""
    if not rows:
        return
    ordem_sec = ["ementa", "relatorio", "fundamentacao", "dispositivo", "indefinido"]
    cores_sec = ["#e09f3e", "#6a994e", "#1b4965", "#bc4749", "#adb5bd"]
    por_run: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        por_run[r["run"]][r["valor"]] = float(r["fracao"])
    runs = sorted(por_run)
    top_k = next((r["top_k"] for r in rows), "?")

    fig, ax = plt.subplots(figsize=(9.5, 0.7 * len(runs) + 2.6))
    fundo = [0.0] * len(runs)
    for sec, cor in zip(ordem_sec, cores_sec):
        vals = [por_run[r].get(sec, 0.0) for r in runs]
        if not any(vals):
            continue
        ax.barh(range(len(runs)), vals, left=fundo, label=sec, color=cor,
                edgecolor="white", linewidth=0.7)
        for i, (v, f0) in enumerate(zip(vals, fundo)):
            if v >= 0.06:
                ax.text(f0 + v / 2, i, f"{v:.0%}", ha="center", va="center",
                        fontsize=7.5, color="white")
        fundo = [f + v for f, v in zip(fundo, vals)]
    ax.set_yticks(range(len(runs)))
    ax.set_yticklabels([rotulo_do_run(r, mais_de_um_retriever(runs)) for r in runs])
    ax.set_xlim(0, 1)
    ax.set_xlabel(f"fração dos chunks vencedores no top-{top_k} de cada consulta")
    ax.legend(frameon=False, ncol=5, fontsize=8.5, loc="lower center",
              bbox_to_anchor=(0.5, -0.32))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    _titulo(fig, "Seção do acórdão de onde vem o trecho que recuperou o documento", ctx, y=1.05)
    _rodape(fig, ctx, extra="nas baselines a seção vem do offset do chunk contra os spans ouro")
    _salvar(fig, destino, ctx, "secoes_recuperadas")


def fig_significancia(rows: list[dict], destino: Path, ctx: dict) -> None:
    """Matriz de p-valores entre os runs, com o limiar de 0,05 destacado."""
    if not rows:
        return
    import numpy as np

    runs = sorted({r["run_a"] for r in rows} | {r["run_b"] for r in rows})
    idx = {r: i for i, r in enumerate(runs)}
    m = np.full((len(runs), len(runs)), np.nan)
    for r in rows:
        i, j = idx[r["run_a"]], idx[r["run_b"]]
        m[i, j] = m[j, i] = float(r["p_value"])
    metrica = next((r["metric"] for r in rows), "ndcg@10")
    n_sig = int(sum(1 for r in rows if float(r["p_value"]) < 0.05))

    fig, ax = plt.subplots(figsize=(1.15 * len(runs) + 4, 1.0 * len(runs) + 3.2))
    im = ax.imshow(m, cmap="RdYlGn_r", vmin=0, vmax=1)
    for i in range(len(runs)):
        for j in range(len(runs)):
            if not np.isnan(m[i, j]):
                marca = " *" if m[i, j] < 0.05 else ""
                ax.text(j, i, f"{m[i, j]:.3f}{marca}", ha="center", va="center",
                        fontsize=8, color="#111")
    com_ret = mais_de_um_retriever(runs)
    rot = [rotulo_do_run(r, com_ret) for r in runs]
    ax.set_xticks(range(len(runs)), rot, rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(len(runs)), rot, fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.75, label="p-valor")
    _titulo(fig, f"p-valores pareados sobre {metrica} — teste t pareado, correção para "
                 f"comparações múltiplas\n* = p < 0,05  ({n_sig} de {len(rows)} pares)", ctx, y=1.10)
    _rodape(fig, ctx)
    _salvar(fig, destino, ctx, "significancia")


# --- CLI --------------------------------------------------------------------------

def fig_condicoes(rows: list[dict], destino: Path, ctx: dict, referencia: str | None = None
                  ) -> None:
    """Progressão de condições experimentais, em barras horizontais.

    A `fig_principal` agrupa por estratégia e reserva uma barra vertical para
    cada condição: ótima para 5 estratégias × 2 retrievers, ilegível para uma
    estratégia × 7 condições, que é o formato da tabela principal da F6. Aqui
    cada condição é uma linha, e o rótulo tem espaço para dizer o que ela é.

    `referencia` é o run tomado como linha de base; a variação percentual
    contra ele é impressa ao lado de cada barra, porque "0,3160" não diz nada
    sozinho e "+27,1%" diz.
    """
    if len(rows) < 3:
        return
    metricas = ["ndcg@10", "mrr@10", "map@10", "recall@100"]
    ordenado = sorted(rows, key=lambda r: float(r["ndcg@10"]))
    base = None
    if referencia:
        base = next((r for r in rows if r["run"] == referencia), None)
    if base is None:
        base = ordenado[0]

    rotulos = []
    for r in ordenado:
        est, cond = partes_do_run(r["run"])
        rotulos.append(f"{ROTULOS.get(est, est)}\n{cond}")

    altura = max(3.2, 0.62 * len(ordenado))
    fig, axes = plt.subplots(1, len(metricas), figsize=(4.0 * len(metricas), altura),
                             sharey=True)
    y = range(len(ordenado))
    for ax, met in zip(axes, metricas):
        valores = [float(r[met]) for r in ordenado]
        v_base = float(base[met])
        ax.barh(list(y), valores, height=0.68,
                color=["#6a994e" if v > v_base else ("#bc4749" if v < v_base else "#888")
                       for v in valores],
                alpha=0.85, edgecolor="white", linewidth=0.8)
        limite = max(valores) * 1.34
        for i, v in enumerate(valores):
            delta = (v - v_base) / v_base * 100 if v_base else 0.0
            txt = f"{v:.4f}" + (f"  ({delta:+.1f}%)" if ordenado[i] is not base else "  (base)")
            ax.text(v + limite * 0.015, i, txt, va="center", fontsize=6.8, color="#333")
        ax.axvline(v_base, color="#555", linestyle=":", linewidth=0.9)
        ax.set_xlim(0, limite)
        ax.set_title(met.upper())
        _estilo(ax)
    axes[0].set_yticks(list(y))
    axes[0].set_yticklabels(rotulos, fontsize=7.5)
    ctx = {**ctx, "retriever": "comparação de condições"}
    _titulo(fig, "Efeito de cada intervenção sobre a recuperação", ctx, y=1.04)
    _rodape(fig, ctx, extra="linha pontilhada = baseline", y0=-0.06)
    _salvar(fig, destino, ctx, "condicoes")


def gerar_figuras(exp: Path, destino: Path | None = None,
                  tabelas: Path | None = None, rotulo_extra: str = "",
                  referencia: str | None = None) -> Path:
    ctx = contexto_da_rodada(exp)
    if rotulo_extra:
        # A rodada de origem continua sendo a mesma; o sufixo diz que a tabela
        # cruza runs de mais de uma (`--incluir`), o que muda o que a figura
        # mostra sem mudar de onde vieram os dados.
        ctx["rodada"] = f"{ctx['rodada']}_{rotulo_extra}"
    tabelas = tabelas or (exp / "tables")
    figuras = destino or (exp / "figuras")
    print(f"rodada: {ctx['rodada']}  ({ctx['data']}, {ctx['retriever']}, commit {ctx['commit']})")
    principais = ler_csv(tabelas / "main_results.csv")
    fig_principal(principais, figuras, ctx)
    fig_condicoes(principais, figuras, ctx, referencia=referencia)
    fig_recorte(ler_csv(tabelas / "slices_query_type.csv"), figuras, ctx,
                "recorte_tipo_consulta", "Desempenho por tipo de consulta do JurisTCU",
                rotulos_x={"LLM": "pergunta (LLM)",
                           "expression from LLM question": "expressão (LLM)",
                           "search log": "consulta real (log)"})
    fig_recorte(ler_csv(tabelas / "slices_doc_length.csv"), figuras, ctx,
                "recorte_tamanho_doc", "Desempenho por tercil de tamanho do documento relevante",
                ordem=["curto", "medio", "longo"],
                rotulos_x={"curto": "curto", "medio": "médio", "longo": "longo"})
    fig_secoes(ler_csv(tabelas / "slices_section.csv"), figuras, ctx)
    fig_significancia(ler_csv(tabelas / "significance.csv"), figuras, ctx)
    print(f"figuras em {figuras}")
    return figuras


def main() -> None:
    from .experiment import EXPERIMENTS_DIR

    ap = argparse.ArgumentParser(description="Gera as figuras a partir das tabelas de uma rodada.")
    ap.add_argument("--referencia", default=None,
                    help="Nome do run tomado como baseline na figura de condicoes. "
                         "Sem isso, o pior run vira a referencia, o que exagera o ganho.")
    ap.add_argument("--experiment", type=Path, default=None)
    ap.add_argument("--destino", type=Path, default=None,
                    help="Pasta de saída (default: <experimento>/figuras/).")
    ap.add_argument("--tables", type=Path, default=None,
                    help="Pasta de tabelas (default: <experimento>/tables/). Use para "
                         "figuras de uma avaliação feita com --incluir.")
    ap.add_argument("--rotulo-extra", default="",
                    help="Sufixo no nome dos arquivos, ex.: 'com_bm25'.")
    args = ap.parse_args()

    exp = args.experiment
    if exp is None:
        candidatos = [d for d in sorted(EXPERIMENTS_DIR.iterdir(), reverse=True)
                      if d.is_dir() and (d / "tables" / "main_results.csv").is_file()]
        if not candidatos:
            raise SystemExit("nenhuma rodada com tabelas; rode `python -m src.evaluate` antes")
        exp = candidatos[0]
    gerar_figuras(exp, args.destino, args.tables, args.rotulo_extra, args.referencia)


if __name__ == "__main__":
    main()
