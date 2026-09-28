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
| `20260928-1638_bm25_sec_sem_relatorio` | F6: índice sem os chunks do relatório |
| `20260928-1652_bm25_controle_amostra` | F6: controle — mesmo tamanho de índice, sorteado |
| `20260928-1751_cv_fusao_bm25_denso` | F6: fusão com peso por validação cruzada |
| `20260928-1728_fusao4_peso_igual` | F6: fusão das 4 condições com peso igual |
| `20260928-1822_f6_tabela_principal` | F6: comparação de condições montada com `--runs` |

Para forçar um nome: `--label meu_rotulo`.

### Rodadas de comparação (`--runs`)

`python -m src.evaluate --runs a.trec b.trec ... --label comparacao` cria uma
rodada nova a partir de runs avulsos de rodadas quaisquer. Os `.trec` são
**copiados** para dentro dela, não referenciados: a pasta continua respondendo
"de onde veio este número?" mesmo que as rodadas de origem sejam
reorganizadas, e o `manifest.json` guarda o caminho de origem de cada um.

Serve para a tabela do artigo. A correção de Bonferroni divide o nível de
significância pelo número de pares, então jogar 35 runs numa tabela só
enterraria efeitos reais debaixo de comparações que ninguém pretende fazer.

## O que é versionado e o que não é

| Caminho | No Git? | Por quê |
|---|---|---|
| `corpus/*.json` | ✅ | São os números do artigo sobre o corpus |
| `experiments/*/manifest.json` | ✅ | É a prova de reprodutibilidade da rodada |
| `experiments/*/tables/*.csv` | ✅ | São os resultados que vão para o artigo |
| `experiments/*/execucao.log` | ✅ | Leve, e mostra os tempos reais |
| `experiments/*/runs/*.trec` | ❌ | ~33 MB por rodada, e o manifesto diz como regerar |

## Figuras: toda imagem é autocontida

`python -m src.plots` gera as figuras de uma rodada em
`experiments/<rodada>/figuras/`, e **cada uma carrega no rodapé** a rodada, a
data, o corpus (nº de docs, consultas e qrels), o retriever/modelo com sua
configuração e o commit — tudo lido do `manifest.json`, nada digitado à mão.

```
experiments/20260906-0515_bm25/figuras/
├── 20260906-0515_bm25__resultados_principais.{pdf,png}
├── 20260906-0515_bm25__recorte_tipo_consulta.{pdf,png}
├── 20260906-0515_bm25__recorte_tamanho_doc.{pdf,png}
├── 20260906-0515_bm25__secoes_recuperadas.{pdf,png}
└── 20260906-0515_bm25__significancia.{pdf,png}
```

O nome do arquivo começa com a rodada e o rodapé repete o contexto, de
propósito: uma figura copiada sozinha para o artigo, para o pôster ou para uma
mensagem continua dizendo de onde veio. Sem isso, três semanas depois ninguém
sabe se aquele gráfico é do corpus de 12.880 ou do de 113.827, do BM25 ou do
denso, de antes ou depois de uma correção.

**Regra:** figura que vai para documentação ou artigo sai do `src.plots`, nunca
de um script avulso — e, ao copiar para uma pasta de docs, vai para uma
subpasta com o nome da rodada (`figuras/<rodada>/`), não solta.

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
