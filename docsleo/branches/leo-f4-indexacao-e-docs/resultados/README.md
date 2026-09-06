# Resultados — branch `leo/f4-indexacao-e-docs`

Resultados **medidos**, cada um com o comando que o gerou e o artefato que o
comprova. Nada aqui é estimativa; quando for projeção, está marcado como tal.

| Doc | Retriever | Status |
|---|---|---|
| [09-resultados-bm25.md](09-resultados-bm25.md) | BM25 (léxico) | ✅ concluído |
| _10-resultados-dense.md_ | Denso (e5-base) | ⏳ em execução |

## Contexto obrigatório para ler qualquer número daqui

**Corpus:** 12.880 acórdãos do TCU, 150 consultas, 2.219 pares de qrel.
Se a equipe mudar o corpus ([../08-decisoes-pendentes.md](../08-decisoes-pendentes.md),
item 1), **tudo aqui precisa ser refeito.**

## Resumo em uma linha

Com BM25, **nenhuma diferença entre as cinco estratégias é estatisticamente
significativa** (menor p = 0,097). O resultado global é nulo — o que o
`plano_tecnico.md` §7 já previa como desfecho legítimo. Os achados que
sobrevivem são os dos recortes e da ablação `gold` × `pred`.

## Artefatos versionados

```
results/tables/main_results.csv          # 5 runs x 4 métricas
results/tables/significance.csv          # 10 pares, p-valor e win/tie/loss
results/tables/significance_report.txt   # relatório do ranx
results/tables/slices_query_type.csv     # recorte por tipo de consulta
results/tables/slices_doc_length.csv     # recorte por tercil de tamanho
results/tables/slices_retriever.csv      # recorte por retriever
```

Os arquivos TREC (`results/runs/*.trec`) **não** são versionados — são
regeneráveis e somam ~33 MB. Reproduza com:

```bash
python -m src.run_experiments --strategy all --retriever bm25   # ~25 min
python -m src.evaluate
```
