# Diário de execução

Cronologia do que foi rodado, com os comandos e o que saiu. Serve para
reproduzir e para escrever a Metodologia sem depender de memória. Os
detalhes de cada item estão nos documentos numerados; aqui é só a linha do
tempo.

---

## 05/09/2026 — sessão 1: ambiente, corpus, F4/F5, primeiro número

| Hora | O quê | Resultado |
|---|---|---|
| 16:30 | Clone, venv em `C:\venvs\tcc-juris`, junctions para `data/` e `.venv` | Python 3.13.7; **o risco `ranx`/numba em 3.13 não se materializou** |
| 16:38 | `download_datasets.py juristcu` | 90 MB |
| 16:40 → 18:50 | `download_datasets.py tcu_acordaos` | 6,0 GB, 21 CSVs |
| 17:00 | Contagem de chaves no `doc.csv` do JurisTCU | **12.881** chaves únicas → o corpus do artigo (113.827) não é o que o código produz. [02-achado-corpus.md](02-achado-corpus.md) |

> **12.881 e 12.880 são coisas diferentes**, e aparecem os dois ao longo dos
> documentos: 12.881 é o número de acórdãos **referenciados** pelo JurisTCU
> (chaves de join únicas no `doc.csv`); 12.880 é o corpus **montado** — um
> desses acórdãos não foi encontrado nos CSVs anuais do TCU. O número que vale
> para qualquer resultado é **12.880**.
| 17:00 | Verificação das 8 citações no arXiv | Nenhuma fantasma. [04-referencias-verificadas.md](04-referencias-verificadas.md) |
| 17:05 → 19:30 | Implementação de F4/F5 (BM25, denso, runs, avaliação, recortes) | 39 → 81 testes |
| 19:00 | `python -m src.ingest` | **12.880** docs, join 98,7%, qrels 99,69% |
| 19:15 | `python -m src.segmenter.validate` | **92,2%** de acurácia, **0%** de fallback |
| 19:20 → 20:10 | `python -m src.chunkers.run --strategy all` | **2.200.767** chunks, 6,0 GB |

## 06/09/2026 — sessão 2: BM25, GPU, análise do domínio, rodada noturna

| Hora | O quê | Resultado |
|---|---|---|
| 02:15 | `run_experiments --retriever bm25` (CPU, 25 min) + `evaluate` | **nDCG@10 de 0,2412 a 0,2526; nenhum p < 0,05.** Marco da Semana 7 |
| 02:40 | Bug: `ranx` lê TREC com encoding da plataforma → recorte por tamanho vazio | Corrigido (leitura em UTF-8). [06-implementacao-f4.md](06-implementacao-f4.md) |
| 02:45 | Bug: tercis cortados pelo corpus davam 3/67/80 consultas | Corrigido (percentis das consultas → 50/50/50) |
| 03:20 | Benchmark do encode em CPU | **4,8 chunks/s → 127 h.** Inviável |
| 03:30 | `torch 2.14.0+cu130` instalado; RTX 5060 reconhecida | GPU fp16: **288 chunks/s** com e5-base |
| 03:35 | Medição de truncamento por estratégia | e5-base (512) descartaria **37%** do conteúdo, só na `fixed_512_256` não. [05-modelos-embedding.md](05-modelos-embedding.md) |
| 03:40 → 04:10 | Teste de `gte-multilingual-base` (falha), `embeddinggemma` (gated), **`bge-m3` (ok)** | bge-m3 adotado: 0% de truncamento, 10,1 h projetadas |
| 04:00 | `results/` reorganizado; `src/experiment.py` (manifesto + log por rodada) | [../../../../results/README.md](../../../../results/README.md) |
| 04:15 | Validação fp16 × fp32 (3.000 chunks, 50 consultas) | tau 0,998; nDCG relativo 0,9995. **fp16 seguro** |
| 04:20 | Checkpoint incremental no encode; **bug do `np.save` pego pelo teste** | Teria quebrado a rodada na 1ª gravação |
| 04:17 → 04:32 | Validação do denso num subcorpus (1.899 docs, 30 consultas) | BM25 0,4928 × denso 0,4032. Config verificada (CLS, Normalize) |
| 04:35 | Localização dos excertos julgados relevantes nas seções | **72% na fundamentação (22,8% do texto).** [03-analise-do-dominio.md](03-analise-do-dominio.md) |
| 04:40 | Comparação com os baselines do JurisTCU | razão estável 0,51–0,60 nos 3 grupos: pipeline sadio |
| 04:45 | Recorte por seção do chunk vencedor; análise de poder | [resultados/01-bm25.md](resultados/01-bm25.md) |
| 04:50 | Tentativa de ONNX Runtime | `optimum` rebaixou o transformers e quebrou o ambiente. **Revertido e descartado** |
| 05:03 → 05:14 | Teste da previsão sobre o denso (451 docs, 25 consultas) | Magnitude certa (3x), **direção errada**. [resultados/03-previsao-denso.md](resultados/03-previsao-denso.md) |
| 05:14 | **Rodada noturna lançada** (`rodada_completa.ps1 -MaxHoras 5`) | BM25 reproduzido **idêntico** (`20260906-0515_bm25`); denso iniciado 05:39 |
| 05:30 → 05:55 | `src/plots.py` com rodapé de contexto; docs reorganizados por rodada | Figuras autocontidas. [../../../../results/README.md](../../../../results/README.md) |
| 05:55 | Rodada **parada e relançada** para partir de commit limpo | Perda: ~10 min do 1º bloco (sem checkpoint ainda) |

