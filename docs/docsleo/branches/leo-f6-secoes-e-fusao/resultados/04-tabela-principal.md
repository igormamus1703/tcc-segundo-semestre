# A tabela principal do artigo: sete condições

**Data:** 28/09/2026 · **Autor:** Leonardo Marques
**Rodada:** `results/experiments/20260928-1705_f6_tabela_principal`
**Estratégia:** `fixed_512_256` (a melhor sob recorte) · 150 consultas · 2.219 qrels

---

## Por que uma rodada só para isto

A correção de Bonferroni divide o nível de significância pelo número de
comparações. Jogar as 35 condições que a branch produziu numa tabela só são 595
pares, e nada sobreviveria — não porque os efeitos sejam frágeis, mas porque a
correção estaria punindo comparações que ninguém pretende fazer.

A tabela do artigo compara **sete condições escolhidas**, que são as que
respondem à pergunta. São 21 pares, e **os 17 que importam passam**.

```bash
python -m src.evaluate --label f6_tabela_principal --runs \
  .../20260906-0515_bm25/runs/fixed_512_256__bm25.trec \
  .../20260907-0125_dense_bge_m3/runs/fixed_512_256__dense-bge_m3.trec \
  .../20260928-1652_bm25_controle_amostra/runs/fixed_512_256__bm25__amostra-0.2800s42.trec \
  .../20260928-1638_bm25_sec_sem_relatorio/runs/fixed_512_256__bm25__sec-sem_relatorio.trec \
  .../20260928-1650_dense_sec_sem_relatorio/runs/fixed_512_256__dense-bge_m3__sec-sem_relatorio.trec \
  .../20260928-1645_cv_fusao_bm25_denso/runs/fixed_512_256__cv-soma_norm.trec \
  .../20260928-1653_cv_fusao_sec_sem_relatorio/runs/fixed_512_256__cv-soma_norm.trec

python -m src.plots --experiment .../20260928-1705_f6_tabela_principal \
    --referencia fixed_512_256__bm25
```

O `--runs` copia os `.trec` escolhidos para dentro da rodada nova, em vez de só
apontar para eles: a pasta continua respondendo "de onde veio este número?"
mesmo que as rodadas de origem sejam reorganizadas.

## A tabela

| # | Configuração | nDCG@10 | MRR@10 | MAP@10 | Recall@100 |
|---|---|---:|---:|---:|---:|
| 1 | **recorte + fusão (peso por CV)** | **0,3160** | **0,6058** | **0,1330** | **0,5259** |
| 2 | BM25, sem o relatório | 0,2904 | 0,5889 | 0,1190 | 0,4993 |
| 3 | denso, sem o relatório | 0,2627 | 0,5190 | 0,1112 | 0,4564 |
| 4 | fusão (peso por CV), índice completo | 0,2606 | 0,4988 | 0,1038 | 0,5037 |
| 5 | **BM25 (baseline da F5)** | 0,2486 | 0,5186 | 0,0963 | 0,4709 |
| 6 | BM25, −67% **aleatório** (controle) | 0,2260 | 0,4725 | 0,0867 | 0,4310 |
| 7 | denso bge-m3 | 0,2055 | 0,4042 | 0,0800 | 0,4759 |

**Linha 1 contra linha 5:** +27,1% em nDCG@10, +16,8% em MRR@10, +38,1% em
MAP@10 e +11,7% em Recall@100. **Nenhuma métrica piora.**

Figura: `figuras/20260928-1705_f6_tabela_principal__condicoes.png` (e `.pdf`).

## Significância (Bonferroni, 21 pares)

Os pares que sustentam a conclusão:

| Comparação | p | V / E / D |
|---|---:|---|
| recorte+fusão × BM25 baseline | **0,00000** | 95 / 20 / 35 |
| recorte+fusão × controle aleatório | **0,00000** | 99 / 16 / 35 |
| recorte+fusão × BM25 sem relatório | **0,00010** | 77 / 33 / 40 |
| BM25 sem relatório × BM25 baseline | **0,00025** | 84 / 26 / 40 |
| BM25 sem relatório × controle aleatório | **0,00000** | 86 / 24 / 40 |
| controle aleatório × BM25 baseline | **0,02842** | 53 / 27 / 70 (o controle **perde**) |
| BM25 baseline × denso | **0,00085** | 75 / 23 / 52 (replica a F5) |

