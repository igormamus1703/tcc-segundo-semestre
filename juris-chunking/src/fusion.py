"""F6 — Fusão de rankings: combinar BM25 e o retriever denso num run só.

O trabalho mediu que o BM25 vence o denso nas cinco estratégias, com p entre
0,000005 e 0,002. Isso **não** quer dizer que o denso seja inútil: quer dizer
que ele erra em lugares diferentes. A pergunta que a fusão responde é se os
dois erram nos MESMOS documentos — se não erram, combiná-los recupera o que
cada um sozinho perde.

É a intervenção mais barata do trabalho: não reindexa nada, não reencoda nada,
lê os arquivos TREC que já estão em `results/experiments/` e escreve um novo.
Segundos de CPU.

Dois métodos, deliberadamente:

- **RRF** (Reciprocal Rank Fusion, Cormack et al. 2009): usa só a POSIÇÃO no
  ranking, nunca o score. É o padrão da área justamente porque BM25 e cosseno
  vivem em escalas incomparáveis — um score de 18,4 do BM25 e um de 0,73 do
  cosseno não têm relação alguma, e somá-los é um erro de categoria.
- **Soma normalizada** (min-max por consulta, com peso): usa a MAGNITUDE. Faz
  sentido testar porque o RRF descarta informação — a distância entre o 1º e o
  2º colocado diz algo — e porque, com um retriever claramente mais forte que
  o outro, dar peso a ele pode superar a fusão democrática do RRF.

Reportar os dois é o que separa "usamos fusão híbrida" de "medimos qual fusão
funciona aqui, e por quê".
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

Ranking = dict[str, dict[str, float]]  # {query_id: {doc_id: score}}


def ler_trec(path: Path) -> Ranking:
    """Lê um run TREC em UTF-8.

    Não reusa `evaluate.load_run` de propósito: aquele devolve um `Run` do
    ranx, que normaliza e ordena internamente. Aqui precisamos do ranking cru,
    com a ordem original, porque o RRF depende da POSIÇÃO — e a posição tem de
    ser a que o retriever produziu, não a que uma biblioteca reconstruiu.
    """
    ranking: Ranking = defaultdict(dict)
    with path.open(encoding="utf-8") as f:
        for line in f:
            partes = line.split()
            if len(partes) < 5:
                continue
            qid, doc_id, score = partes[0], partes[2], partes[4]
            ranking[qid][doc_id] = float(score)
    return dict(ranking)


def _posicoes(ranking: Ranking) -> dict[str, dict[str, int]]:
    """{query_id: {doc_id: rank}}, com rank começando em 1."""
    return {
        qid: {doc: i for i, (doc, _s) in
              enumerate(sorted(docs.items(), key=lambda kv: -kv[1]), start=1)}
        for qid, docs in ranking.items()
    }


def rrf(rankings: list[Ranking], k: int = 60, pesos: list[float] | None = None) -> Ranking:
    """Reciprocal Rank Fusion: `score(d) = Σ_r peso_r / (k + rank_r(d))`.

    `k = 60` é o valor do artigo original e o default de praticamente toda
    implementação; ele amortece o topo, impedindo que um único retriever muito
    confiante no 1º lugar domine a fusão. Fica exposto como parâmetro porque
    varrê-lo é uma análise de sensibilidade barata, e um k escolhido sem
    justificativa é exatamente o tipo de grau de liberdade que a banca cobra.

    Documento que aparece em um ranking só entra com a parcela daquele
    ranking — não é penalizado explicitamente, mas perde para quem os dois
    retrievers encontraram, que é a propriedade desejada.
    """
    if not rankings:
        raise ValueError("nada para fundir")
    if pesos is None:
        pesos = [1.0] * len(rankings)
    if len(pesos) != len(rankings):
        raise ValueError(f"{len(pesos)} pesos para {len(rankings)} rankings")

    fundido: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for ranking, peso in zip(rankings, pesos):
        for qid, posicao_do_doc in _posicoes(ranking).items():
            for doc_id, rank in posicao_do_doc.items():
                fundido[qid][doc_id] += peso / (k + rank)
    return {qid: dict(docs) for qid, docs in fundido.items()}


def soma_normalizada(rankings: list[Ranking], pesos: list[float] | None = None) -> Ranking:
    """Min-max por consulta e soma ponderada dos scores.

    A normalização é **por consulta**, não global: o BM25 dá scores muito
    maiores para consultas longas, e normalizar sobre o corpus inteiro faria
    as consultas curtas contribuírem quase nada para a fusão.

    Consulta em que todos os scores são iguais (denominador zero) recebe 0,5
    para todos os documentos — ou seja, aquele retriever não opina, em vez de
    produzir NaN que se propaga silenciosamente até a métrica final.
    """
    if not rankings:
        raise ValueError("nada para fundir")
    if pesos is None:
        pesos = [1.0] * len(rankings)
    if len(pesos) != len(rankings):
        raise ValueError(f"{len(pesos)} pesos para {len(rankings)} rankings")

    fundido: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for ranking, peso in zip(rankings, pesos):
        for qid, docs in ranking.items():
            if not docs:
                continue
            valores = docs.values()
            lo, hi = min(valores), max(valores)
            faixa = hi - lo
            for doc_id, score in docs.items():
                norm = 0.5 if faixa == 0 else (score - lo) / faixa
                fundido[qid][doc_id] += peso * norm
    return {qid: dict(docs) for qid, docs in fundido.items()}


METODOS = {"rrf": rrf, "soma_norm": soma_normalizada}


def escrever_trec(path: Path, ranking: Ranking, run_name: str, top_docs: int = 1000) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for qid, docs in ranking.items():
            ordenado = sorted(docs.items(), key=lambda kv: -kv[1])[:top_docs]
            for rank, (doc_id, score) in enumerate(ordenado, start=1):
                f.write(f"{qid} Q0 {doc_id} {rank} {score:.6f} {run_name}\n")
                n += 1
    return n


def agrupar_por_estrategia(paths: list[Path]) -> dict[str, list[Path]]:
    """`structural_gold__bm25.trec` -> chave `structural_gold`.

    Fundir dois retrievers da MESMA estratégia é o que isola o efeito da
    fusão. Fundir `structural_gold__bm25` com `fixed_512_256__dense` mediria
    fusão e mudança de chunking ao mesmo tempo, e nenhum dos dois efeitos
    ficaria interpretável.
    """
    grupos: dict[str, list[Path]] = defaultdict(list)
    for p in paths:
        grupos[p.stem.split("__")[0]].append(p)
    return dict(grupos)


def _retriever_do_run(path: Path) -> str:
    partes = path.stem.split("__")
    return partes[1] if len(partes) > 1 else "desconhecido"


def main() -> None:
    import argparse

    from .experiment import EXPERIMENTS_DIR, Experimento

    parser = argparse.ArgumentParser(
        description="Funde os runs de duas ou mais rodadas (tipicamente BM25 + denso) "
                    "numa rodada nova, sem reindexar nada."
    )
    parser.add_argument("--experimentos", type=Path, nargs="+", required=True,
                        help="Pastas em results/experiments/ cujos runs serao fundidos.")
    parser.add_argument("--metodo", default="rrf", choices=list(METODOS))
    parser.add_argument("--k", type=int, default=60, help="Constante do RRF.")
    parser.add_argument("--pesos", type=float, nargs="+", default=None,
                        help="Um peso por experimento, na mesma ordem. Default: todos 1.")
    parser.add_argument("--top-docs", type=int, default=1000)
    parser.add_argument("--label", default=None)
    args = parser.parse_args()

    por_dir: list[list[Path]] = []
    for d in args.experimentos:
        runs_dir = d / "runs" if (d / "runs").is_dir() else d
        encontrados = sorted(runs_dir.glob("*.trec"))
        if not encontrados:
            raise SystemExit(f"nenhum run em {runs_dir}")
        por_dir.append(encontrados)

    # Um run por (estratégia, experimento). Se uma rodada tiver dois runs da
    # mesma estratégia (duas agregações, por exemplo), é ambíguo qual fundir —
    # melhor abortar do que escolher em silêncio.
    catalogo: dict[str, list[Path]] = defaultdict(list)
    for paths in por_dir:
        grupos = agrupar_por_estrategia(paths)
        for estrategia, lista in grupos.items():
            if len(lista) > 1:
                raise SystemExit(
                    f"{estrategia}: {len(lista)} runs na mesma rodada "
                    f"({[p.name for p in lista]}) — qual fundir e ambiguo"
                )
            catalogo[estrategia].append(lista[0])

    fundiveis = {e: ps for e, ps in catalogo.items() if len(ps) >= 2}
    if not fundiveis:
        raise SystemExit(
            "nenhuma estrategia aparece em 2+ rodadas — nao ha o que fundir.\n"
            f"  estrategias por rodada: "
            f"{[sorted(agrupar_por_estrategia(p)) for p in por_dir]}"
        )
    sozinhas = sorted(set(catalogo) - set(fundiveis))
    if sozinhas:
        print(f"  ignorando (so uma rodada tem): {sozinhas}")

    sufixo = f"{args.metodo}{'' if args.metodo != 'rrf' else f'-k{args.k}'}"
    if args.pesos:
        sufixo += "-p" + "_".join(f"{p:g}" for p in args.pesos)
    rotulo = args.label or f"fusao_{sufixo}"

    config = {
        "metodo": args.metodo,
        "k_rrf": args.k if args.metodo == "rrf" else None,
        "pesos": args.pesos,
        "experimentos_fundidos": [str(d) for d in args.experimentos],
        "top_docs": args.top_docs,
        "estrategias": sorted(fundiveis),
    }

    with Experimento(rotulo, config=config) as exp:
        for estrategia, paths in sorted(fundiveis.items()):
            rankings = [ler_trec(p) for p in paths]
            if args.metodo == "rrf":
                fundido = rrf(rankings, k=args.k, pesos=args.pesos)
            else:
                fundido = soma_normalizada(rankings, pesos=args.pesos)
            run_name = f"{estrategia}__{sufixo}"
            n = escrever_trec(exp.runs_dir / f"{run_name}.trec", fundido, run_name,
                              top_docs=args.top_docs)
            fontes = [f"{_retriever_do_run(p)}" for p in paths]
            exp.registrar(run_name, {
                "fontes": fontes,
                "arquivos": [str(p) for p in paths],
                "n_queries": len(fundido),
                "n_linhas_run": n,
            })
            exp.log(f"{run_name}: {' + '.join(fontes)} -> {n:,} linhas")

        exp.log(f"avalie com: python -m src.evaluate --experiment {exp.dir} "
                f"--incluir {' '.join(str(d) for d in args.experimentos)}")
    _ = EXPERIMENTS_DIR  # o índice é reescrito no __exit__ do Experimento


if __name__ == "__main__":
    main()
