# Branch `leo/f4-indexacao-e-docs`

**Autor:** Leonardo Marques · **Aberta em:** 2026-09-05 · **Fechada em:** 2026-09-07 · **Status:** ✅ concluída, mergeada na `main`

Implementa as fases **F4 (indexação e runs)** e **F5 (avaliação, significância e
recortes)**, que estavam como stubs, e documenta os achados que surgiram ao
rodar o pipeline sobre o corpus real.

## Comece por aqui

| Se você tem 2 minutos | Leia |
|---|---|
| O problema mais urgente do projeto | [02-achado-corpus.md](02-achado-corpus.md) — o artigo diz 113.827 documentos, o código produz 12.880 |
| O achado mais interessante | [03-analise-do-dominio.md](03-analise-do-dominio.md) — 72% da relevância está em 22,8% do texto |
| O resultado final | [resultados/06-final-5x2.md](resultados/06-final-5x2.md) — 5 estratégias × 2 retrievers, e o BM25 vence o denso nas cinco |
| O que precisa ser decidido | [08-decisoes-pendentes.md](08-decisoes-pendentes.md) |
| Os números para corrigir no artigo | [07-numeros-para-o-artigo.md](07-numeros-para-o-artigo.md) |

## Documentos

### Achados e decisões
| Doc | Assunto |
|---|---|
| [02-achado-corpus.md](02-achado-corpus.md) | 🔴 O corpus do código (12.880) ≠ o do artigo (113.827) |
| [03-analise-do-dominio.md](03-analise-do-dominio.md) | Onde mora a relevância no acórdão + comparação com os baselines do JurisTCU |
| [04-referencias-verificadas.md](04-referencias-verificadas.md) | As 8 citações conferidas no arXiv e o que o BR-TaxQA-R realmente concluiu |
| [05-modelos-embedding.md](05-modelos-embedding.md) | Escolha do embedder — decidida pela janela de contexto, não pelo ranking |
| [08-decisoes-pendentes.md](08-decisoes-pendentes.md) | Checklist do que a equipe precisa decidir |

### Execução
| Doc | Assunto |
|---|---|
| [01-ambiente-setup.md](01-ambiente-setup.md) | Setup da máquina, versões, junctions |
| [06-implementacao-f4.md](06-implementacao-f4.md) | Decisões de projeto e armadilhas de biblioteca |
| [07-numeros-para-o-artigo.md](07-numeros-para-o-artigo.md) | Tabela de substituição: número do artigo × valor medido |
| [09-diario-execucao.md](09-diario-execucao.md) | Diário cronológico dos comandos |

### Resultados
| Doc | Assunto |
|---|---|
| [resultados/01-bm25.md](resultados/01-bm25.md) | Primeiro número: BM25 nas 5 estratégias, com gráficos |
| [resultados/02-benchmark-gpu.md](resultados/02-benchmark-gpu.md) | Custo do encode, escolha de precisão e o que NÃO acelerou |
| [resultados/03-previsao-denso.md](resultados/03-previsao-denso.md) | Previsão registrada antes de rodar, e o teste dela |
| [resultados/04-denso-parcial.md](resultados/04-denso-parcial.md) | Denso, 3 de 5 estratégias — registro parcial, **superado** pelo 06 |
| [resultados/05-filtragem-por-secao.md](resultados/05-filtragem-por-secao.md) | 🏆 **Descartar o relatório melhora o nDCG@10 em 16,9%** (p = 0,001) |
| [resultados/06-final-5x2.md](resultados/06-final-5x2.md) | ⭐ **Resultado final:** 5 estratégias × 2 retrievers, com a inversão completa |

## Código entregue

| Entrega | Onde |
|---|---|
| BM25 sobre chunks (`bm25s`) | `src/indexing/lexical.py` |
| Retriever denso (FAISS + cache `.npy` + checkpoint) | `src/indexing/dense.py` |
| Normalização PT compartilhada por indexação e busca | `src/indexing/text_norm.py` |
| Orquestrador com orçamento de tempo | `src/run_experiments.py` |
| Métricas, significância e poder estatístico | `src/evaluate.py`, `src/analysis.py` |
| Rastreabilidade das rodadas (manifesto + log) | `src/experiment.py` |
| Figuras do artigo | `src/plots.py` |
| Rodada completa em um comando | `scripts/rodada_completa.ps1` |

## Testes: 115 passando

Eram **39** antes desta branch. Os 76 novos existem sobretudo para travar
**erros silenciosos** — os que não levantam exceção, só pioram o número ou
esvaziam uma tabela:

- **encoding**: o `ranx` lê TREC com o encoding da plataforma e transforma
  `plenário` em `plenÃ¡rio`; quase todo doc_id do TCU tem acento
- **alinhamento**: `make_comparable=True` altera o `Run` in-place, e ler os ids
  antes pareia o score com a consulta errada
- **cache**: embedding reaproveitado de outro conjunto de chunks não
  corresponde mais ao chunk daquela posição
- **checkpoint**: bloco truncado por interrupção precisa ser refeito, não aceito
- **normalização**: se a busca normalizar diferente da indexação, o recall cai
  sem nenhum erro
- **recortes**: tercis cortados pelos percentis do corpus dão grupos de 3/67/80

Três bugs reais foram encontrados **pelos próprios testes** antes de causarem
dano: o `np.save` que acrescenta `.npy` e quebraria o checkpoint na primeira
gravação; o `--max-horas 0` que é *falsy* e desligava o próprio orçamento; e o
teste que criava pastas na `results/experiments/` de verdade.

## Checklist para o merge

- [x] `pytest` verde (115)
- [x] Pipeline rodado ponta a ponta no corpus real (ingest → chunkers → BM25 → avaliação)
- [x] Artefatos regenerados e versionados
- [x] Documentação e figuras (10 figuras, com rodapé de contexto)
- [x] Rodada densa, 3 de 5 estratégias (`20260906-0547_dense_bge_m3`)
- [x] Duas estratégias fixas no denso (`20260907-0125_dense_bge_m3`) — **experimento 5 × 2 completo**
- [x] Avaliação cruzada BM25 × denso, com significância e poder
- [x] Merge na `main` — 07/09/2026
- [ ] **Revisão do Igor** — sobretudo a questão do corpus, porque muda o artigo

> O merge foi feito com a revisão do Igor ainda pendente **de propósito**: a
> branch só acrescenta código e documentação e não altera as fases dele, e
> segurá-la na prateleira atrasaria quem for continuar. A decisão do corpus
> continua aberta, registrada em
> [08-decisoes-pendentes.md](08-decisoes-pendentes.md).

## Pontos de atenção para quem revisar

1. **A branch altera `results/corpus/*.json`.** Não é regressão: os valores
   antigos vinham de uma rodada anterior ao filtro `wanted_keys`.
2. **`results/` foi reorganizado** em `corpus/` e `experiments/<data-hora>_rótulo/`,
   com manifesto por rodada. Ver `results/README.md`.
3. **Não mexi em `ingest.py`, `segmenter/` nem `chunkers/`** — as fases do Igor
   ficaram intactas. Duas melhorias sugeridas estão em
   [08-decisoes-pendentes.md](08-decisoes-pendentes.md), item 5.
4. **Os números do artigo mudam** se esta branch for aceita — lista completa em
   [07-numeros-para-o-artigo.md](07-numeros-para-o-artigo.md).
