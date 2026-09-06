# Testes — branch `leo/f4-indexacao-e-docs`

**Última execução:** 2026-09-06 · **Resultado: 89 passed** ✅

```bash
cd juris-chunking
pytest -q          # 89 passed
```

## Cobertura por arquivo

| Arquivo | Testes | Fase | Autoria |
|---|---:|---|---|
| `tests/test_ingest.py` | 12 | F1 | Igor |
| `tests/test_segmenter.py` | 6 | F2 | Igor |
| `tests/test_tokenization.py` | 7 | F3 | Igor |
| `tests/test_chunkers.py` | 12 | F3 | Igor |
| `tests/test_retrieval.py` | 2 | F4 | Igor |
| **`tests/test_indexing.py`** | **18** | **F4** | **Leo (novo)** |
| **`tests/test_run_experiments.py`** | **11** | **F4** | **Leo (novo)** |
| **`tests/test_evaluate.py`** | **21** | **F5** | **Leo (novo)** |
| **Total** | **89** | | (eram 39 antes desta branch) |

## O que os testes novos travam, e por quê

Todos os testes abaixo existem porque o erro correspondente é **silencioso** —
não levanta exceção, só piora o resultado ou esvazia uma tabela. São
exatamente os que a suíte precisa ter, porque um erro barulhento a gente
descobre sozinho.

### Encoding e normalização

| Teste | O que impede |
|---|---|
| `test_load_qrels_preserva_acento_no_doc_id` | O `ranx` lê TREC com o encoding da plataforma e transforma `plenário` em `plenÃ¡rio`. Quase todo doc_id do TCU tem acento |
| `test_load_run_preserva_acento_no_doc_id` | idem, do lado do run |
| `test_qrels_e_run_com_acento_casam_e_avaliam` | Ponta a ponta: doc_id acentuado tem que dar nDCG 1.0, não 0 |
| `test_bm25_casa_consulta_acentuada_com_texto_sem_acento` | Se a normalização da busca divergir da indexação, o recall cai sem nenhum erro |
| `test_normalize_iguala_termo_acentuado_e_nao_acentuado` | "acórdão" e "acordao" viram termos distintos no índice |

### Correção numérica

| Teste | O que impede |
|---|---|
| `test_per_query_scores_alinha_score_com_a_consulta_certa` | `make_comparable=True` altera o Run in-place; ler os ids antes pareia score com a consulta errada |
| `test_dense_cache_invalida_se_chunks_mudarem` | Cache reaproveitado indevidamente faz o embedding da posição *i* não corresponder ao chunk *i* |
| `test_query_terciles_ficam_equilibrados_mesmo_com_relevantes_grandes` | Tercis cortados pelos percentis do corpus dão grupos de 3/67/80 consultas |
| `test_slice_by_doc_length_usa_docs_relevantes_nao_recuperados` | Recorte dependente do run torna as colunas da tabela não comparáveis |
| `test_run_one_bm25_ponta_a_ponta` | A agregação tem que colapsar chunks do mesmo documento numa linha só |

### Configuração

| Teste | O que impede |
|---|---|
| `test_models_yaml_nao_tem_mais_preencher` | O `hf_id: PREENCHER` bloqueava a F4 |
| `test_models_yaml_default_embedder_nao_e_gated` | O default precisa rodar sem ninguém criar conta no Hugging Face |
| `test_models_yaml_todo_embedder_tem_prefixos` | Prefixo errado degrada a recuperação silenciosamente |

## Testes que não existem (e por quê)

- **Denso com o modelo real**: `tests/test_indexing.py` usa um `FakeModel`
  determinístico em vez de baixar ~500 MB de pesos. A validação com o modelo de
  verdade é feita fora da suíte, por smoke test.
- **Corpus real**: nenhum teste depende de `data/` — a suíte roda numa máquina
  recém-clonada, sem os 6 GB baixados.
