# A tabela principal do artigo: oito condições

**Data:** 28/09/2026 · **Autor:** Leonardo Marques
**Rodada:** `results/experiments/20260928-1822_f6_tabela_principal`
**Estratégia:** `fixed_512_256` (a melhor sob recorte) · 150 consultas · 2.219 qrels

---

## Por que uma rodada só para isto

A correção de Bonferroni divide o nível de significância pelo número de
comparações. Jogar as ~40 condições que a branch produziu numa tabela só são
centenas de pares, e nada sobreviveria — não porque os efeitos sejam frágeis,
mas porque a correção estaria punindo comparações que ninguém pretende fazer.

A tabela do artigo compara **oito condições escolhidas**, que são as que
respondem à pergunta. São 28 pares, e **23 deles passam**.

```bash
python -m src.evaluate --label f6_tabela_principal --runs \
  .../20260906-0515_bm25/runs/fixed_512_256__bm25.trec \
  .../20260907-0125_dense_bge_m3/runs/fixed_512_256__dense-bge_m3.trec \
  .../20260928-1652_bm25_controle_amostra/runs/fixed_512_256__bm25__amostra-0.2800s42.trec \
  .../20260928-1638_bm25_sec_sem_relatorio/runs/fixed_512_256__bm25__sec-sem_relatorio.trec \
  .../20260928-1650_dense_sec_sem_relatorio/runs/fixed_512_256__dense-bge_m3__sec-sem_relatorio.trec \
  .../20260928-1751_cv_fusao_bm25_denso/runs/fixed_512_256__cv-soma_norm.trec \
  .../20260928-1758_cv_fusao_sec_sem_relatorio/runs/fixed_512_256__cv-soma_norm.trec \
  .../20260928-1728_fusao4_peso_igual/runs/fixed_512_256__soma_norm.trec

python -m src.plots --experiment .../20260928-1822_f6_tabela_principal \
    --referencia fixed_512_256__bm25
```

O `--runs` copia os `.trec` escolhidos para dentro da rodada nova, em vez de só
apontar para eles: a pasta continua respondendo "de onde veio este número?"
mesmo que as rodadas de origem sejam reorganizadas.

## A tabela

| # | Configuração | nDCG@10 | MRR@10 | MAP@10 | Recall@100 |
|---|---|---:|---:|---:|---:|
| 1 | **fusão das 4 condições, peso igual** | **0,3215** | 0,6000 | **0,1402** | **0,5479** |
| 2 | recorte + fusão (peso por CV) | 0,3160 | **0,6058** | 0,1330 | 0,5259 |
| 3 | BM25, sem o relatório | 0,2904 | 0,5889 | 0,1190 | 0,4993 |
| 4 | denso, sem o relatório | 0,2627 | 0,5190 | 0,1112 | 0,4564 |
| 5 | fusão (peso por CV), índice completo | 0,2606 | 0,4988 | 0,1038 | 0,5037 |
| 6 | **BM25 (baseline da F5)** | 0,2486 | 0,5186 | 0,0963 | 0,4709 |
| 7 | BM25, −67% **aleatório** (controle) | 0,2260 | 0,4725 | 0,0867 | 0,4310 |
| 8 | denso bge-m3 | 0,2055 | 0,4042 | 0,0800 | 0,4759 |

**Linha 1 contra linha 6:** +29,3% em nDCG@10, +15,7% em MRR@10, +45,6% em
MAP@10 e +16,4% em Recall@100. **Nenhuma métrica piora.**

Figura: `figuras/20260928-1822_f6_tabela_principal__condicoes.png` (e `.pdf`).

## Significância (Bonferroni, 28 pares)

Os pares que sustentam a conclusão:

| Comparação | p | V / E / D |
|---|---:|---|
| fusão das 4 × BM25 baseline | **0,00000** | 100 / 20 / 30 |
| fusão das 4 × controle aleatório | **0,00000** | 104 / 19 / 27 |
| fusão das 4 × BM25 sem relatório | **0,00030** | 75 / 27 / 48 |
| recorte + fusão × BM25 baseline | **0,00000** | 95 / 20 / 35 |
| recorte + fusão × BM25 sem relatório | **0,00010** | 77 / 33 / 40 |
| BM25 sem relatório × BM25 baseline | **0,00025** | 84 / 26 / 40 |
| BM25 sem relatório × controle aleatório | **0,00000** | 86 / 24 / 40 |
| controle aleatório × BM25 baseline | **0,02842** | 53 / 27 / 70 (o controle **perde**) |
| BM25 baseline × denso | **0,00085** | 75 / 23 / 52 (replica a F5) |
| denso sem relatório × denso | **0,00000** | 90 / 25 / 35 |

Cinco pares **não** dão significativos, e quatro deles são informativos:

| Comparação | p | leitura |
|---|---:|---|
| fusão das 4 × recorte + fusão (CV) | 0,338 | **as duas melhores são equivalentes** — e a sem parâmetro é a que se reporta |
| fusão (índice completo) × BM25 baseline | 0,081 | nesta estratégia, a fusão sozinha é marginal; ela **precisa** do recorte |
| fusão (índice completo) × denso sem relatório | 0,870 | duas rotas diferentes chegam ao mesmo lugar |
| BM25 baseline × denso sem relatório | 0,345 | recortar o índice do denso o traz ao nível do BM25 completo |

## O ganho não se concentra nas consultas fáceis

Recorte por tipo de consulta do JurisTCU, 50 consultas cada, com IC 95% por
bootstrap (10.000 reamostragens de consultas):

| Configuração | pergunta (LLM) | expressão (LLM) | **consulta real (log)** |
|---|---:|---:|---:|
| BM25 (baseline) | 0,3214 [0,273–0,371] | 0,2920 [0,242–0,342] | 0,1335 [0,091–0,179] |
| BM25 sem relatório | 0,3669 [0,316–0,417] | 0,3463 [0,294–0,396] | 0,1547 [0,106–0,207] |
| recorte + fusão (CV) | 0,4041 [0,353–0,456] | 0,3799 [0,329–0,429] | **0,1640** [0,116–0,216] |
| **fusão das 4** | **0,4166** [0,363–0,470] | **0,3900** [0,336–0,442] | 0,1578 [0,111–0,208] |

| Tipo | ganho da fusão das 4 sobre o BM25 |
|---|---:|
| pergunta sintética (LLM) | **+29,6%** |
| expressão sintética (LLM) | **+33,6%** |
| **consulta real de log** | **+18,2%** |

Este é o recorte que costuma desmontar melhoria: as consultas reais de log são
as mais difíceis (nDCG@10 de 0,13 contra 0,32 das sintéticas) e as menos
parecidas com o que o método foi desenhado para atacar. **O ganho se mantém nos
três grupos**, ainda que menor nas reais — e, nelas, a configuração com recorte
+ fusão por CV (0,1640) supera a fusão das quatro (0,1578). Os ICs se
sobrepõem, como esperado com n = 50 por grupo; a afirmação é de consistência da
direção, não de diferença entre grupos.

> Os valores por consulta usam o desempate por `doc_id` descrito em
> [../03-empate-de-score.md](../03-empate-de-score.md). Por isso a média
> ponderada dos três grupos não reproduz exatamente o valor da tabela
> principal, que vem do `ranx.evaluate` direto: a diferença é da ordem de
> 0,0005.

## As três configurações recomendadas

Não há uma resposta só. Há três pontos na curva de custo × qualidade, e o
artigo deve apresentar os três:

| Se você quer... | Configuração | nDCG@10 | Custo |
|---|---|---:|---|
| o melhor custo-benefício | BM25, sem o relatório | 0,2904 (+16,8%) | **um** índice, com **1/3** do tamanho |
| o melhor com índice enxuto | recorte + fusão por CV | 0,3160 (+27,1%) | dois índices de 1/3, duas buscas |
| o melhor resultado | fusão das 4, peso igual | **0,3215 (+29,3%)** | dois índices completos + dois recortados, quatro buscas |

Em palavras, a recomendação do meio-termo:

> Segmentar o acórdão nas suas macro-seções (basta o segmentador por regras:
> a estrutura ouro não é necessária), **indexar tudo menos o relatório**,
> recuperar com BM25 e com um retriever denso, e **combinar os dois rankings**.
> Os índices ficam com um terço do tamanho e o nDCG@10 sobe 27%.

## Ressalvas honestas

1. **A `fixed_512_256` foi escolhida por ser a melhor sob recorte.** Isso é
   uma escolha informada pelos dados. A tabela equivalente para as outras
   quatro estratégias está em
   [01-recorte-por-secao.md](01-recorte-por-secao.md) e
   [03-fusao-hibrida.md](03-fusao-hibrida.md), e o padrão é o mesmo em todas —
   nenhuma conclusão depende dessa escolha.
2. **A escolha de descartar *o relatório* entre as quatro seções foi informada
   pelo teste exploratório de 07/09**, sobre o mesmo conjunto de avaliação. O
   que impede que isso seja um ajuste ao acaso é o controle aleatório, não a
   validação cruzada.
3. **A fusão das quatro não tem hiperparâmetro**, e é por isso que ela é a
   linha 1 da tabela mesmo empatando com a linha 2. A linha 2 exigiu validação
   cruzada para ser reportável; a linha 1, não.
4. **Corpus de 12.880 acórdãos**, como toda a F5. A decisão de corpus
   (12.880 × 113.827) continua aberta e vale igualmente para estes números.