## Fim da sessão 2

A rodada densa de 5 h fechou **3 das 5 estratégias**
(`20260906-0547_dense_bge_m3`): as duas estruturais e a `recursive_default`.
As duas fixas ficaram para a sessão seguinte, reaproveitando o cache.

---

## 07/09/2026 — sessão 3: as duas fixas, a filtragem por seção, e o fechamento

| Hora | O quê | Resultado |
|---|---|---|
| 00:40 | Rodada densa relançada para as duas fixas | Interrompida por **desligamento da máquina**, com 14 blocos já gravados |
| 01:25 | Relançamento (`20260907-0125_dense_bge_m3`) | **Retomou do checkpoint sem reencodar** os 14 blocos — economizou ~1 h |
| 01:25 → 03:04 | `fixed_512_256` no denso (907.914 chunks) | 99,2 min. **Experimento 5 × 2 completo** |
| 03:10 | Avaliação cruzada (`evaluate --incluir 20260906-0515_bm25`) | 10 runs, 45 pares, **26 significativos**. [resultados/06-final-5x2.md](resultados/06-final-5x2.md) |
| 03:20 | Figuras das duas rodadas (`src/plots.py`) | 10 figuras PDF+PNG, com rodapé de contexto |
| 03:40 | **Experimento exploratório:** filtrar o índice FAISS por seção, reusando o cache | Descartar o relatório dá **+16,9% de nDCG@10** (p = 0,001), e vale com spans preditos (p = 0,017). [resultados/05-filtragem-por-secao.md](resultados/05-filtragem-por-secao.md) |
| 04:10 | Revisão de todos os `.md` do repositório contra os números finais | Trechos escritos com o experimento ainda parcial corrigidos em 9 arquivos |
| 04:30 | `pytest -q` e **merge** de `leo/f4-indexacao-e-docs` na `main` | Branch fechada |

### A armadilha da sessão: significativo **e** abaixo do MDE

O único par significativo entre estratégias (`fixed_512_256` ×
`structural_gold` no denso, p = 0,0295) tem efeito de **0,0208**, enquanto o
MDE para poder de 80% é **0,0265**. Não há contradição — o MDE é o efeito
detectável *com 80% de poder*, e efeitos menores aparecem com poder inferior.
Mas obriga a reportar o achado como **resultado de fronteira**, que precisa de
replicação, e não como conclusão. Ficou registrado assim nos três documentos
que o citam.

## Em aberto ao fim da branch

- **Decisão do corpus oficial** — bloqueia os números do artigo. É da equipe.
- Reimplementar a **filtragem por seção** em `src/`, com testes, e rodar no
  BM25 e nas outras estratégias — hoje é só exploratória, no denso.
- Análise de sensibilidade da agregação (`sum_top_k` vs `max_pooling`).
- Notebooks 01–03.

Os próximos passos completos, com responsáveis em aberto, estão no
[PLANO.md](../../../../PLANO.md) da raiz.
