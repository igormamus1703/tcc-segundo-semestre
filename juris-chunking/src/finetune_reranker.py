"""F7 — Fine-tune do reranker no domínio, com supervisão em nível de passagem.

O `bge-reranker-v2-m3` usado sem ajuste (zero-shot) não superou a melhor
configuração de primeiro estágio em nenhuma das duas coleções (H6 falhou). É
um cross-encoder multilíngue genérico: nunca viu um acórdão do TCU.

O JUÁ-Juris permite algo raro em RI jurídica: **supervisão de passagem**. Para
cada consulta de treino, sabemos não só qual acórdão é relevante, mas *em que
trecho* dele está o excerto que originou o enunciado (`src/jua.py` o localiza).
O exemplo de treino fica:

- **positivo:** o chunk do acórdão relevante que contém o excerto;
- **negativos difíceis:** os chunks que *venceram* os acórdãos errados mais
  bem colocados pelo BM25 para aquela consulta (o `__chunks.jsonl` do run).

Perda listwise (entropia cruzada sobre o grupo 1 positivo + k negativos), que
é como os rerankers BGE são treinados. **LoRA** (Hu et al. 2021) em vez de
fine-tune completo: AdamW sobre 568M parâmetros não cabe em 8 GB; com LoRA, só
~1% dos parâmetros treina, e o modelo base fica congelado.

Tudo sai do split de **treino** do JUÁ. O modelo ajustado é avaliado com o
mesmo `src.rerank`, nas mesmas candidatas, contra o zero-shot.
"""

from __future__ import annotations

import csv
import json
import math
import random
import time
from pathlib import Path

from .ingest import INTERIM_DIR, JURISTCU_DOCS, normalize_html
from .jua import ANCORA, PREFIXO, localizar, mapa_dobrado

csv.field_size_limit(2**28)


# --- montagem dos exemplos (puro) ---------------------------------------------

def chunk_que_contem(chunks_do_doc: list[dict], pos: int) -> dict | None:
    """O chunk cujo intervalo contém o MEIO da âncora localizada.

    O meio, e não o início: com janelas sobrepostas (512/256), o início da
    âncora pode cair no fim de um chunk que só tem os primeiros caracteres do
    excerto. Entre os que contêm o meio, o de início mais próximo do excerto.
    """
    meio = pos + ANCORA // 2
    cands = [c for c in chunks_do_doc if c["start"] <= meio < c["end"]]
    if not cands:
        return None
    return max(cands, key=lambda c: c["start"] if c["start"] <= pos else -1)


def grupo(qid: str, relevante: str, positivo: str, vencedores: list[dict], k: int
          ) -> list[str] | None:
    """[positivo, k negativos]: os vencedores dos acórdãos ERRADOS, em ordem de rank."""
    negativos = []
    for r in sorted(vencedores, key=lambda r: r["rank"]):
        if r["doc_id"] != relevante and r["chunk_id"] != positivo:
            negativos.append(r["chunk_id"])
        if len(negativos) == k:
            return [positivo, *negativos]
    return None


# --- CLI -----------------------------------------------------------------------

