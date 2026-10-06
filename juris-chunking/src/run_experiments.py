"""F4 — Runs: estratégia de chunking x retriever -> arquivo TREC.

Para cada par (estratégia, retriever): busca os top-N CHUNKS de cada consulta,
agrega chunk -> documento e grava o ranking de documentos no formato TREC
(`results/runs/{estrategia}__{retriever}[__{agregacao}].trec`).

A agregação é o ponto metodológico delicado: o índice é de chunks, mas os
qrels são de documentos. Buscamos fundo em chunks (`--top-chunks`, 2000 por
padrão) justamente para que documentos longos, cujos chunks se espalham pelo
ranking, não sejam truncados antes da agregação.

Uso:
    python -m src.run_experiments --strategy all --retriever bm25
    python -m src.run_experiments --strategy all --retriever bm25 --limit-queries 10
    python -m src.run_experiments --strategy structural_gold --retriever dense
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml

from . import sections as secoes_mod
from .chunkers.base import Chunk
from .chunkers.run import PROCESSED_DIR
from .experiment import Experimento
from .ingest import INTERIM_DIR
from .retrieval import max_pooling, sum_top_k

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNS_DIR = REPO_ROOT / "results" / "runs"
MODELS_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "models.yaml"

AGGREGATIONS = {"max_pooling": max_pooling, "sum_top_k": sum_top_k}


def load_models_config(path: Path = MODELS_CONFIG) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_queries(path: Path, limit: int | None = None) -> list[dict]:
    queries = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                break
            queries.append(json.loads(line))
    return queries


def load_chunks(strategy: str, processed_dir: Path = PROCESSED_DIR) -> list[Chunk]:
    path = processed_dir / strategy / "chunks.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} nao existe. Rode antes: "
            f"python -m src.chunkers.run --strategy {strategy}"
        )
    chunks = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            chunks.append(
                Chunk(
                    chunk_id=d["chunk_id"],
                    doc_id=d["doc_id"],
                    text=d["text"],
                    section=d.get("section"),
                    start=d["start"],
                    end=d["end"],
                )
            )
    return chunks


def build_index(retriever: str, chunks: list[Chunk], models_cfg: dict, embedder: str | None):
    """Devolve um índice já construído, com a interface comum
    (`search_batch`, `chunk_ids`, `doc_ids`)."""
    if retriever == "bm25":
        from .indexing.lexical import BM25Index

        index = BM25Index(backend=models_cfg.get("lexical", {}).get("backend", "bm25s"))
        index.build(chunks)
        return index

    if retriever == "dense":
        from .indexing.dense import DenseIndex

        embedders = {e["name"]: e for e in models_cfg["embedders"]}
        name = embedder or models_cfg.get("dense", {}).get("default_embedder")
        if name not in embedders:
            raise SystemExit(f"embedder desconhecido: {name!r} (opcoes: {list(embedders)})")
        cfg = embedders[name]
        if cfg["hf_id"] == "PREENCHER":
            raise SystemExit(f"embedder {name!r} esta com hf_id 'PREENCHER' em models.yaml")
        return DenseIndex(
            model_name=cfg["hf_id"],
            query_prefix=cfg.get("query_prefix", ""),
            passage_prefix=cfg.get("passage_prefix", ""),
            batch_size=cfg.get("batch_size", 64),
            max_seq_length=cfg.get("max_seq_length"),
            dtype=cfg.get("dtype", "auto"),
        )

    raise SystemExit(f"retriever desconhecido: {retriever!r} (use 'bm25' ou 'dense')")


def write_trec_run(path: Path, ranked: dict[str, list[tuple[str, float]]], run_name: str) -> int:
    """`qid Q0 docid rank score nome` — uma linha por documento recuperado."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n_lines = 0
    with path.open("w", encoding="utf-8") as f:
        for qid, docs in ranked.items():
            for rank, (doc_id, score) in enumerate(docs, start=1):
                f.write(f"{qid} Q0 {doc_id} {rank} {score:.6f} {run_name}\n")
                n_lines += 1
    return n_lines


