# Branch `leo/f4-indexacao-e-docs`

**Autor:** Leonardo Marques · **Aberta em:** 2026-09-05 · **Status:** 🟡 em teste, ainda não mergeada

Implementa as fases **F4 (indexação e runs)** e **F5 (avaliação, significância e
recortes)**, que estavam como stubs com `NotImplementedError`, e documenta as
divergências encontradas entre o que o artigo publica e o que o código produz.

## O que esta branch entrega

| Entrega | Onde |
|---|---|
| BM25 sobre chunks (`bm25s`) | `src/indexing/lexical.py` |
| Retriever denso (FAISS `IndexFlatIP` + cache `.npy`) | `src/indexing/dense.py` |
| Normalização PT compartilhada por indexação e busca | `src/indexing/text_norm.py` |
| Orquestrador estratégia × retriever → TREC run | `src/run_experiments.py` |
| Métricas, significância pareada e CLI das tabelas | `src/evaluate.py` |
| Bootstrap IC 95% e os três recortes analíticos | `src/analysis.py` |
| `hf_id` do `pt_compact` resolvido pelo MTEB-BR | `configs/models.yaml` |

## Documentos

### Decisões e achados
| Doc | Assunto |
|---|---|
| [02-achado-corpus.md](02-achado-corpus.md) | 🔴 **O mais importante:** o corpus do código (12.880) ≠ o do artigo (113.827) |
| [03-referencias-verificadas.md](03-referencias-verificadas.md) | As 8 citações verificadas no arXiv + o que o BR-TaxQA-R realmente concluiu |
| [04-modelos-embedding.md](04-modelos-embedding.md) | Escolha do embedder via MTEB-BR e o único passo manual do projeto |
| [08-decisoes-pendentes.md](08-decisoes-pendentes.md) | Checklist do que a equipe precisa decidir |

### Execução
| Doc | Assunto |
|---|---|
| [01-ambiente-setup.md](01-ambiente-setup.md) | Setup da máquina, versões, junctions |
| [05-diario-execucao.md](05-diario-execucao.md) | Diário cronológico dos comandos e saídas |
| [06-implementacao-f4.md](06-implementacao-f4.md) | Decisões de projeto do código e armadilhas de biblioteca |
| [07-numeros-para-o-artigo.md](07-numeros-para-o-artigo.md) | Tabela de substituição: número do artigo × valor medido |

### Testes e resultados
| Pasta | Conteúdo |
|---|---|
| [testes/](testes/) | Estado da suíte, o que cada teste trava, como rodar |
| [resultados/](resultados/) | Resultados medidos, por retriever |

## Checklist para o merge na `main`

- [x] `pytest` verde (**89 passed**)
- [x] Pipeline rodado ponta a ponta no corpus real (ingest → chunkers → BM25 → avaliação)
- [x] Artefatos regenerados e versionados (`results/tables/`)
- [x] Documentação escrita
- [ ] **Revisão do Igor** — especialmente a questão do corpus ([02](02-achado-corpus.md)), porque muda o artigo
- [ ] Runs densos concluídos
- [ ] Merge

## Commits

```
3e281f0  Corrige leitura UTF-8 dos arquivos TREC e balanceia os tercis do recorte
3c4b3bb  Adiciona checklist de decisoes pendentes da equipe
41123b3  Documenta a analise do BR-TaxQA-R e a escala real do chunking
e7aef6d  Corrige recorte por tamanho de documento quando falta n_tokens no corpus
e78ac65  Atualiza README com F4/F5 concluidas e o passo manual do embedder gated
d10c442  Regenera eda_stats e segmenter_validation no corpus que o codigo produz
dd4f2f0  Implementa F4 (indexacao e runs) e F5 (avaliacao)
```

## Pontos de atenção para quem revisar

1. **A branch altera `results/tables/eda_stats.json` e `segmenter_validation.json`.**
   Não é regressão: os valores antigos vinham de uma rodada anterior ao filtro
   `wanted_keys`. Ver [02-achado-corpus.md](02-achado-corpus.md).
2. **Não mexi em `ingest.py`, `segmenter/` nem `chunkers/`** — as fases do Igor
   ficaram intactas. Há duas melhorias sugeridas para o `ingest.py` em
   [08-decisoes-pendentes.md](08-decisoes-pendentes.md), item 5, aguardando o aval dele.
3. **Os números do artigo mudam** se esta branch for aceita. A lista completa
   está em [07-numeros-para-o-artigo.md](07-numeros-para-o-artigo.md).
