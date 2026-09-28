"""F6 — Seleção honesta de hiperparâmetro da fusão, por validação cruzada.

Este módulo existe por causa de um problema metodológico, não de engenharia.

A fusão ponderada de BM25 com o retriever denso melhora o nDCG@10 — mas o peso
que a faz melhorar foi escolhido olhando o resultado. Com 150 consultas e uma
varredura de ~24 configurações, **alguma** delas ia parecer boa por acaso;
reportar a melhor como se fosse um achado é o erro clássico de ajustar no
conjunto de teste, e é exatamente o que uma banca procura numa tabela em que
um método novo ganha do baseline por poucos pontos.

A correção é padrão em RI quando existe uma coleção só: **validação cruzada
por consulta**. O peso é escolhido nas dobras de treino e aplicado na dobra de
teste, que não participou da escolha. O número reportado é a média dos scores
de teste das consultas, cada uma pontuada por um modelo que nunca a viu.

O que isso custa: o número fica um pouco menor que o da varredura. O que isso
compra: o número é defensável. A diferença entre os dois — "ganho aparente" e
"ganho após CV" — é ela própria um resultado a reportar, porque quantifica o
quanto da melhoria vinha do ajuste.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from ranx import Qrels, Run

from .analysis import per_query_scores
from .fusion import Ranking, rrf, soma_normalizada

# Grade padrão: peso do BM25 na fusão. O peso do denso é o complemento na soma
# normalizada, e 1.0 fixo no RRF. Inclui 1.0 (fusão democrática) e, no RRF,
# pesos altos — o BM25 é o retriever mais forte, e a hipótese natural é que ele
# deva dominar.
GRADE_SOMA_NORM = (0.5, 0.6, 0.7, 0.8, 0.9)
GRADE_RRF = (1.0, 1.5, 2.0, 3.0, 5.0)


@dataclass
class ResultadoCV:
    metodo: str
    metric: str
    n_folds: int
    # peso escolhido em cada dobra: se variar muito, o "melhor peso" é ruído
    pesos_escolhidos: list[float] = field(default_factory=list)
    scores_teste: dict[str, float] = field(default_factory=dict)  # {qid: score}
    scores_baseline: dict[str, float] = field(default_factory=dict)
    # ranking da dobra de teste, pelo peso escolhido sem ela: o run cruzado
    run_cv: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def media(self) -> float:
        return float(np.mean(list(self.scores_teste.values())))

    @property
    def media_baseline(self) -> float:
        return float(np.mean(list(self.scores_baseline.values())))

    @property
    def ganho_relativo(self) -> float:
        base = self.media_baseline
        return (self.media - base) / base if base else 0.0

    @property
    def peso_estavel(self) -> bool:
        """Todas as dobras escolheram o mesmo peso?

        Se sim, o peso é uma propriedade da coleção, e reportá-lo como
        recomendação faz sentido. Se não, o que se pode afirmar é que *alguma*
        fusão ponderada ajuda — não que 0,7 seja o número certo.
        """
        return len(set(self.pesos_escolhidos)) == 1

    def teste_pareado(self) -> dict:
        from scipy import stats

        qids = sorted(set(self.scores_teste) & set(self.scores_baseline))
        a = np.array([self.scores_teste[q] for q in qids])
        b = np.array([self.scores_baseline[q] for q in qids])
        difs = a - b
        return {
            "n_queries": len(qids),
            "p_value": float(stats.ttest_rel(a, b).pvalue),
            "vitorias": int((difs > 0).sum()),
            "empates": int((difs == 0).sum()),
            "derrotas": int((difs < 0).sum()),
        }


def _fundir(bm25: Ranking, denso: Ranking, metodo: str, peso: float, k: int) -> Ranking:
    if metodo == "soma_norm":
        return soma_normalizada([bm25, denso], pesos=[peso, 1.0 - peso])
    if metodo == "rrf":
        return rrf([bm25, denso], k=k, pesos=[peso, 1.0])
    raise ValueError(f"metodo desconhecido: {metodo!r}")


def _recortar(ranking: Ranking, qids: set[str]) -> Ranking:
    return {q: d for q, d in ranking.items() if q in qids}


def _pontuar(qrels: Qrels, ranking: Ranking, qids: set[str], metric: str) -> dict[str, float]:
    """Scores por consulta, restritos a `qids`.

    O recorte é feito ANTES de entregar ao ranx, e os qrels também são
    recortados: avaliar o run inteiro e filtrar depois daria o mesmo aqui, mas
    passa a dar diferente assim que a métrica for de corpus (como um MAP
    global), e o bug seria invisível.
    """
    qrels_recortado = Qrels({q: d for q, d in qrels.to_dict().items() if q in qids})
    run = Run(_recortar(ranking, qids), name="tmp")
    return per_query_scores(qrels_recortado, run, metric)


def dobras(qids: list[str], n_folds: int, seed: int = 42) -> list[list[str]]:
    """Parte as consultas em `n_folds` dobras, embaralhadas com semente fixa.

    A semente é fixa e explícita porque o resultado da CV depende dela: sem
    isso, dois autores rodando o mesmo comando publicariam números diferentes,
    e nenhum dos dois saberia por quê.
    """
    ordenados = sorted(qids)
    rng = np.random.default_rng(seed)
    embaralhados = list(rng.permutation(ordenados))
    return [embaralhados[i::n_folds] for i in range(n_folds)]


def validacao_cruzada(
    qrels: Qrels,
    bm25: Ranking,
    denso: Ranking,
    metodo: str = "soma_norm",
    grade: tuple[float, ...] | None = None,
    k_rrf: int = 60,
    n_folds: int = 5,
    seed: int = 42,
    metric: str = "ndcg@10",
) -> ResultadoCV:
    """Escolhe o peso nas dobras de treino, mede na dobra de teste.

    A comparação com o baseline usa as MESMAS consultas de teste, uma a uma —
    é o pareamento que dá poder ao teste estatístico. Comparar a média da CV
    com a média global do BM25 seria comparar dois números calculados sobre
    conjuntos diferentes.
    """
    if grade is None:
        grade = GRADE_SOMA_NORM if metodo == "soma_norm" else GRADE_RRF

    qids = sorted(set(bm25) & set(denso) & set(qrels.to_dict()))
    if len(qids) < n_folds:
        raise ValueError(f"{len(qids)} consultas nao dao {n_folds} dobras")

    # As fusões não dependem da dobra — calcular uma vez por peso, e não uma
    # vez por (peso, dobra), corta o trabalho por um fator n_folds.
    fundidos = {p: _fundir(bm25, denso, metodo, p, k_rrf) for p in grade}

    resultado = ResultadoCV(metodo=metodo, metric=metric, n_folds=n_folds)
    todas = dobras(qids, n_folds, seed)
    for i, teste in enumerate(todas):
        treino = {q for j, d in enumerate(todas) if j != i for q in d}
        medias = {
            p: float(np.mean(list(_pontuar(qrels, fundidos[p], treino, metric).values())))
            for p in grade
        }
        # Desempate pelo menor peso: com dois pesos empatados, o mais
        # conservador é o que menos se afasta da fusão democrática.
        melhor = min(grade, key=lambda p: (-medias[p], p))
        resultado.pesos_escolhidos.append(melhor)
        resultado.scores_teste.update(_pontuar(qrels, fundidos[melhor], set(teste), metric))
        resultado.scores_baseline.update(_pontuar(qrels, bm25, set(teste), metric))
        # O ranking de cada consulta de teste vem do peso escolhido SEM ela.
        # Guardá-lo permite gravar um run TREC que é, consulta a consulta, o
        # que a CV mediu — o artefato que comprova o número no artigo.
        for qid in teste:
            if qid in fundidos[melhor]:
                resultado.run_cv[qid] = fundidos[melhor][qid]
    return resultado


@dataclass
class ResultadoSelecao:
    """Escolha de uma CONFIGURAÇÃO (não de um peso) por validação cruzada."""

    metric: str
    n_folds: int
    escolhidas: list[str] = field(default_factory=list)
    scores_teste: dict[str, float] = field(default_factory=dict)
    scores_baseline: dict[str, float] = field(default_factory=dict)
    baseline: str = ""

    @property
    def media(self) -> float:
        return float(np.mean(list(self.scores_teste.values())))

    @property
    def media_baseline(self) -> float:
        return float(np.mean(list(self.scores_baseline.values())))

    @property
    def ganho_relativo(self) -> float:
        b = self.media_baseline
        return (self.media - b) / b if b else 0.0

    @property
    def escolha_estavel(self) -> bool:
        return len(set(self.escolhidas)) == 1

    def teste_pareado(self) -> dict:
        from scipy import stats

        qids = sorted(set(self.scores_teste) & set(self.scores_baseline))
        a = np.array([self.scores_teste[q] for q in qids])
        b = np.array([self.scores_baseline[q] for q in qids])
        difs = a - b
        return {
            "n_queries": len(qids),
            "p_value": float(stats.ttest_rel(a, b).pvalue),
            "vitorias": int((difs > 0).sum()),
            "empates": int((difs == 0).sum()),
            "derrotas": int((difs < 0).sum()),
        }


def selecao_por_cv(
    qrels: Qrels,
    candidatos: dict[str, Ranking],
    baseline: str,
    n_folds: int = 5,
    seed: int = 42,
    metric: str = "ndcg@10",
) -> ResultadoSelecao:
    """Escolhe *qual configuração usar* nas dobras de treino e mede na de teste.

    Existe para responder a uma crítica específica, e séria, ao resultado do
    recorte por seção: **a decisão de descartar o relatório foi tomada olhando
    os dados de relevância** — a estatística "72% da relevância está na
    fundamentação" vem de localizar os excertos julgados relevantes dentro dos
    acórdãos, que são os mesmos julgamentos usados na avaliação.

    Isso não é ajuste de parâmetro por varredura (o recorte tem justificativa
    de domínio anterior à medição), mas também não é independente. A pergunta
    que fica é: *se tivéssemos decidido com menos consultas, decidiríamos o
    mesmo, e o ganho valeria nas consultas que não participaram da decisão?*

    Aqui a escolha entre as configurações candidatas é feita **só com as
    consultas de treino**, e o número reportado vem só das de teste. Se o ganho
    sobrevive, a decisão generaliza entre consultas — que é o que este corpus
    permite testar. **Generalização para outra coleção continua fora de
    alcance, e segue como limitação declarada.**
    """
    if baseline not in candidatos:
        raise ValueError(f"baseline {baseline!r} nao esta entre os candidatos")
    if len(candidatos) < 2:
        raise ValueError("selecao precisa de ao menos duas configuracoes")

    qids = sorted(set(qrels.to_dict()).intersection(*(set(r) for r in candidatos.values())))
    if len(qids) < n_folds:
        raise ValueError(f"{len(qids)} consultas nao dao {n_folds} dobras")

    # Pontuar uma vez por candidato, e recortar por dobra depois: avaliar cada
    # candidato em cada dobra multiplicaria o trabalho por `n_folds` sem mudar
    # nada, já que a pontuação de uma consulta não depende das outras.
    por_candidato = {
        nome: _pontuar(qrels, ranking, set(qids), metric)
        for nome, ranking in candidatos.items()
    }

    resultado = ResultadoSelecao(metric=metric, n_folds=n_folds, baseline=baseline)
    todas = dobras(qids, n_folds, seed)
    for i, teste in enumerate(todas):
        treino = [q for j, d in enumerate(todas) if j != i for q in d]
        medias = {
            nome: float(np.mean([s[q] for q in treino])) for nome, s in por_candidato.items()
        }
        # Desempate por nome, para a escolha ser determinística.
        melhor = min(medias, key=lambda n: (-medias[n], n))
        resultado.escolhidas.append(melhor)
        for q in teste:
            resultado.scores_teste[q] = por_candidato[melhor][q]
            resultado.scores_baseline[q] = por_candidato[baseline][q]
    return resultado


# --- CLI --------------------------------------------------------------------

def _runs_por_estrategia(exp_dir: Path) -> dict[str, Path]:
    runs = exp_dir / "runs" if (exp_dir / "runs").is_dir() else exp_dir
    return {p.stem.split("__")[0]: p for p in sorted(runs.glob("*.trec"))}


def main() -> None:
    import argparse
    import csv

    from .evaluate import evaluate_run, load_qrels
    from .experiment import Experimento
    from .fusion import escrever_trec, ler_trec
    from .ingest import INTERIM_DIR

    parser = argparse.ArgumentParser(
        description="Escolhe o peso da fusao por validacao cruzada por consulta e grava "
                    "o run cruzado — o numero reportado nao usa a consulta de teste na "
                    "escolha do peso."
    )
    parser.add_argument("--bm25", type=Path, required=True, help="Rodada com os runs BM25.")
    parser.add_argument("--denso", type=Path, required=True, help="Rodada com os runs densos.")
    parser.add_argument("--metodo", nargs="+", default=["soma_norm", "rrf"],
                        choices=["soma_norm", "rrf"])
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--k-rrf", type=int, default=60)
    parser.add_argument("--metric", default="ndcg@10")
    parser.add_argument("--qrels", type=Path, default=INTERIM_DIR / "qrels.trec")
    parser.add_argument("--label", default=None)
    args = parser.parse_args()

    qrels = load_qrels(args.qrels)
    lex, den = _runs_por_estrategia(args.bm25), _runs_por_estrategia(args.denso)
    comuns = sorted(set(lex) & set(den))
    if not comuns:
        raise SystemExit(
            f"nenhuma estrategia em comum: bm25={sorted(lex)} denso={sorted(den)}"
        )

    config = {
        "bm25": str(args.bm25), "denso": str(args.denso), "metodos": args.metodo,
        "folds": args.folds, "seed": args.seed, "k_rrf": args.k_rrf,
        "metrica_de_selecao": args.metric, "estrategias": comuns,
    }
    linhas: list[dict] = []
    with Experimento(args.label or f"cv_fusao_{args.folds}fold", config=config) as exp:
        for estrategia in comuns:
            r_bm25 = ler_trec(lex[estrategia])
            r_denso = ler_trec(den[estrategia])
            for metodo in args.metodo:
                r = validacao_cruzada(
                    qrels, r_bm25, r_denso, metodo=metodo, k_rrf=args.k_rrf,
                    n_folds=args.folds, seed=args.seed, metric=args.metric,
                )
                run_name = f"{estrategia}__cv-{metodo}"
                escrever_trec(exp.runs_dir / f"{run_name}.trec", r.run_cv, run_name)
                teste = r.teste_pareado()
                # As métricas completas saem do run cruzado gravado, para que a
                # linha da tabela e o arquivo TREC nunca possam divergir.
                from ranx import Run as _Run
                metricas = evaluate_run(qrels, _Run(r.run_cv, name=run_name))
                linha = {
                    "estrategia": estrategia, "metodo": metodo,
                    "pesos_escolhidos": "|".join(f"{p:g}" for p in r.pesos_escolhidos),
                    "peso_estavel": r.peso_estavel,
                    f"{args.metric}_cv": round(r.media, 4),
                    f"{args.metric}_bm25": round(r.media_baseline, 4),
                    "ganho_relativo": round(r.ganho_relativo, 4),
                    "p_value": round(teste["p_value"], 6),
                    "significativo_p<0.05": teste["p_value"] < 0.05,
                    "vitorias": teste["vitorias"], "empates": teste["empates"],
                    "derrotas": teste["derrotas"],
                    **{k: round(v, 4) for k, v in metricas.items()},
                }
                linhas.append(linha)
                exp.registrar(run_name, linha)
                exp.log(
                    f"{run_name}: {r.media:.4f} vs {r.media_baseline:.4f} "
                    f"({r.ganho_relativo:+.1%}, p={teste['p_value']:.4f}) "
                    f"pesos={linha['pesos_escolhidos']}"
                )

        destino = exp.tables_dir / "cv_fusao.csv"
        with destino.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
            w.writeheader()
            w.writerows(linhas)
        exp.log(f"tabela em {destino}")


if __name__ == "__main__":
    main()