def write_chunks_top(
    path: Path,
    ranked: dict[str, list[tuple[str, float]]],
    vencedores: dict[str, dict[str, tuple[str, float]]],
    posicao: dict[str, tuple[str | None, int, int]],
    run_name: str,
    top_k: int = 50,
) -> int:
    """Grava o chunk que "ganhou" cada documento recuperado, com seu offset.

    Só os `top_k` primeiros documentos de cada consulta — é o que a análise por
    seção usa, e guardar os 1000 multiplicaria o arquivo sem serventia.
    """
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for qid, docs in ranked.items():
            for rank, (doc_id, score) in enumerate(docs[:top_k], start=1):
                venc = vencedores.get(qid, {}).get(doc_id)
                if not venc:
                    continue
                pos = posicao.get(venc[0])
                if pos is None:
                    continue
                section, start, end = pos
                f.write(json.dumps({
                    "run": run_name, "query_id": qid, "rank": rank,
                    "doc_id": doc_id, "chunk_id": venc[0],
                    "section": section, "start": start, "end": end,
                    "score": round(float(score), 6),
                }, ensure_ascii=False) + "\n")
                n += 1
    return n


def run_one(
    strategy: str,
    retriever: str,
    queries: list[dict],
    models_cfg: dict,
    top_chunks: int = 2000,
    top_docs: int = 1000,
    aggregation: str = "max_pooling",
    embedder: str | None = None,
    processed_dir: Path = PROCESSED_DIR,
    runs_dir: Path = RUNS_DIR,
    log=None,
    bloco: int = 25_000,
    secoes: set[str] | None = None,
    pesos: dict[str, float] | None = None,
    spans_por_doc: dict[str, list[dict]] | None = None,
    amostra: float | None = None,
    amostra_seed: int = 42,
    amostra_igual_a: set[str] | None = None,
    criterio: str = "maioria",
) -> dict:
    t0 = time.time()
    chunks = load_chunks(strategy, processed_dir)

    # F6 — recorte do índice por seção do acórdão. O filtro roda ANTES de
    # construir o índice: é isso que faz o índice encolher (e o BM25 ficar mais
    # rápido), em vez de só descartar resultados depois da busca. Filtrar
    # depois daria outro número — os chunks descartados ainda teriam ocupado
    # vagas no top-k da busca.
    recorte_secoes: dict | None = None
    if secoes:
        spans = spans_por_doc or {}
        antes = len(chunks)
        chunks, contagem = secoes_mod.filtrar(chunks, secoes, spans, criterio=criterio)
        if not chunks:
            raise SystemExit(
                f"{strategy}: o recorte {sorted(secoes)} nao deixou nenhum chunk "
                f"(distribuicao real: {contagem})"
            )
        recorte_secoes = {
            "secoes": sorted(secoes),
            "criterio": criterio,
            "chunks_antes": antes,
            "chunks_depois": len(chunks),
            "fracao_mantida": round(len(chunks) / antes, 4),
            "distribuicao": contagem,
        }
        (log or print)(
            f"  [{strategy}] secoes {sorted(secoes)}: {antes:,} -> {len(chunks):,} chunks "
            f"({len(chunks)/antes:.1%})"
        )

    # Controle do recorte por secao: um indice do MESMO tamanho, mas sorteado.
    # Se este tambem melhorar, o achado e sobre o tamanho do indice e nao sobre
    # a estrutura do acordao.
    controle_amostra: dict | None = None
    if amostra is not None or amostra_igual_a:
        antes = len(chunks)
        # `--amostra-igual-a` casa o tamanho do indice com o que o recorte por
        # secao produziria NESTA estrategia. A fracao equivalente varia de 28%
        # (fixed_512_256) a 34% (structural_pred): passar um numero unico na
        # linha de comando daria um controle desalinhado justamente onde a
        # comparacao precisa ser exata.
        if amostra_igual_a:
            alvo, _ = secoes_mod.filtrar(chunks, amostra_igual_a, spans_por_doc or {})
            fracao = len(alvo) / antes
        else:
            fracao = amostra
        chunks = secoes_mod.amostra_aleatoria(chunks, fracao, seed=amostra_seed)
        controle_amostra = {
            "fracao": round(fracao, 6), "seed": amostra_seed,
            "igual_a_secoes": sorted(amostra_igual_a) if amostra_igual_a else None,
            "chunks_antes": antes, "chunks_depois": len(chunks),
        }
        (log or print)(
            f"  [{strategy}] amostra aleatoria {fracao:.4f} (seed {amostra_seed}"
            + (f", igualando {sorted(amostra_igual_a)}" if amostra_igual_a else "")
            + f"): {antes:,} -> {len(chunks):,} chunks"
        )

    peso_do_chunk: dict[str, float] = {}
    if pesos:
        peso_do_chunk = secoes_mod.pesos_por_chunk(chunks, pesos, spans_por_doc or {})
        (log or print)(
            f"  [{strategy}] pesos {pesos}: {len(peso_do_chunk):,} chunks com peso != 1"
        )

    index = build_index(retriever, chunks, models_cfg, embedder)

    # O nome do retriever no run carrega o modelo denso usado: sem isso, rodar
    # dois embedders sobrescreveria o run do outro, silenciosamente.
    if retriever == "dense":
        nome_embedder = embedder or models_cfg.get("dense", {}).get("default_embedder")
        retriever_tag = f"dense-{nome_embedder}"
        (log or print)(f"  [{strategy}] {index.describe()}")
        # Cache dos embeddings junto dos chunks da estratégia (contrato da
        # secao 2 do plano_implementacao.md). Com recorte por seção, os chunks
        # são um subconjunto: o cache é lido (e recortado) mas nunca escrito,
        # para não substituir o encode completo de 10 h por um parcial.
        index.build(chunks, cache_dir=processed_dir / strategy,
                    show_progress=False, log=log or print, bloco=bloco,
                    cache_somente_leitura=bool(secoes or controle_amostra))
    else:
        retriever_tag = retriever

    chunk_to_doc = dict(zip(index.chunk_ids, index.doc_ids))
    # Só os metadados de posição são necessários daqui em diante. Guardar os
    # objetos Chunk inteiros manteria vivos ~1,7 GB de texto da estratégia
    # fixed_512_256 durante a busca e a agregação, ao lado dos ~3,7 GB de
    # embeddings e da cópia que o FAISS faz.
    posicao = {c.chunk_id: (c.section, c.start, c.end) for c in chunks}
    n_chunks = len(chunks)
    del chunks
    agg_fn = AGGREGATIONS[aggregation]

    results = index.search_batch([q["text"] for q in queries], top_k=top_chunks)

    # O nome do run carrega TODA variante que muda o número: agregação, corte
    # por seção e ponderação. Dois runs da mesma estratégia e retriever com
    # recortes diferentes gravariam no mesmo arquivo, e o segundo apagaria o
    # primeiro sem aviso — que é o mesmo motivo de o modelo denso já estar no
    # nome.
    suffix = "" if aggregation == "max_pooling" else f"__{aggregation}"
    if secoes:
        suffix += f"__sec-{secoes_mod.rotulo_secoes(secoes)}"
        if criterio != "maioria":
            suffix += f"__crit-{criterio}"
    if pesos:
        suffix += f"__peso-{secoes_mod.rotulo_pesos(pesos)}"
    if controle_amostra:
        suffix += f"__amostra-{controle_amostra['fracao']:.4f}s{amostra_seed}"
    run_name = f"{strategy}__{retriever_tag}{suffix}"

    ranked: dict[str, list[tuple[str, float]]] = {}
    # Qual CHUNK deu o score de cada documento? É o que permite depois dizer de
    # qual macro-seção do acórdão veio o trecho que fez o documento ser
    # recuperado (`analysis.slice_by_section`) — inclusive nas baselines, que
    # não carregam rótulo de seção, mas carregam offset.
    vencedores: dict[str, dict[str, tuple[str, float]]] = {}
    for q, hits in zip(queries, results):
        # A ponderação por seção entra AQUI, entre a busca e a agregação: o
        # score do chunk é multiplicado pelo peso da sua seção, e é o valor
        # ponderado que disputa o max-pooling. Assim um trecho do relatório só
        # ganha o documento se vencer mesmo depois do desconto.
        #
        # Limitação a declarar: o peso é aplicado DEPOIS do corte em
        # `top_chunks`. Um chunk de peso alto que não entrou nos 2.000
        # primeiros por score bruto continua de fora. Com 2.000 chunks por
        # consulta e pesos que só descontam, o efeito é pequeno — mas é uma
        # aproximação, e não uma reordenação exata do índice inteiro.
        if peso_do_chunk:
            scored = [
                (cid, chunk_to_doc[cid], score * peso_do_chunk.get(cid, 1.0))
                for cid, score in hits
            ]
        else:
            scored = [(cid, chunk_to_doc[cid], score) for cid, score in hits]
        doc_scores = agg_fn(scored)
        ranked[q["query_id"]] = sorted(doc_scores.items(), key=lambda kv: -kv[1])[:top_docs]
        melhor: dict[str, tuple[str, float]] = {}
        for cid, doc_id, score in scored:
            if doc_id not in melhor or score > melhor[doc_id][1]:
                melhor[doc_id] = (cid, score)
        vencedores[q["query_id"]] = melhor

    n_lines = write_trec_run(runs_dir / f"{run_name}.trec", ranked, run_name)
    write_chunks_top(runs_dir / f"{run_name}__chunks.jsonl", ranked, vencedores,
                     posicao, run_name)

    info = {
        "run": run_name,
        "n_chunks": n_chunks,
        "n_queries": len(queries),
        "n_linhas_run": n_lines,
        "segundos": round(time.time() - t0, 1),
    }
    if recorte_secoes:
        info["recorte_secoes"] = recorte_secoes
    if pesos:
        info["pesos"] = {"por_secao": pesos, "n_chunks_ponderados": len(peso_do_chunk)}
    if controle_amostra:
        info["controle_amostra"] = controle_amostra
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera TREC runs por estrategia x retriever.")
    parser.add_argument("--strategy", nargs="+", default=["all"],
                        help="Estrategias na ORDEM de execucao, ou 'all'. A ordem importa "
                             "numa rodada longa: o que roda primeiro e o que estara pronto "
                             "se algo interromper.")
    parser.add_argument("--retriever", default="bm25", choices=["bm25", "dense", "all"])
    parser.add_argument("--embedder", default=None, help="Nome em models.yaml (so para dense).")
    parser.add_argument("--aggregation", default="max_pooling", choices=list(AGGREGATIONS))
    parser.add_argument("--secoes", default=None, metavar="LISTA",
                        help="F6 — indexa so estas macro-secoes do acordao. Aceita a forma "
                             "positiva ('ementa,fundamentacao,dispositivo') ou a negativa "
                             "('sem:relatorio', ou '--secoes=-relatorio' colado, que o "
                             "argparse senao le como opcao). "
                             "Vale para as cinco estrategias: nas fixas/recursiva a secao "
                             "vem do offset do chunk contra os spans do documento.")
    parser.add_argument("--pesos", default=None, metavar="LISTA",
                        help="F6 — em vez de cortar, pondera: 'relatorio=0.5' multiplica o "
                             "score dos chunks do relatorio antes da agregacao. Preserva o "
                             "recall que o corte binario sacrifica.")
    parser.add_argument("--amostra", type=float, default=None, metavar="FRACAO",
                        help="F6, CONTROLE — mantem uma fracao aleatoria dos chunks, em vez "
                             "de recortar por secao. Serve para responder se o ganho do "
                             "recorte vem da estrutura do acordao ou so de um indice menor.")
    parser.add_argument("--amostra-igual-a", default=None, metavar="LISTA",
                        help="F6, CONTROLE PAREADO — sorteia tantos chunks quantos o recorte "
                             "por estas secoes deixaria, em cada estrategia. E o controle "
                             "exato: mesmo tamanho de indice, sem respeitar a estrutura.")
    parser.add_argument("--amostra-seed", type=int, default=42)
    parser.add_argument("--secoes-criterio", default="maioria", choices=list(secoes_mod.CRITERIOS),
                        help="F7 — como decidir se um chunk e da secao: 'maioria' (F6) ou 'toca' "
                             "(qualquer trecho de uma secao mantida basta).")
    parser.add_argument("--corpus", type=Path, default=INTERIM_DIR / "corpus_docs.jsonl",
                        help="So usado por --secoes/--pesos, para ler os spans do documento.")
    parser.add_argument("--top-chunks", type=int, default=2000)
    parser.add_argument("--bloco", type=int, default=25_000,
                        help="Chunks por bloco de checkpoint no encode denso.")
    parser.add_argument("--max-horas", type=float, default=None,
                        help="Orcamento de tempo: nao INICIA uma estrategia nova depois "
                             "disso. O que ficar de fora roda depois reaproveitando o "
                             "cache, sem reencodar nada.")
    parser.add_argument("--top-docs", type=int, default=1000)
    parser.add_argument("--limit-queries", type=int, default=None, help="Smoke test.")
    parser.add_argument("--queries", type=Path, default=INTERIM_DIR / "queries.jsonl")
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--runs-dir", type=Path, default=None,
                        help="Se omitido, cria results/experiments/<data-hora>_<rotulo>/runs/.")
    parser.add_argument("--label", default=None, help="Rótulo da rodada (nome da pasta).")
    args = parser.parse_args()

    models_cfg = load_models_config()
    queries = load_queries(args.queries, args.limit_queries)
    if not queries:
        raise SystemExit(f"nenhuma consulta lida de {args.queries}")

    # F6 — recorte/ponderação por seção. Os spans só são lidos se alguma das
    # duas opções foi pedida: `load_gold_spans` varre um corpus_docs.jsonl de
    # 780 MB na primeira vez, e uma rodada normal não precisa disso.
    try:
        secoes = secoes_mod.parse_secoes(args.secoes) if args.secoes else None
        pesos = secoes_mod.parse_pesos(args.pesos) if args.pesos else None
        amostra_igual_a = (
            secoes_mod.parse_secoes(args.amostra_igual_a) if args.amostra_igual_a else None
        )
    except ValueError as e:
        raise SystemExit(f"--secoes/--pesos/--amostra-igual-a: {e}") from None
    if secoes and (amostra_igual_a or args.amostra):
        raise SystemExit(
            "--secoes com --amostra*: o controle aleatorio SUBSTITUI o recorte por secao, "
            "nao se soma a ele. Rode as duas condicoes em rodadas separadas."
        )
    if secoes and pesos:
        raise SystemExit(
            "--secoes e --pesos juntos medem duas intervencoes ao mesmo tempo e "
            "nenhuma das duas ficaria interpretavel. Rode uma de cada vez."
        )
    spans_por_doc: dict[str, list[dict]] = {}
    if secoes or pesos or amostra_igual_a:
        from .evaluate import load_gold_spans

        if not args.corpus.exists():
            raise SystemExit(f"--secoes/--pesos precisam de {args.corpus} (rode src.ingest)")
        spans_por_doc = load_gold_spans(args.corpus)
        print(f"spans de {len(spans_por_doc):,} documentos", flush=True)

    if args.strategy == ["all"]:
        # Ordem deliberada: as estrategias estruturais primeiro, porque sao as
        # que respondem a pergunta de pesquisa; as fixas, mais caras, por
        # ultimo. Numa rodada de ~10 h, se algo interromper, o que ja terminou
        # e o que mais importa.
        disponiveis = {p.name for p in args.processed_dir.iterdir() if p.is_dir()}
        preferencia = ["structural_gold", "structural_pred", "recursive_default",
                       "fixed_1024_512", "fixed_512_256"]
        strategies = [e for e in preferencia if e in disponiveis]
        strategies += sorted(disponiveis - set(strategies))
        if not strategies:
            raise SystemExit(
                f"nenhuma estrategia em {args.processed_dir} — rode "
                "`python -m src.chunkers.run` antes"
            )
    else:
        strategies = list(args.strategy)
        faltando = [e for e in strategies if not (args.processed_dir / e).is_dir()]
        if faltando:
            raise SystemExit(f"estrategia(s) sem chunks gerados: {faltando}")

    retrievers = ["bm25", "dense"] if args.retriever == "all" else [args.retriever]

    rotulo = args.label or _rotulo_automatico(args, retrievers, models_cfg)
    config = {
        "estrategias": strategies,
        "retrievers": retrievers,
        "embedder": args.embedder or models_cfg.get("dense", {}).get("default_embedder"),
        "agregacao": args.aggregation,
        "top_chunks": args.top_chunks,
        "top_docs": args.top_docs,
        "n_queries": len(queries),
        "limite_queries": args.limit_queries,
        "corpus": str(args.queries),
        "secoes": sorted(secoes) if secoes else None,
        "pesos_por_secao": pesos,
        "amostra_aleatoria": args.amostra,
        "amostra_igual_a": sorted(amostra_igual_a) if amostra_igual_a else None,
        "amostra_seed": args.amostra_seed if (args.amostra or amostra_igual_a) else None,
    }
    if "dense" in retrievers:
        nome = config["embedder"]
        cfg_emb = next((e for e in models_cfg["embedders"] if e["name"] == nome), {})
        config["modelo_denso"] = {k: cfg_emb.get(k) for k in
                                  ("hf_id", "max_seq_length", "batch_size", "dtype")}

    with Experimento(rotulo, config=config) as exp:
        runs_dir = args.runs_dir or exp.runs_dir
        inicio = time.time()
        pulados: list[str] = []
        taxa_chunks_s: float | None = None
        for retriever in retrievers:
            for strategy in strategies:
                # Orçamento de tempo: numa rodada noturna, é melhor terminar 3
                # estratégias e ter resultado do que começar a quarta e ser
                # interrompido no meio. O que ficar de fora roda depois e
                # reaproveita o cache — nada é reencodado.
                #
                # A decisão usa a duração ESTIMADA da próxima estratégia, não
                # só o tempo já decorrido: começar às 4h55 uma etapa de 2h30
                # estouraria um orçamento de 5h em metade do tempo de novo.
                # A estimativa vem da taxa medida nas estratégias anteriores
                # desta mesma rodada — nada de constante chutada.
                #
                # `is not None`, e não um teste de verdade: `--max-horas 0` é
                # falsy e desligaria silenciosamente o próprio orçamento.
                if args.max_horas is not None:
                    decorrido = (time.time() - inicio) / 3600
                    estimado = _estimar_horas(strategy, args.processed_dir, taxa_chunks_s)
                    if decorrido + estimado > args.max_horas:
                        pulados.append(f"{strategy}__{retriever}")
                        exp.log(
                            f"pulando {strategy}__{retriever}: estimados {estimado:.1f} h "
                            f"nao cabem no orcamento ({decorrido:.1f}/{args.max_horas} h usados)"
                        )
                        continue
                info = run_one(
                    strategy,
                    retriever,
                    queries,
                    models_cfg,
                    top_chunks=args.top_chunks,
                    top_docs=args.top_docs,
                    aggregation=args.aggregation,
                    embedder=args.embedder,
                    processed_dir=args.processed_dir,
                    runs_dir=runs_dir,
                    log=exp.log,
                    bloco=args.bloco,
                    secoes=secoes,
                    pesos=pesos,
                    spans_por_doc=spans_por_doc,
                    amostra=args.amostra,
                    amostra_seed=args.amostra_seed,
                    amostra_igual_a=amostra_igual_a,
                    criterio=args.secoes_criterio,
                )
                if info["segundos"] > 0:
                    taxa_chunks_s = info["n_chunks"] / info["segundos"]
                exp.registrar(info["run"], info)
                exp.log(
                    f"{info['run']}: {info['n_chunks']:,} chunks, "
                    f"{info['n_linhas_run']:,} linhas, {info['segundos']}s"
                    f"  [decorrido {(time.time()-inicio)/3600:.1f} h]"
                )

        if pulados:
            exp.manifest["pulados_por_tempo"] = pulados
            exp.log(f"orcamento de {args.max_horas} h atingido; nao iniciados: {pulados}")
            exp.log("rode o mesmo comando depois: o cache evita reencodar o que ja foi feito")


