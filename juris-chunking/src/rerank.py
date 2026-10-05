"""F7 — Reranking com cross-encoder: o recorte por seção sobrevive a um modelo forte?

Reranking com cross-encoder é a intervenção que mais rende em RI desde
Nogueira & Cho (2019): o modelo lê consulta e passagem *juntas*, em vez de
comparar dois vetores calculados separadamente. A pergunta da F7 não é "o
reranker ajuda?" (quase sempre ajuda), é a que interessa ao TCC:

    **depois de um reranker forte, ainda importa QUAL parte do acórdão ele lê?**

Se o cross-encoder for bom o bastante para descontar sozinho o relatório, o
recorte por seção vira redundante e a contribuição da F6 encolhe para "um
truque de primeiro estágio". Se não for, o recorte é complementar a modelos
fortes, e o achado vale mais.

Desenho (documento longo → passagens → max, o MaxP de Dai & Callan 2019):

- **candidatos:** os `top` primeiros documentos de um run de primeiro estágio;
- **passagens de cada documento:** os chunks que *venceram* aquele documento
  nos runs-fonte (o `__chunks.jsonl` que todo run grava). Com quatro fontes
  (BM25 e denso, com e sem relatório), cada documento tem até quatro
  passagens, escolhidas por sinais diferentes;
- **score do documento:** o maior score do cross-encoder entre as passagens;
- **variantes**, com os MESMOS candidatos, para isolar o efeito do que se lê:
  `todas` (qualquer passagem) e `sem_relatorio` (descarta as passagens cujo
  offset cai no relatório).

Documento sem passagem nenhuma (nenhuma fonte o tinha no top-50) não pode ser
lido. Ele fica DEPOIS dos reranqueados, na ordem original, e é contado: se a
contagem for alta, o número do reranker está medindo cobertura, não leitura.

O score de cada par (consulta, chunk) é guardado num cache em disco com
checkpoint: a rodada do JUÁ-Juris são centenas de milhares de pares, e uma
queda no meio não pode custar o que já foi calculado.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable

from .analysis import section_of_span
from .fusion import Ranking, escrever_trec, ler_trec

Pontuador = Callable[[list[tuple[str, str]]], list[float]]


# --- lógica pura (testada sem GPU) ------------------------------------------

def passagens_por_documento(
    sidecars: dict[str, Path],
) -> dict[tuple[str, str], dict[str, dict]]:
    """{(qid, doc_id): {chunk_id: {"fontes": [...], "start": s, "end": e}}}.

    O mesmo chunk pode vencer o documento em mais de uma fonte (BM25 e denso
    concordando); ele é lido uma vez só, e as fontes ficam registradas.
    """
    out: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for fonte, path in sidecars.items():
        with path.open(encoding="utf-8") as f:
            for linha in f:
                r = json.loads(linha)
                chave = (r["query_id"], r["doc_id"])
                info = out[chave].setdefault(
                    r["chunk_id"], {"fontes": [], "start": r["start"], "end": r["end"]})
                info["fontes"].append(fonte)
    return dict(out)


def fora_do_relatorio(info: dict, spans: list[dict] | None) -> bool:
    """A passagem pode ser lida na variante `sem_relatorio`?

    Sem spans não há como saber a seção; a passagem é mantida (o mesmo
    critério conservador da ponderação na F6: na dúvida, compete).
    """
    if not spans:
        return True
    return section_of_span(info["start"], info["end"], spans) != "relatorio"


def reranquear(
    candidatos: Ranking,
    passagens: dict[tuple[str, str], dict[str, dict]],
    scores: dict[tuple[str, str], float],
    top: int,
    filtro: Callable[[str, dict], bool] | None = None,
    preservar: bool = False,
) -> tuple[Ranking, dict]:
    """Reordena os `top` primeiros de cada consulta pelo max do cross-encoder.

    `filtro(doc_id, info)` decide se uma passagem pode ser lida. Devolve o run
    reranqueado (os documentos além do `top` vêm depois, na ordem original) e
    contagens de cobertura.

    `preservar=True` separa dois efeitos que o filtro mistura: se NENHUMA
    passagem do documento passa no filtro, ele é lido mesmo assim, por todas.
    Sem isso, o filtro também *rebaixa* os documentos que só tinham passagem
    no relatório, e a variante mede "o que se lê" e "quem é rebaixado" juntos.
    """
    out: Ranking = {}
    lidos = sem_passagem = 0
    for qid, docs in candidatos.items():
        ordem = [d for d, _ in sorted(docs.items(), key=lambda kv: (-kv[1], kv[0]))]
        cabeca, cauda = ordem[:top], ordem[top:]
        com_nota: list[tuple[str, float]] = []
        sem_nota: list[str] = []
        for doc in cabeca:
            todas = [(cid, info) for cid, info in passagens.get((qid, doc), {}).items()
                     if (qid, cid) in scores]
            permitidas = [(c, i) for c, i in todas if filtro is None or filtro(doc, i)]
            if preservar and not permitidas:
                permitidas = todas
            notas = [scores[(qid, cid)] for cid, _ in permitidas]
            if notas:
                com_nota.append((doc, max(notas)))
            else:
                sem_nota.append(doc)
        lidos += len(com_nota)
        sem_passagem += len(sem_nota)
        com_nota.sort(key=lambda kv: (-kv[1], kv[0]))
        # Scores sintéticos decrescentes: o que importa no TREC é a ordem, e
        # misturar a escala do cross-encoder com a do primeiro estágio na
        # mesma lista seria comparar coisas incomparáveis.
        final = [d for d, _ in com_nota] + sem_nota + cauda
        n = len(final)
        out[qid] = {d: float(n - i) for i, d in enumerate(final)}
    total = lidos + sem_passagem
    return out, {
        "documentos_lidos": lidos,
        "documentos_sem_passagem": sem_passagem,
        "fracao_sem_passagem": round(sem_passagem / total, 4) if total else 0.0,
    }


def pares_pendentes(
    candidatos: Ranking,
    passagens: dict[tuple[str, str], dict[str, dict]],
    top: int,
    ja_pontuados: set[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Pares (qid, chunk_id) que ainda precisam passar pelo cross-encoder."""
    pend: set[tuple[str, str]] = set()
    for qid, docs in candidatos.items():
        cabeca = sorted(docs.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
        for doc, _ in cabeca:
            for cid in passagens.get((qid, doc), {}):
                if (qid, cid) not in ja_pontuados:
                    pend.add((qid, cid))
    return sorted(pend)


# --- cache em disco ----------------------------------------------------------

def ler_cache(path: Path) -> dict[tuple[str, str], float]:
    scores: dict[tuple[str, str], float] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for linha in f:
                qid, cid, s = linha.rstrip("\n").split("\t")
                scores[(qid, cid)] = float(s)
    return scores


def pontuar_com_cache(
    pares: list[tuple[str, str]],
    textos_consulta: dict[str, str],
    textos_chunk: dict[str, str],
    pontuador: Pontuador,
    cache: Path,
    bloco: int = 2048,
    log: Callable[[str], None] = print,
) -> dict[tuple[str, str], float]:
    """Pontua `pares` em blocos, anexando cada bloco ao cache antes do próximo.

    Os pares são ordenados pelo tamanho do texto: lotes de tamanho parecido
    desperdiçam menos padding na GPU.
    """
    cache.parent.mkdir(parents=True, exist_ok=True)
    pares = sorted(pares, key=lambda p: len(textos_chunk[p[1]]))
    novos: dict[tuple[str, str], float] = {}
    t0 = time.time()
    with cache.open("a", encoding="utf-8") as f:
        for i in range(0, len(pares), bloco):
            lote = pares[i:i + bloco]
            notas = pontuador([(textos_consulta[q], textos_chunk[c]) for q, c in lote])
            for (q, c), s in zip(lote, notas):
                novos[(q, c)] = float(s)
                f.write(f"{q}\t{c}\t{float(s):.6f}\n")
            f.flush()
            feitos = min(i + bloco, len(pares))
            ritmo = feitos / max(time.time() - t0, 1e-9)
            log(f"  {feitos:,}/{len(pares):,} pares ({ritmo:.0f}/s, "
                f"faltam ~{(len(pares) - feitos) / max(ritmo, 1e-9) / 60:.0f} min)")
    return novos


def textos_dos_chunks(chunks_jsonl: Path, ids: Iterable[str]) -> dict[str, str]:
    """Lê do `chunks.jsonl` (centenas de milhares de linhas) só os ids pedidos."""
    faltam = set(ids)
    textos: dict[str, str] = {}
    with chunks_jsonl.open(encoding="utf-8") as f:
        for linha in f:
            # filtro barato antes do json.loads: o id vem no começo da linha
            inicio = linha[:300]
            if '"chunk_id": "' in inicio:
                cid = inicio.split('"chunk_id": "', 1)[1].split('"', 1)[0]
                if cid not in faltam:
                    continue
            r = json.loads(linha)
            if r["chunk_id"] in faltam:
                textos[r["chunk_id"]] = r["text"]
    if len(textos) != len(faltam):
        raise SystemExit(f"{len(faltam) - len(textos)} chunks pedidos nao estao em {chunks_jsonl}")
    return textos


def cross_encoder(modelo: str, max_length: int, batch: int) -> Pontuador:
    import torch
    from sentence_transformers import CrossEncoder

    ce = CrossEncoder(
        modelo, max_length=max_length,
        device="cuda" if torch.cuda.is_available() else "cpu",
        model_kwargs={"torch_dtype": torch.float16} if torch.cuda.is_available() else {},
    )

    def pontuar(pares: list[tuple[str, str]]) -> list[float]:
        return [float(s) for s in ce.predict(pares, batch_size=batch, show_progress_bar=False)]

    return pontuar


# --- CLI --------------------------------------------------------------------

def main() -> None:
    import argparse

    from .experiment import Experimento
    from .chunkers.run import PROCESSED_DIR
    from .ingest import INTERIM_DIR

    parser = argparse.ArgumentParser(
        description="Reranqueia o top-N de um run com cross-encoder, lendo as passagens "
                    "que venceram cada documento nos runs-fonte.")
    parser.add_argument("--candidatos", type=Path, required=True, help="Run TREC de primeiro estagio.")
    parser.add_argument("--fontes", type=Path, nargs="+", required=True,
                        help="Arquivos __chunks.jsonl dos runs-fonte das passagens.")
    parser.add_argument("--estrategia", required=True, help="Estrategia de chunking dos runs.")
    parser.add_argument("--nome", required=True, help="Prefixo do run gravado, ex.: fusao4.")
    parser.add_argument("--variantes", nargs="+",
                        default=["todas", "sem_relatorio", "sem_relatorio_preserva"],
                        choices=["todas", "sem_relatorio", "sem_relatorio_preserva"])
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument("--modelo", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--max-length", type=int, default=1024,
                        help="O card do bge-reranker-v2-m3 recomenda 1024 (fine-tune).")
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--queries", type=Path, default=INTERIM_DIR / "queries.jsonl")
    parser.add_argument("--corpus", type=Path, default=INTERIM_DIR / "corpus_docs.jsonl")
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--cache", type=Path, required=True,
                        help="TSV de scores (qid, chunk_id) — compartilhado entre chamadas "
                             "sobre a MESMA colecao de consultas.")
    parser.add_argument("--label", default=None)
    args = parser.parse_args()

    textos_q = {}
    with args.queries.open(encoding="utf-8") as f:
        for linha in f:
            r = json.loads(linha)
            textos_q[r["query_id"]] = r["text"]

    candidatos = ler_trec(args.candidatos)
    fontes = {p.stem.removesuffix("__chunks"): p for p in args.fontes}
    passagens = passagens_por_documento(fontes)

    config = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    config["fontes"] = [str(p) for p in args.fontes]
    with Experimento(args.label or f"rerank_{args.nome}", config=config) as exp:
        scores = ler_cache(args.cache)
        pend = pares_pendentes(candidatos, passagens, args.top, set(scores))
        exp.log(f"{len(scores):,} pares no cache; {len(pend):,} a pontuar")
        if pend:
            textos_c = textos_dos_chunks(
                args.processed_dir / args.estrategia / "chunks.jsonl", {c for _, c in pend})
            pontuador = cross_encoder(args.modelo, args.max_length, args.batch)
            scores.update(pontuar_com_cache(pend, textos_q, textos_c, pontuador,
                                            args.cache, log=exp.log))

        spans: dict[str, list[dict]] = {}
        if any(v.startswith("sem_relatorio") for v in args.variantes):
            docs_usados = {d for (_q, d) in passagens}
            with args.corpus.open(encoding="utf-8") as f:
                for linha in f:
                    r = json.loads(linha)
                    if r["doc_id"] in docs_usados:
                        spans[r["doc_id"]] = r["gold_spans"]

        for variante in args.variantes:
            filtro = None if variante == "todas" else (
                lambda doc, info: fora_do_relatorio(info, spans.get(doc)))
            run, cobertura = reranquear(candidatos, passagens, scores, args.top, filtro,
                                        preservar=variante == "sem_relatorio_preserva")
            run_name = f"{args.estrategia}__rerank-{args.nome}-{variante}"
            escrever_trec(exp.runs_dir / f"{run_name}.trec", run, run_name)
            exp.registrar(run_name, {"variante": variante, "top": args.top, **cobertura})
            exp.log(f"{run_name}: {cobertura}")


if __name__ == "__main__":
    main()
