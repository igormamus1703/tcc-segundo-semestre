# Benchmark do encode denso e escolha do embedder

**Data:** 2026-09-06 · **Autor:** Leonardo Marques
**Hardware:** RTX 5060 (8 GB VRAM, Blackwell sm_120) · i5-13400 · 32 GB RAM · Windows 11
**Amostra:** chunks reais do corpus (`structural_gold`, amostragem espaçada)

## Por que este documento existe

A pergunta era simples — "quanto tempo leva o encode denso?" — mas a resposta
mudou três vezes, e cada mudança veio de uma medição que contradisse uma
estimativa. Está tudo aqui para que ninguém refaça o caminho.

| Momento | Estimativa | Como foi obtida |
|---|---|---|
| Inicial | ~24 h em CPU | chute de 25 chunks/s |
| Medido em CPU | **127 h** | benchmark real: 4,8 chunks/s |
| Medido em GPU (e5-base) | 2,1 h | 288 chunks/s — **mas com 37% de truncamento** |
| **Final (bge-m3, GPU)** | **10,1 h** | projeção ponderada por estratégia, **0% de truncamento** |

## 1. O problema que quase passou despercebido: truncamento desigual

O tokenizador do pipeline é o `tiktoken cl100k_base`, mas o modelo usa o seu
próprio (subword). Chunks de 1024 tokens tiktoken viram ~850 tokens de subword
— e o `multilingual-e5-base` só aceita **512**.

Medido sobre 500 chunks reais por estratégia:

| Estratégia | Mediana (tokens do modelo) | Chunks truncados | Conteúdo perdido |
|---|---|---|---|
| fixed_512_256 | 424 | **0,0%** | **0,0%** |
| fixed_1024_512 | 847 | 98,6% | **38,9%** |
| recursive_default | 787 | 96,6% | 33,4% |
| structural_gold | 840 | 87,2% | 36,8% |
| structural_pred | 843 | 88,0% | 37,5% |

**Isso invalidaria o experimento.** Não porque o truncamento é ruim em si, mas
porque ele é **desigual**: a `fixed_512_256` seria a única avaliada com 100% do
seu conteúdo, e as outras quatro perderiam ~37%. Qualquer vantagem dela no
resultado final seria artefato da janela do encoder, não da estratégia de
chunking.

É exatamente o erro que apontamos no BR-TaxQA-R (confundir tamanho de chunk com
estratégia) — teria sido irônico repeti-lo.

## 2. Candidatos testados

| Modelo | Params | Janela | Gate | Resultado |
|---|---|---|---|---|
| `intfloat/multilingual-e5-base` | 278M | 512 | não | 288 chunks/s, mas **37% de truncamento** ❌ |
| `Alibaba-NLP/gte-multilingual-base` | 305M | 8192 | não | **quebra**: `device-side assert` no CUDA ❌ |
| `google/embeddinggemma-300m` | 308M | 2048 | **sim** | `401 GatedRepoError` — exige `hf auth login` ⏳ |
| **`BAAI/bge-m3`** | 568M | 8192 | não | **47–102 chunks/s, 0% de truncamento** ✅ |

Sobre o `gte`: falha em fp16 **e** fp32, com janela 1024 **e** 512, com
`unpad_inputs=False` e `use_memory_efficient_attention=False`. O código remoto
(`trust_remote_code`) não sobrevive ao stack atual (torch 2.14, transformers
5.x, Blackwell). O assert é *sticky*: contamina o contexto CUDA e derruba tudo
que rodar depois no mesmo processo — por isso cada variante precisa de um
processo próprio para ser testada.

## 3. CPU vs GPU vs precisão

```
e5-base, chunks reais, batch 32
CPU  (10 threads torch)     4,8 chunks/s     127 h
GPU  fp32                    90,1 chunks/s     6,8 h     VRAM 1,64 G
GPU  fp16                   288,2 chunks/s     2,1 h     VRAM 0,84 G
```

**fp16 dá 3,2x sobre fp32 e 60x sobre a CPU**, com metade da VRAM. Batch maior
não ajuda (288 → 284 → 278 em 32/64/128): o gargalo é compute, não paralelismo.

## 4. Projeção final (BGE-M3, fp16, janela 1024, batch 32)

Medida **por estratégia**, porque o custo depende do comprimento e a
`fixed_512_256` tem chunks com metade dos tokens:

| Estratégia | Chunks | Tokens/chunk | chunks/s | Horas |
|---|---:|---:|---:|---:|
| fixed_512_256 | 907.914 | 423 | 101,7 | 2,48 |
| fixed_1024_512 | 450.786 | 842 | 46,9 | 2,67 |
| recursive_default | 270.070 | 770 | 48,1 | 1,56 |
| structural_gold | 286.689 | 773 | 46,9 | 1,70 |
| structural_pred | 285.308 | 770 | 47,0 | 1,68 |
| **Total** | **2.200.767** | | | **10,09 h** |

**Truncamento: 0,00% em todas as cinco.**

## 5. Otimizações testadas que NÃO funcionaram

Registradas para ninguém tentar de novo:

| Tentativa | Resultado | Por quê |
|---|---|---|
| **Deduplicar chunks** entre estratégias | **0,4%** de redundância | As estratégias recortam o mesmo corpus, mas os chunks quase nunca são byte-idênticos. `structural_gold` e `pred` concordam em 87% das *fronteiras*, o que não produz textos iguais |
| **`torch.compile(dynamic=True)`** | 0,99x | Sem ganho; comprimentos variáveis impedem a fusão de kernels valer a pena |
| **TF32 + `cudnn.benchmark`** | 1,00x | Irrelevante: já estamos em fp16, que não passa pelo caminho TF32 |
| **Batch 64 / 128** | 0,99x / 0,97x | A GPU já satura em batch 32; só cresce a VRAM |

### Onde o tempo realmente vai

```
encode completo   5,35 s  (47,8 chunks/s)
  tokenização (CPU)  0,32 s   5,9%
  forward (GPU)      5,39 s  100,7%
```

**A GPU é 100% do custo.** Descarta qualquer otimização do lado da CPU
(pré-tokenização, paralelismo de dataloader) — não há tempo de CPU para
recuperar.

## 6. Por que não dá para chegar a 2 h nesta GPU

Conta fechada: 1,46 bilhão de tokens × ~0,6 GFLOP/token (BGE-M3 é
XLM-RoBERTa **large**, 24 camadas × 1024) ≈ **876 PFLOPs**. A RTX 5060 entrega
~40 TFLOPS fp16 sustentados → ~6 h teóricas, 10 h reais (60% de utilização, o
que é normal para sequências de comprimento variável).

Para 2 h seria preciso um modelo **base** (12 camadas × 768), ~3,5x mais
barato. O `gte-multilingual-base` era exatamente esse perfil — e está quebrado.
O `embeddinggemma-300m` fica no meio do caminho (24 × 768) e deve dar ~5 h, mas
depende do login no Hugging Face.

**Conclusão: 10 h é o custo real da opção cientificamente correta nesta
máquina.** Cabe numa noite, e o cache `.npy` garante que só precisa ser pago
uma vez.

## 7. Comandos

```bash
# rodada completa do denso (cria results/experiments/<data-hora>_dense_bge_m3/)
cd juris-chunking
python -m src.run_experiments --strategy all --retriever dense

# depois, a avaliação (encontra a rodada mais recente sozinha)
python -m src.evaluate
```

Smoke test antes, para confirmar que a GPU está sendo usada:

```bash
python -m src.run_experiments --strategy structural_gold --retriever dense --limit-queries 5
```
