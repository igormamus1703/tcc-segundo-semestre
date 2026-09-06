# Branch `leo/f4-indexacao-e-docs`

**Autor:** Leonardo Marques · **Aberta em:** 2026-09-05 · **Status:** 🟡 em teste, ainda não mergeada

Implementa as fases **F4 (indexação e runs)** e **F5 (avaliação, significância e
recortes)**, que estavam como stubs com `NotImplementedError`, e documenta as
divergências entre o que o artigo publica e o que o código produz.

## Documentos

| Doc | Assunto |
|---|---|
| [02-achado-corpus.md](02-achado-corpus.md) | 🔴 **O mais importante:** o corpus do código (12.880) ≠ o do artigo (113.827) |
| [07-numeros-para-o-artigo.md](07-numeros-para-o-artigo.md) | Tabela de substituição: número do artigo × valor medido |
| [08-decisoes-pendentes.md](08-decisoes-pendentes.md) | Checklist do que a equipe precisa decidir |
| [03-referencias-verificadas.md](03-referencias-verificadas.md) | As 8 citações verificadas no arXiv + o que o BR-TaxQA-R concluiu |
| [04-modelos-embedding.md](04-modelos-embedding.md) | Escolha do embedder via MTEB-BR e o único passo manual do projeto |
| [01-ambiente-setup.md](01-ambiente-setup.md) | Setup da máquina, versões, junctions |
| [05-diario-execucao.md](05-diario-execucao.md) | Diário cronológico dos comandos e saídas |
| [06-implementacao-f4.md](06-implementacao-f4.md) | Decisões de projeto e armadilhas de biblioteca |
| [resultados/](resultados/) | Números medidos, por retriever |

## Código entregue

| Entrega | Onde |
|---|---|
| BM25 sobre chunks (`bm25s`) | `src/indexing/lexical.py` |
| Retriever denso (FAISS `IndexFlatIP` + cache `.npy`) | `src/indexing/dense.py` |
| Normalização PT compartilhada por indexação e busca | `src/indexing/text_norm.py` |
| Orquestrador estratégia × retriever → TREC run | `src/run_experiments.py` |
| Métricas, significância pareada e CLI das tabelas | `src/evaluate.py` |
| Bootstrap IC 95% e os três recortes | `src/analysis.py` |
| `hf_id` do `pt_compact` resolvido pelo MTEB-BR | `configs/models.yaml` |

## Testes: 89 passed ✅

```bash
cd juris-chunking && pytest -q
```

Eram 39 antes desta branch. Os 50 novos estão em `test_indexing.py` (18),
`test_evaluate.py` (21) e `test_run_experiments.py` (11), e existem sobretudo
para travar **erros silenciosos** — os que não levantam exceção, só pioram o
número ou esvaziam uma tabela:

- **encoding**: o `ranx` lê TREC com o encoding da plataforma e transforma
  `plenário` em `plenÃ¡rio`; quase todo doc_id do TCU tem acento
- **alinhamento**: `make_comparable=True` altera o Run in-place, e ler os ids
  antes pareia o score com a consulta errada
- **cache**: embedding reaproveitado de outro conjunto de chunks não
  corresponde mais ao chunk daquela posição
- **normalização**: se a busca normalizar diferente da indexação, o recall cai
  sem nenhum erro
- **recortes**: tercis cortados pelos percentis do corpus dão grupos de 3/67/80

O teste do denso usa um modelo falso determinístico, para não baixar 500 MB de
pesos numa suíte unitária; a validação com o modelo real é feita por smoke test.

## Checklist para o merge

- [x] `pytest` verde (89 passed)
- [x] Pipeline rodado ponta a ponta no corpus real (ingest → chunkers → BM25 → avaliação)
- [x] Artefatos regenerados e versionados (`results/tables/`)
- [ ] **Revisão do Igor** — especialmente a questão do corpus ([02](02-achado-corpus.md)), porque muda o artigo
- [ ] Runs densos concluídos
- [ ] Merge

## Pontos de atenção para quem revisar

1. **A branch altera `results/tables/eda_stats.json` e `segmenter_validation.json`.**
   Não é regressão: os valores antigos vinham de uma rodada anterior ao filtro
   `wanted_keys`. Ver [02-achado-corpus.md](02-achado-corpus.md).
2. **Não mexi em `ingest.py`, `segmenter/` nem `chunkers/`** — as fases do Igor
   ficaram intactas. Duas melhorias sugeridas para o `ingest.py` estão em
   [08-decisoes-pendentes.md](08-decisoes-pendentes.md), item 5, aguardando o aval dele.
3. **Os números do artigo mudam** se esta branch for aceita — lista completa em
   [07-numeros-para-o-artigo.md](07-numeros-para-o-artigo.md).
