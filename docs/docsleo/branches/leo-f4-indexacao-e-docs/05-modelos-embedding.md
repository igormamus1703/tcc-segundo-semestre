# Escolha do embedder

**Data:** 2026-09-06 (revisto) · **Autor:** Leonardo Marques
**Decisão:** `BAAI/bge-m3` como default · **Status:** fechado

## O problema inicial

`configs/models.yaml` vinha com `hf_id: "PREENCHER"` no `pt_compact`,
bloqueando a F4. Havia também divergência entre os documentos: o
`plano_implementacao.md` §F4 mandava usar `intfloat/multilingual-e5-base`
como default, enquanto o `models.yaml` trazia `e5-large`.

Mas ao resolver isso apareceu um critério que **nenhum dos dois planos previa**
e que acabou dominando a escolha: **a janela de contexto**.

## O critério que decidiu: janela, não ranking

O tokenizador do pipeline é o `tiktoken cl100k_base`; o do modelo é outro.
Chunks de 1024 tokens tiktoken viram ~850 tokens de subword — e o
`multilingual-e5-base` só aceita **512**. Medido sobre 500 chunks reais por
estratégia:

| Estratégia | Mediana (tokens do modelo) | Truncados | Conteúdo perdido |
|---|---:|---:|---:|
| fixed_512_256 | 424 | **0,0%** | **0,0%** |
| fixed_1024_512 | 847 | 98,6% | **38,9%** |
| recursive_default | 787 | 96,6% | 33,4% |
| structural_gold | 840 | 87,2% | 36,8% |
| structural_pred | 843 | 88,0% | 37,5% |

**Isso invalidaria o experimento.** Não pelo truncamento em si, mas por ele ser
**desigual**: a `fixed_512_256` seria a única avaliada com 100% do conteúdo, e
as outras quatro perderiam ~37%. Qualquer vantagem dela seria artefato da
janela do encoder, não da estratégia de chunking — exatamente o erro que
apontamos no BR-TaxQA-R (ver [04-referencias-verificadas.md](04-referencias-verificadas.md)).

## Candidatos testados

| Modelo | Params | Janela | Gate | Resultado |
|---|---:|---:|---|---|
| **`BAAI/bge-m3`** | 568M | 8192 | não | ✅ **adotado** — 0% de truncamento com janela 1024 |
| `google/embeddinggemma-300m` | 308M | 2048 | **sim** | 13º de 93 no MTEB-BR, mas exige `hf auth login` |
| `intfloat/multilingual-e5-base` | 278M | 512 | não | ❌ truncaria 83% dos chunks |
| `Alibaba-NLP/gte-multilingual-base` | 305M | 8192 | não | ❌ quebra com `device-side assert` no CUDA |

Sobre o `gte`: seria o ideal em custo (arquitetura *base*, ~3,5x mais barata
que o bge-m3, que é XLM-RoBERTa **large**). Falha em fp16 **e** fp32, com
janela 1024 **e** 512, com `unpad_inputs=False`. O código remoto
(`trust_remote_code`) não sobrevive ao stack atual (torch 2.14, transformers
5.x, Blackwell). O assert é *sticky* — contamina o contexto CUDA e derruba
tudo depois no mesmo processo, então cada variante precisa de processo próprio
para ser testada.

## Configuração final

```yaml
- name: bge_m3                 # DEFAULT
  hf_id: "BAAI/bge-m3"
  query_prefix: ""             # o bge-m3 dispensa prefixo
  passage_prefix: ""
  max_seq_length: 1024
  batch_size: 32
  dtype: auto                  # fp16 na GPU, fp32 na CPU
  gated: false
```

Configuração **verificada**, não presumida: pooling **CLS** (o correto para o
bge-m3), camada `Normalize` ativa (cosseno = produto interno no FAISS),
dimensão 1024.

**Prefixos não são decoração.** Cada família foi treinada com um formato de
entrada, e usar o errado degrada a recuperação **silenciosamente** — o modelo
não reclama, só recupera pior. Por isso ficam versionados no `models.yaml`, com
teste que exige que todo embedder declare os seus:

| Modelo | query | passage |
|---|---|---|
| bge-m3 | *(vazio)* | *(vazio)* |
| e5 | `query: ` | `passage: ` |
| embeddinggemma | `task: search result \| query: ` | `title: none \| text: ` |

## fp16: 3x mais rápido, e validado

Medido contra fp32 em 3.000 chunks e 50 consultas reais:

| Métrica | Valor |
|---|---|
| Kendall tau sobre os scores | **0,998** |
| nDCG@10 do fp16 tomando fp32 como referência | **0,9995** |
| Trocas de ordem entre itens com Δscore < 1e-3 | **100%** (mediana 2e-4) |

As 14 trocas de posição observadas acontecem todas entre itens praticamente
empatados. **O ganho de 3x não custa qualidade.**

## ⚠️ O único passo manual do projeto

`google/embeddinggemma-300m` é **gated** no Hugging Face — dá `401
GatedRepoError` sem autenticação:

```bash
# aceitar a licença em https://huggingface.co/google/embeddinggemma-300m
hf auth login
python -m src.run_experiments --strategy all --retriever dense --embedder pt_compact
```

**Por isso ele não é o default.** Com o `bge_m3` (Apache-2.0, sem gate) o
pipeline roda ponta a ponta sem ninguém criar conta — o que importa para
reprodutibilidade: qualquer integrante clona o repo e roda.

## O que isso significa para o artigo

A frase atual — *"a compact Portuguese model selected based on MTEB-BR"* —
precisa mudar. O critério que decidiu **não foi a posição no ranking**, foi a
**janela de contexto**, e isso é um argumento metodológico melhor: escolhemos
o modelo que permite comparar as cinco estratégias **sem viés de truncamento**.

Sugestão de redação: *"o embedder foi escolhido pela janela de contexto, e não
apenas pelo desempenho em benchmark: um encoder de 512 tokens truncaria 83% dos
chunks e, por atingir as estratégias de forma desigual, introduziria viés na
comparação."*

## Fontes

- [MTEB-BR — arXiv:2607.04581](https://arxiv.org/abs/2607.04581)
- [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)
- [google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m)
- Medições: [resultados/02-benchmark-gpu.md](resultados/02-benchmark-gpu.md)