Duas comparações **não** dão significativas, e as duas são informativas:

| Comparação | p | leitura |
|---|---:|---|
| fusão (índice completo) × BM25 baseline | 0,081 | nesta estratégia, a fusão sozinha é marginal; ela **precisa** do recorte |
| fusão (índice completo) × denso sem relatório | 0,870 | duas rotas diferentes chegam ao mesmo lugar |

## O ganho não se concentra nas consultas fáceis

Recorte por tipo de consulta do JurisTCU, 50 consultas cada, com IC 95% por
bootstrap (10.000 reamostragens de consultas):

| Configuração | pergunta (LLM) | expressão (LLM) | **consulta real (log)** |
|---|---:|---:|---:|
| BM25 (baseline) | 0,3214 [0,273–0,371] | 0,2920 [0,242–0,342] | 0,1322 [0,090–0,178] |
| denso | 0,2723 [0,220–0,326] | 0,2510 [0,198–0,306] | 0,0932 [0,061–0,129] |
| controle aleatório | 0,2976 [0,251–0,347] | 0,2581 [0,206–0,309] | 0,1224 [0,085–0,164] |
| BM25 sem relatório | 0,3669 [0,316–0,417] | 0,3473 [0,295–0,397] | 0,1569 [0,108–0,210] |
| denso sem relatório | 0,3455 [0,295–0,398] | 0,3054 [0,252–0,359] | 0,1373 [0,091–0,188] |
| fusão, índice completo | 0,3394 [0,289–0,391] | 0,3076 [0,257–0,358] | 0,1349 [0,093–0,181] |
| **recorte + fusão** | **0,4041** [0,353–0,456] | **0,3799** [0,329–0,429] | **0,1640** [0,116–0,216] |

| Tipo | ganho da config. final sobre o BM25 |
|---|---:|
| pergunta sintética (LLM) | **+25,7%** |
| expressão sintética (LLM) | **+30,1%** |
| **consulta real de log** | **+24,1%** |

Este é o recorte que costuma desmontar melhoria: as consultas reais de log são
as mais difíceis (nDCG@10 de 0,13 contra 0,32 das sintéticas) e as menos
parecidas com o que o método foi desenhado para atacar. **O ganho se mantém
quase idêntico nos três grupos.** Os ICs se sobrepõem, como esperado com
n = 50 por grupo — a afirmação é de consistência da direção, não de diferença
entre grupos.

## A configuração recomendada, em palavras

> Segmentar o acórdão nas suas macro-seções (basta o segmentador por regras:
> a estrutura ouro não é necessária), **indexar tudo menos o relatório**,
> recuperar com BM25 e com um retriever denso, e **combinar os dois rankings
> com o BM25 pesando ~0,7**. O índice fica com um terço do tamanho e o
> nDCG@10 sobe 27%.

## Ressalvas honestas

1. **A `fixed_512_256` foi escolhida por ser a melhor sob recorte.** Isso é
   uma escolha informada pelos dados. A tabela equivalente para as outras
   quatro estratégias está em
   [01-recorte-por-secao.md](01-recorte-por-secao.md) e
   [03-fusao-hibrida.md](03-fusao-hibrida.md), e o padrão é o mesmo em todas —
   nenhuma conclusão depende dessa escolha.
2. **O peso da fusão veio de CV; a decisão de descartar o relatório não.** Ela
   veio de uma medição do domínio feita *antes* (F5), não de uma varredura. Mas
   a escolha de descartar *o relatório* entre as quatro seções foi informada
   pelo teste exploratório de 07/09, e o conjunto de avaliação é o mesmo. O
   controle aleatório é o que impede que isso seja um ajuste ao acaso.
3. **Corpus de 12.880 acórdãos**, como toda a F5. A decisão de corpus
   (12.880 × 113.827) continua aberta e vale igualmente para estes números.
