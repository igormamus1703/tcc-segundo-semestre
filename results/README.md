# results/

Todo número que aparece no artigo tem que sair de um arquivo daqui, e todo
arquivo daqui tem que dizer de onde veio. Esta pasta é organizada para
responder, meses depois, à única pergunta que importa na defesa: **"de onde
veio este número?"**

```
results/
├── corpus/                    caracterização do corpus (muda só quando o corpus muda)
│   ├── eda_stats.json         nº de docs, tokens por doc, presença de seção
│   └── segmenter_validation.json   acurácia do segmentador contra os spans ouro
│
└── experiments/               uma pasta por RODADA de recuperação
    ├── INDICE.md              tabela de todas as rodadas (gerado, não editar)
    └── AAAAMMDD-HHMM_rotulo/
        ├── manifest.json      config, commit, hardware, versões, tempos
        ├── execucao.log       log com horário de cada etapa
        ├── runs/              arquivos TREC (NÃO versionados — regeneráveis)
        └── tables/            métricas, significância e recortes desta rodada
```

## Convenção de nomes

`AAAAMMDD-HHMM_rotulo` — a data em primeiro lugar faz a ordem alfabética ser a
cronológica, então `ls` já lista na ordem certa e o mais recente fica no fim.
Sem `:` no nome, que o Windows recusa.

O rótulo diz o que a rodada é, e é gerado automaticamente a partir dos
argumentos:

| Exemplo | O que foi |
|---|---|
| `20260906-0215_bm25` | as 5 estratégias no BM25 |
| `20260906-2230_dense_bge_m3` | as 5 estratégias no denso com BGE-M3 |
| `20260906-1830_dense_bge_m3_smoke10q` | smoke test, 10 consultas |
| `20260907-0900_bm25_sum_top_k` | análise de sensibilidade da agregação |

Para forçar um nome: `--label meu_rotulo`.

## O que é versionado e o que não é

| Caminho | No Git? | Por quê |
|---|---|---|
| `corpus/*.json` | ✅ | São os números do artigo sobre o corpus |
| `experiments/*/manifest.json` | ✅ | É a prova de reprodutibilidade da rodada |
| `experiments/*/tables/*.csv` | ✅ | São os resultados que vão para o artigo |
| `experiments/*/execucao.log` | ✅ | Leve, e mostra os tempos reais |
| `experiments/*/runs/*.trec` | ❌ | ~33 MB por rodada, e o manifesto diz como regerar |

## O manifesto

Cada rodada grava um `manifest.json` com:

- **`config`** — estratégias, retriever, embedder (com janela, batch e dtype),
  agregação, `top_chunks`/`top_docs`, nº de consultas;
- **`git`** — commit, branch e se a árvore estava suja (se estava, o resultado
  não é reproduzível a partir do commit — é um alerta, não um detalhe);
- **`versoes`** — Python, torch, sentence-transformers, faiss, bm25s, ranx,
  tiktoken, numpy;
- **`hardware`** — SO, CPU, GPU e VRAM, porque tempo de execução sem hardware
  declarado não significa nada;
- **`etapas`** — uma entrada por estratégia, com nº de chunks e segundos;
- **`comando`** — a linha exata que gerou tudo aquilo.

## Como reproduzir uma rodada

```bash
# 1. leia o comando e o commit no manifesto
cat results/experiments/<rodada>/manifest.json

# 2. volte ao commit, se necessário, e rode o comando de lá
python -m src.run_experiments --strategy all --retriever bm25
python -m src.evaluate          # usa a rodada mais recente automaticamente
```

Para avaliar uma rodada específica em vez da mais recente:

```bash
python -m src.evaluate --experiment results/experiments/20260906-0215_bm25
```
