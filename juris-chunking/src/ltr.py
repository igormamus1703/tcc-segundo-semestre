"""F7 — Ranker aprendido sensível à seção (learning-to-rank).

A F6 decidiu À MÃO o que fazer com cada seção: tirar o relatório, manter o
resto. Foi uma decisão binária, tomada olhando os julgamentos do mesmo
benchmark em que depois foi medida. Este módulo troca a decisão manual por uma
**aprendida dos dados**, numa coleção de treino que nunca entra na avaliação:

- **treino:** 6 mil consultas do split de *treino* do JUÁ-Juris (`src/jua.py`);
- **teste:** o split de *teste* do JUÁ-Juris e o **JurisTCU** — uma coleção
  que o modelo nunca viu, com outro tipo de consulta (log real, perguntas) e
  relevância graduada.

**Os sinais.** Para cada par (consulta, documento), o que doze buscas dizem
dele: BM25 e denso, cada um sobre o documento inteiro, sem o relatório, e
sobre cada seção isolada (ementa, relatório, fundamentação, dispositivo). De
cada busca saem o score normalizado na consulta e a posição. Mais três
atributos de contexto: tamanho do documento, fração dele que é relatório e
tamanho da consulta.

Com isso o modelo pode aprender, por exemplo, que um casamento forte que só
existe no relatório vale pouco, ou que a fundamentação vale mais para
consultas longas — exatamente o que a F6 não conseguia expressar com um corte
binário. É a versão aprendida do BM25F (Robertson et al. 2004): pesos por
campo, só que estimados por LambdaMART (Burges 2010) em vez de fixados.

**A pergunta científica é a ablação.** O mesmo modelo, treinado *sem* os
sinais por seção (só BM25 e denso sobre o documento inteiro), é a fusão
aprendida "comum". Se o modelo com seções ganhar dele, a estrutura do acórdão
agrega valor mesmo quando a combinação dos sinais é aprendida, e não só
quando é feita à mão.

**Interpretação.** O LightGBM calcula valores SHAP de forma exata para
árvores (`pred_contrib`, Lundberg et al. 2020). A média de |SHAP| por sinal,
agrupada por seção, mostra *o que o modelo aprendeu* sobre cada parte do
acórdão — uma medida da importância de cada seção que não depende de
nenhuma escolha nossa.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from .experiment import EXPERIMENTS_DIR, ultima_rodada
from .fusion import Ranking, escrever_trec, ler_trec

SECOES = ("ementa", "relatorio", "fundamentacao", "dispositivo")
RETRIEVERS = ("bm25", "dense")
# sinal -> (retriever, "visão" do documento)
SINAIS = {f"{r}_{v}": (r, v) for r in RETRIEVERS
          for v in ("doc", "sem_relatorio", *SECOES)}
POOL = ("bm25_doc", "bm25_sem_relatorio", "dense_doc", "dense_sem_relatorio")
PROFUNDIDADE = 100      # top-k de cada sinal-pool que entra nos candidatos
TOPO_SINAL = 200        # todo sinal é truncado aqui ANTES de normalizar
AUSENTE = TOPO_SINAL + 1  # posição atribuída a quem não aparece no top do sinal


# --- atributos (puro, testado) -----------------------------------------------

def normalizar(docs: dict[str, float], topo: int = TOPO_SINAL
               ) -> tuple[dict[str, float], dict[str, int]]:
    """(score min-max na consulta, posição a partir de 1) do top-`topo` de um ranking.

    **O corte vem antes do min-max, e isso não é detalhe.** Os runs de treino
    têm 200 documentos por consulta, e parte dos runs de teste tem 1.000. Sem
    o corte, o mínimo de uma lista de 1.000 é muito menor, todo score
    normalizado sobe, e o modelo recebe no teste uma distribuição que nunca
    viu. A primeira versão do LTR tinha esse defeito: no JurisTCU, o modelo
    "sem seções" ficava 29% abaixo do próprio BM25 que ele recebia como
    atributo. Travado por `test_normalizar_corta_antes_do_minmax`.
    """
    if not docs:
        return {}, {}
    ordem = sorted(docs.items(), key=lambda kv: (-kv[1], kv[0]))[:topo]
    docs = dict(ordem)
    lo, hi = min(docs.values()), max(docs.values())
    faixa = hi - lo
    norm = {d: (0.5 if faixa == 0 else (s - lo) / faixa) for d, s in docs.items()}
    pos = {d: i for i, (d, _s) in enumerate(ordem, start=1)}
    return norm, pos


def candidatos(sinais: dict[str, Ranking], qid: str, profundidade: int = PROFUNDIDADE) -> list[str]:
    """União do top-`profundidade` dos sinais-pool, em ordem determinística."""
    vistos: dict[str, None] = {}
    for nome in POOL:
        docs = sinais.get(nome, {}).get(qid, {})
        for d, _s in sorted(docs.items(), key=lambda kv: (-kv[1], kv[0]))[:profundidade]:
            vistos.setdefault(d, None)
    return list(vistos)


def nomes_atributos(sinais: list[str]) -> list[str]:
    # Sem atributo de tamanho da consulta: o treino (enunciados do JUÁ) só tem
    # consultas de 10 a 60 palavras, e o JurisTCU tem consultas de 3. Uma árvore
    # extrapolaria uma divisão aprendida em "12 palavras" para um regime que
    # nunca viu. Removido na segunda versão, junto com o corte do `normalizar`.
    return ([f"{s}__score" for s in sinais] + [f"{s}__posicao" for s in sinais]
            + ["doc_log_tamanho", "doc_fracao_relatorio"])


def matriz(
    sinais: dict[str, Ranking],
    usar: list[str],
    qids: list[str],
    textos: dict[str, str],
    doc_info: dict[str, tuple[float, float]],
    qrels: dict[str, dict[str, int]] | None = None,
) -> tuple[np.ndarray, np.ndarray, list[int], list[tuple[str, str]]]:
    """(X, y, tamanho de cada grupo, (qid, doc) de cada linha).

    Um grupo por consulta, como o LambdaRank exige; as linhas de uma consulta
    ficam contíguas e na ordem de `candidatos`.
    """
    linhas, rotulos, grupos, chaves = [], [], [], []
    for qid in qids:
        cands = candidatos(sinais, qid)
        if not cands:
            continue
        por_sinal = [normalizar(sinais.get(s, {}).get(qid, {})) for s in usar]
        for d in cands:
            scores = [ns.get(d, 0.0) for ns, _p in por_sinal]
            posicoes = [p.get(d, AUSENTE) for _ns, p in por_sinal]
            log_tam, frac_rel = doc_info.get(d, (0.0, 0.0))
            linhas.append(scores + posicoes + [log_tam, frac_rel])
            rotulos.append((qrels or {}).get(qid, {}).get(d, 0))
            chaves.append((qid, d))
        grupos.append(len(cands))
    return (np.asarray(linhas, dtype=np.float32), np.asarray(rotulos, dtype=np.int32),
            grupos, chaves)


def dividir_por_consulta(qids: list[str], fracao_validacao: float, seed: int = 42
                         ) -> tuple[list[str], list[str]]:
    """Treino/validação separados POR CONSULTA: nenhuma consulta nos dois."""
    ordenados = sorted(qids)
    rng = np.random.default_rng(seed)
    embaralhados = list(rng.permutation(ordenados))
    n_val = int(round(len(embaralhados) * fracao_validacao))
    return sorted(embaralhados[n_val:]), sorted(embaralhados[:n_val])


def run_do_modelo(chaves: list[tuple[str, str]], pontuacao: np.ndarray) -> Ranking:
    out: Ranking = defaultdict(dict)
    for (q, d), s in zip(chaves, pontuacao):
        out[q][d] = float(s)
    return dict(out)


# --- leitura ------------------------------------------------------------------

def resolver_run(ref: str, raiz: Path = EXPERIMENTS_DIR) -> Path:
    """`rotulo/arquivo.trec`, ou `rotulo/*` quando a rodada tem um run só."""
    rotulo, _, arquivo = ref.partition("/")
    rodada = ultima_rodada(rotulo, raiz=raiz)
    if rodada is None:
        raise SystemExit(f"nenhuma rodada com runs para o rotulo {rotulo!r}")
    if arquivo == "*":
        trecs = sorted(p for p in (rodada / "runs").glob("*.trec"))
        if len(trecs) != 1:
            raise SystemExit(f"{rodada}: esperava 1 run, achei {len(trecs)}")
        return trecs[0]
    return rodada / "runs" / arquivo


def ler_qrels(path: Path) -> dict[str, dict[str, int]]:
    q: dict[str, dict[str, int]] = defaultdict(dict)
    with path.open(encoding="utf-8") as f:
        for linha in f:
            qid, _z, d, r = linha.split()
            q[qid][d] = int(r)
    return dict(q)


def ler_textos(path: Path) -> dict[str, str]:
    out = {}
    with path.open(encoding="utf-8") as f:
        for linha in f:
            r = json.loads(linha)
            out[r["query_id"]] = r["text"]
    return out


def info_dos_documentos(gold_spans_path: Path) -> dict[str, tuple[float, float]]:
    """{doc_id: (log do tamanho em caracteres, fração que é relatório)}."""
    spans = json.loads(gold_spans_path.read_text(encoding="utf-8"))
    out = {}
    for doc, ss in spans.items():
        total = max((s["end"] for s in ss), default=0)
        rel = sum(s["end"] - s["start"] for s in ss if s["section"] == "relatorio")
        out[doc] = (math.log1p(total), rel / total if total else 0.0)
    return out


def carregar(spec: dict, raiz_repo: Path) -> dict:
    return {
        "qrels": ler_qrels(raiz_repo / spec["qrels"]),
        "textos": ler_textos(raiz_repo / spec["queries"]),
        "sinais": {nome: ler_trec(resolver_run(ref)) for nome, ref in spec["sinais"].items()},
    }


# --- CLI ----------------------------------------------------------------------

MODELOS = {
    # o modelo completo e as ablações; cada um é uma lista de sinais
    "ltr_secoes": list(SINAIS),
    "ltr_sem_secoes": ["bm25_doc", "dense_doc"],
    "ltr_recorte_f6": ["bm25_doc", "bm25_sem_relatorio", "dense_doc", "dense_sem_relatorio"],
}

PARAMS = dict(
    objective="lambdarank", metric="ndcg", eval_at=[10], n_estimators=3000,
    learning_rate=0.03, num_leaves=31, min_child_samples=50, subsample=0.8,
    subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, lambdarank_truncation_level=30,
    random_state=42, verbose=-1,
)


def main() -> None:
    import argparse

    import lightgbm as lgb

    from .experiment import Experimento

    parser = argparse.ArgumentParser(description="Treina e avalia o ranker aprendido da F7.")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--label", default="f7_ltr")
    parser.add_argument("--validacao", type=float, default=0.15)
    args = parser.parse_args()

    raiz_repo = Path(__file__).resolve().parent.parent
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    doc_info = info_dos_documentos(raiz_repo / spec["gold_spans"])

    with Experimento(args.label, config={"spec": spec, "params": PARAMS,
                                         "modelos": MODELOS}) as exp:
        treino = carregar(spec["treino"], raiz_repo)
        testes = {nome: carregar(c, raiz_repo) for nome, c in spec["testes"].items()}
        exp.log(f"treino: {len(treino['textos'])} consultas; testes: "
                + ", ".join(f"{n} ({len(t['textos'])})" for n, t in testes.items()))

        qids_tr, qids_val = dividir_por_consulta(sorted(treino["textos"]), args.validacao)
        resumo = []
        for nome_modelo, usar in MODELOS.items():
            atributos = nomes_atributos(usar)
            Xtr, ytr, gtr, _ = matriz(treino["sinais"], usar, qids_tr, treino["textos"],
                                      doc_info, treino["qrels"])
            Xva, yva, gva, _ = matriz(treino["sinais"], usar, qids_val, treino["textos"],
                                      doc_info, treino["qrels"])
            modelo = lgb.LGBMRanker(**PARAMS)
            modelo.fit(Xtr, ytr, group=gtr, eval_set=[(Xva, yva)], eval_group=[gva],
                       feature_name=atributos,
                       callbacks=[lgb.early_stopping(200, verbose=False)])
            exp.log(f"{nome_modelo}: {len(atributos)} atributos, {Xtr.shape[0]:,} linhas de treino, "
                    f"melhor iteracao {modelo.best_iteration_}, "
                    f"nDCG@10 val = {modelo.best_score_['valid_0']['ndcg@10']:.4f}")
            modelo.booster_.save_model(str(exp.dir / f"{nome_modelo}.txt"))

            for nome_teste, t in testes.items():
                qids = sorted(t["textos"])
                X, _y, _g, chaves = matriz(t["sinais"], usar, qids, t["textos"], doc_info)
                pont = modelo.predict(X, num_iteration=modelo.best_iteration_)
                # A coleção vai no nome do arquivo, e não numa subpasta: o
                # `ultima_rodada` só enxerga runs em `runs/*.trec`.
                pasta = spec["testes"][nome_teste]["pasta"]
                run_name = f"{spec['estrategia']}__{nome_modelo}"
                escrever_trec(exp.runs_dir / f"{pasta}__{run_name}.trec",
                              run_do_modelo(chaves, pont), run_name)
                if nome_modelo == "ltr_secoes":
                    # SHAP exato de árvore: contribuição de cada atributo por linha
                    contrib = modelo.booster_.predict(X, num_iteration=modelo.best_iteration_,
                                                      pred_contrib=True)[:, :-1]
                    media_abs = np.abs(contrib).mean(axis=0)
                    for a, v, sinal_medio in zip(atributos, media_abs, contrib.mean(axis=0)):
                        resumo.append({"teste": nome_teste, "atributo": a,
                                       "shap_medio_abs": float(v),
                                       "shap_medio": float(sinal_medio)})
                    np.save(exp.dir / f"shap_{spec['testes'][nome_teste]['pasta']}.npy",
                            np.column_stack([contrib, X]).astype(np.float32))

        with (exp.tables_dir / "shap.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(resumo[0].keys()))
            w.writeheader()
            w.writerows(resumo)
        (exp.dir / "atributos.json").write_text(
            json.dumps(nomes_atributos(MODELOS["ltr_secoes"]), ensure_ascii=False), encoding="utf-8")
        exp.log("runs gravados em runs/<pasta>__<run>.trec; avalie com src.replicacao")


if __name__ == "__main__":
    main()