def _contar_chunks(strategy: str, processed_dir: Path) -> int:
    """Conta as linhas do chunks.jsonl sem desserializar o JSON — precisa saber
    o tamanho da etapa antes de decidir se ela cabe no orçamento."""
    caminho = processed_dir / strategy / "chunks.jsonl"
    if not caminho.is_file():
        return 0
    with caminho.open("rb") as f:
        return sum(1 for _ in f)


def _estimar_horas(strategy: str, processed_dir: Path, taxa_chunks_s: float | None) -> float:
    """Duração estimada da estratégia, pela taxa medida nas anteriores.

    Sem nenhuma etapa concluída ainda (a primeira da rodada), devolve 0: não há
    base para estimar, e recusar a primeira etapa deixaria a rodada sem
    nenhum resultado — que é pior do que estourar o orçamento.
    """
    if not taxa_chunks_s:
        return 0.0
    return _contar_chunks(strategy, processed_dir) / taxa_chunks_s / 3600


def _rotulo_automatico(args, retrievers, models_cfg) -> str:
    """Nome legível da pasta: diz o retriever, o modelo e se foi smoke test."""
    partes = ["-".join(retrievers)]
    if "dense" in retrievers:
        partes.append(args.embedder or models_cfg.get("dense", {}).get("default_embedder", ""))
    if args.strategy != ["all"]:
        partes.append("-".join(args.strategy))
    if args.limit_queries:
        partes.append(f"smoke{args.limit_queries}q")
    if args.aggregation != "max_pooling":
        partes.append(args.aggregation)
    # A variante de seção precisa aparecer no NOME DA PASTA, não só no do run:
    # é assim que o INDICE.md mostra de relance o que cada rodada testou.
    if getattr(args, "secoes", None):
        partes.append("sec-" + secoes_mod.rotulo_secoes(secoes_mod.parse_secoes(args.secoes)))
        if getattr(args, "secoes_criterio", "maioria") != "maioria":
            partes.append("crit-" + args.secoes_criterio)
    if getattr(args, "pesos", None):
        partes.append("peso-" + secoes_mod.rotulo_pesos(secoes_mod.parse_pesos(args.pesos)))
    if getattr(args, "amostra", None) is not None:
        partes.append(f"amostra{args.amostra:.4f}")
    if getattr(args, "amostra_igual_a", None):
        partes.append("amostra-igual-" + secoes_mod.rotulo_secoes(
            secoes_mod.parse_secoes(args.amostra_igual_a)))
    return "_".join(p for p in partes if p)


if __name__ == "__main__":
    main()