def main() -> None:
    import argparse

    import numpy as np
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    from .chunkers.run import PROCESSED_DIR
    from .experiment import Experimento, ultima_rodada
    from .rerank import textos_dos_chunks

    p = argparse.ArgumentParser(description="Fine-tune LoRA do reranker no treino do JUA-Juris.")
    p.add_argument("--base", default="BAAI/bge-reranker-v2-m3")
    p.add_argument("--estrategia", default="fixed_512_256")
    p.add_argument("--rodada-negativos", default="h8_tr_bm25",
                   help="Rotulo da rodada BM25 sobre as consultas de treino (com __chunks.jsonl).")
    p.add_argument("--queries", type=Path, default=INTERIM_DIR / "jua" / "queries_train_amostra.jsonl")
    p.add_argument("--qrels", type=Path, default=INTERIM_DIR / "jua" / "qrels_train_amostra.trec")
    p.add_argument("--negativos", type=int, default=7)
    p.add_argument("--consultas-por-passo", type=int, default=2)
    p.add_argument("--acumular", type=int, default=4)
    p.add_argument("--epocas", type=int, default=1)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--max-length", type=int, default=512)
    p.add_argument("--validacao", type=int, default=300)
    p.add_argument("--saida", type=Path, default=Path(__file__).resolve().parent.parent
                   / "data" / "models" / "bge-reranker-v2-m3-jua-lora")
    p.add_argument("--label", default="f7_finetune_reranker")
    args = p.parse_args()

    torch.manual_seed(42)
    random.seed(42)
    with Experimento(args.label, config={k: str(v) for k, v in vars(args).items()}) as exp:
        # 1. exemplos -----------------------------------------------------------
        textos_q, relevante = {}, {}
        with args.queries.open(encoding="utf-8") as f:
            for l in f:
                r = json.loads(l)
                textos_q[r["query_id"]] = r["text"]
        with args.qrels.open(encoding="utf-8") as f:
            for l in f:
                q, _z, d, _s = l.split()
                relevante[q] = d
        excerto = {}
        with JURISTCU_DOCS.open(encoding="utf-8", newline="", errors="replace") as f:
            for row in csv.DictReader(f):
                excerto[f"jua-{row['KEY']}"] = normalize_html(row.get("EXCERTO"))

        docs_rel = set(relevante.values())
        texto_doc = {}
        with (INTERIM_DIR / "corpus_docs.jsonl").open(encoding="utf-8") as f:
            for l in f:
                r = json.loads(l)
                if r["doc_id"] in docs_rel:
                    texto_doc[r["doc_id"]] = r["text"]
        chunks_doc: dict[str, list[dict]] = {}
        with (PROCESSED_DIR / args.estrategia / "chunks.jsonl").open(encoding="utf-8") as f:
            for l in f:
                inicio = l[:300]
                doc = inicio.split('"doc_id": "', 1)[1].split('"', 1)[0]
                if doc in docs_rel:
                    r = json.loads(l)
                    chunks_doc.setdefault(doc, []).append(
                        {"chunk_id": r["chunk_id"], "start": r["start"], "end": r["end"]})

        rodada = ultima_rodada(args.rodada_negativos)
        sidecar = next(p for p in (rodada / "runs").glob("*__chunks.jsonl"))
        vencedores: dict[str, list[dict]] = {}
        with sidecar.open(encoding="utf-8") as f:
            for l in f:
                r = json.loads(l)
                vencedores.setdefault(r["query_id"], []).append(r)

        grupos, sem_local, sem_neg = [], 0, 0
        for qid in sorted(textos_q):
            d = relevante.get(qid)
            if d not in texto_doc:
                continue
            pos = localizar(excerto.get(qid, ""), *mapa_dobrado(texto_doc[d]))
            c = chunk_que_contem(chunks_doc.get(d, []), pos) if pos is not None else None
            if c is None:
                sem_local += 1
                continue
            g = grupo(qid, d, c["chunk_id"], vencedores.get(qid, []), args.negativos)
            if g is None:
                sem_neg += 1
                continue
            grupos.append((qid, g))
        random.shuffle(grupos)
        val, treino = grupos[:args.validacao], grupos[args.validacao:]
        exp.log(f"{len(grupos)} grupos ({len(treino)} treino, {len(val)} validacao); "
                f"{sem_local} sem excerto localizado, {sem_neg} sem negativos suficientes")
        ids = {c for _q, g in grupos for c in g}
        texto_chunk = textos_dos_chunks(PROCESSED_DIR / args.estrategia / "chunks.jsonl", ids)

        # 2. modelo -------------------------------------------------------------
        tok = AutoTokenizer.from_pretrained(args.base)
        modelo = AutoModelForSequenceClassification.from_pretrained(args.base, num_labels=1)
        modelo.gradient_checkpointing_enable()
        lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                          target_modules=["query", "key", "value", "dense"],
                          modules_to_save=["classifier"])
        modelo = get_peft_model(modelo, lora)
        treinaveis = sum(p.numel() for p in modelo.parameters() if p.requires_grad)
        total = sum(p.numel() for p in modelo.parameters())
        exp.log(f"LoRA: {treinaveis:,} de {total:,} parametros treinaveis ({treinaveis / total:.2%})")
        disp = "cuda"
        modelo.to(disp)

        def logits(lote: list[tuple[str, list[str]]]) -> torch.Tensor:
            pares = [(textos_q[q], texto_chunk[c]) for q, g in lote for c in g]
            # "longest_first", e não "only_second": há enunciados mais longos que
            # a janela inteira, e cortar só a passagem aborta o treino no meio
            # (aconteceu no passo ~200 da primeira tentativa).
            enc = tok([a for a, _ in pares], [b for _, b in pares], truncation="longest_first",
                      max_length=args.max_length, padding=True, return_tensors="pt").to(disp)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                out = modelo(**enc).logits.view(len(lote), -1)
            return out.float()

        def avaliar() -> dict:
            modelo.eval()
            acertos, perdas = 0, []
            with torch.no_grad():
                for i in range(0, len(val), 8):
                    lg = logits(val[i:i + 8])
                    perdas.append(torch.nn.functional.cross_entropy(
                        lg, torch.zeros(len(lg), dtype=torch.long, device=disp)).item())
                    acertos += int((lg.argmax(dim=1) == 0).sum())
            modelo.train()
            return {"perda_val": float(np.mean(perdas)), "acerto_top1_val": acertos / len(val)}

        # 3. treino -------------------------------------------------------------
        otim = torch.optim.AdamW([p for p in modelo.parameters() if p.requires_grad], lr=args.lr,
                                 weight_decay=0.01)
        passos_por_epoca = math.ceil(len(treino) / args.consultas_por_passo)
        total_otim = math.ceil(passos_por_epoca * args.epocas / args.acumular)
        aquec = max(1, int(0.05 * total_otim))
        agenda = torch.optim.lr_scheduler.LambdaLR(
            otim, lambda s: min(1.0, (s + 1) / aquec) * max(0.0, (total_otim - s) / max(1, total_otim - aquec)))
        curva = [{"passo_otim": 0, "perda_treino": None, **avaliar()}]
        exp.log(f"antes do treino: {curva[0]}")
        modelo.train()
        t0, passo, acum = time.time(), 0, []
        for epoca in range(args.epocas):
            random.shuffle(treino)
            for i in range(0, len(treino), args.consultas_por_passo):
                lote = treino[i:i + args.consultas_por_passo]
                lg = logits(lote)
                perda = torch.nn.functional.cross_entropy(
                    lg, torch.zeros(len(lote), dtype=torch.long, device=disp)) / args.acumular
                perda.backward()
                acum.append(perda.item() * args.acumular)
                if (i // args.consultas_por_passo + 1) % args.acumular == 0:
                    torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
                    otim.step()
                    agenda.step()
                    otim.zero_grad()
                    passo += 1
                    if passo % 100 == 0:
                        # checkpoint do adaptador: uma queda não custa o treino inteiro
                        modelo.save_pretrained(args.saida.parent / (args.saida.name + "-ckpt"))
                    if passo % 50 == 0 or passo == total_otim:
                        ponto = {"passo_otim": passo, "perda_treino": float(np.mean(acum)), **avaliar()}
                        curva.append(ponto)
                        acum = []
                        exp.log(f"epoca {epoca} passo {passo}/{total_otim} {ponto} "
                                f"[{(time.time() - t0) / 60:.1f} min]")

        with (exp.tables_dir / "curva.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(curva[0].keys()))
            w.writeheader()
            w.writerows(curva)

        # 4. funde o LoRA no modelo e salva um cross-encoder comum ----------------
        fundido = modelo.merge_and_unload()
        args.saida.mkdir(parents=True, exist_ok=True)
        fundido.save_pretrained(args.saida)
        tok.save_pretrained(args.saida)
        exp.registrar("modelo", {"saida": str(args.saida), "curva": curva[-1]})
        exp.log(f"modelo salvo em {args.saida}")


if __name__ == "__main__":
    main()
