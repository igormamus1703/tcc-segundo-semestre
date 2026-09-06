# Números medidos × números publicados no artigo

**Data:** 2026-09-06 (revisto) · **Autor:** Leonardo Marques

> **Regra:** nenhum número entra na versão final do artigo sem estar nesta
> tabela, com o artefato que o comprova. Os valores da coluna "artigo hoje" vêm
> de uma rodada de agosto sobre um corpus que o código **não produz mais**
> (ver [02-achado-corpus.md](02-achado-corpus.md)).

## 1. Tabela de substituição

| Item | Artigo/pôster hoje | **Medido** | Onde corrigir |
|---|---:|---:|---|
| Documentos indexáveis | 113.827 | **12.880** | §Materials, Tabela I, Fig. 2, pôster |
| Mediana de tokens/doc | 7.347 | **11.426** | §Materials, Fig. 2, pôster |
| p90 de tokens/doc | 24.163 | **38.390** | §Materials, Fig. 2 |
| p99 de tokens/doc | 71.480 | **105.313** | §Materials, Fig. 2 |
| Média de tokens/doc | 11.651 | **18.174** | (usada nos cálculos de custo) |
| Match do join (F1) | 97,9% | **98,7%** | §Stages F1, pôster |
| Qrels preservados (F1) | 99,2% | **99,69%** | §Stages F1, pôster |
| Acurácia do segmentador (F2) | 92,7% | **92,2%** | §Stages F2, pôster |
| Taxa de fallback (F2) | 1,6% | **0,0%** | §Stages F2, pôster |
| Python | 3.11 | **3.13.7** | §Infrastructure |
| Composição por seção | relatório 72,5%, ementa 1,0% | **relatório 69,9%, ementa 1,3%** | §Materials, Fig. 2 |

Artefatos: `results/corpus/eda_stats.json`,
`results/corpus/segmenter_validation.json`,
`juris-chunking/data/interim/join_report.json`.

## 2. Números NOVOS, que o artigo ainda não tem

Todos medidos nesta branch. Os três primeiros são achados originais.

| Número | Valor | Documento |
|---|---:|---|
| **Relevância concentrada na fundamentação** | **72,0%** da relevância em 22,8% do texto (3,2x) | [03-analise-do-dominio.md](03-analise-do-dominio.md) |
| Posição mediana do trecho relevante | **79%** do documento | idem |
| Nosso BM25 vs JurisTCU (mesmos grupos) | razão estável de **0,51–0,60** | idem |
| Chunks gerados | **2.200.767** nas 5 estratégias | [resultados/02-benchmark-gpu.md](resultados/02-benchmark-gpu.md) |
| structural_gold vs pred (nº de chunks) | diferença de **0,48%** | idem |
| nDCG@10 BM25 (5 estratégias) | **0,2412 a 0,2526** | [resultados/01-bm25.md](resultados/01-bm25.md) |
| Significância (10 pares) | **nenhum p < 0,05** (menor: 0,097) | idem |
| Consultas reais vs sintéticas | **0,139 vs 0,312** (2,2x) | idem |

## 2b. RESULTADOS — a tabela principal do artigo

Estado em 06/09/2026, 11h. **Parcial**: faltam as duas estratégias fixas no
denso, rodando (`fixed_1024_512`, `fixed_512_256`).

| Estratégia | BM25 nDCG@10 | Denso nDCG@10 |
|---|---:|---:|
| structural_pred | **0,2526** | 0,1912 |
| structural_gold | 0,2521 | 0,1847 |
| fixed_1024_512 | 0,2510 | *(rodando)* |
| fixed_512_256 | 0,2486 | *(rodando)* |
| recursive_default | 0,2412 | **0,1967** |

Fontes: `results/experiments/20260906-0515_bm25/tables/main_results.csv` e
`20260906-0547_dense_bge_m3/tables_com_bm25/main_results.csv`.

### Os três resultados que o artigo pode afirmar

**1. O BM25 supera o retriever denso, com significância forte.**

| Comparação (mesma estratégia) | p | vitórias BM25 / empates / vitórias denso |
|---|---:|---|
| structural_gold | **0,000005** | 83 / 25 / 42 |
| structural_pred | **0,000010** | 83 / 21 / 46 |
| recursive_default | **0,002189** | 80 / 23 / 47 |

É o **único** resultado significativo do trabalho, e é contraintuitivo. Coerente
com `pereira2026jua` (baselines lexicais competitivas em RI jurídica em
português) e com o JurisTCU, onde os modelos BERT-based foram os piores.

**2. A estratégia de chunking não altera a recuperação — em nenhum retriever.**
BM25: nenhum p < 0,05 entre as cinco (menor: 0,097). Denso: nenhum p < 0,05
entre as três (menor: 0,213). Com análise de poder declarada: 150 consultas
detectam diferenças a partir de ~0,016–0,022 em nDCG@10, e as diferenças
observadas entre estratégias são de 0,001 a 0,012.

**3. O erro do segmentador não custa desempenho.**
`structural_gold` × `structural_pred`: p = 0,827 no BM25 e 0,283 no denso, com
o **predito** à frente nos dois. 97 empates em 150 consultas no BM25. Um
segmentador por regras com 92,2% de acurácia entrega o mesmo que a estrutura
ouro — a conclusão prática mais útil do trabalho, e a ablação que o BR-TaxQA-R
não tem.

### Um achado que muda a redação da hipótese

**A ordem das estratégias se inverte entre os retrievers.** O
`recursive_default` é o pior dos cinco no BM25 e o melhor dos três no denso.
As estruturais fazem o caminho contrário. Nenhuma dessas diferenças é
significativa, mas a inversão é consistente e merece ser reportada — ela é
evidência **contra** um efeito estável do chunking estrutural, não a favor.

## 3. Composição do corpus por seção (para refazer a Figura 2)

Medido sobre 3.000 documentos, em fração de caracteres:

| Seção | % do corpus | % da relevância julgada |
|---|---:|---:|
| relatório | 69,9% | 25,7% |
| fundamentação | 22,8% | **72,0%** |
| dispositivo | 6,0% | 1,8% |
| ementa | 1,3% | 0,4% |

**A Figura 2 do artigo deve passar a mostrar as duas colunas**, não só a
primeira. O contraste entre "quanto ocupa" e "quanto importa" é o achado, e uma
figura com as duas séries lado a lado comunica isso de imediato.

## 4. Presença de seção (quantos documentos têm cada uma)

| Seção | Presença |
|---|---:|
| dispositivo | **100,0%** |
| relatório | 99,98% |
| fundamentação | 99,88% |
| ementa | 99,87% |

Contra 97,4%–99,9% no corpus de 113k: o corpus filtrado é **estruturalmente
mais completo**, o que faz sentido — são os acórdãos que o próprio TCU
selecionou para virar jurisprudência.

## 5. Escala e custo (medidos, não estimados)

| Estratégia | Chunks | Tokens/chunk | Horas de encode (RTX 5060, fp16) |
|---|---:|---:|---:|
| fixed_512_256 | 907.914 | 423 | 2,48 |
| fixed_1024_512 | 450.786 | 842 | 2,67 |
| recursive_default | 270.070 | 770 | 1,56 |
| structural_gold | 286.689 | 773 | 1,70 |
| structural_pred | 285.308 | 770 | 1,68 |
| **Total** | **2.200.767** | | **10,09** |

Em CPU seriam **127 h**. No corpus de 113.827 documentos, ~19,5 M chunks e
~9 dias de CPU — a diferença entre caber e não caber no cronograma.

## 6. Correções de texto que não são numéricas

1. **"Python 3.11"** → **3.13.7**; o risco registrado de incompatibilidade do
   `ranx`/numba com 3.13 não se materializou.
2. **"~100k documents ... compatible with personal hardware and Google Colab"**
   → não se sustenta (9 dias de CPU nessa escala). Com 12.880 documentos e GPU,
   a afirmação passa a ser verdadeira.
3. **Escolha do embedder** → o critério decisivo foi a **janela de contexto**,
   não a posição no MTEB-BR. Ver [05-modelos-embedding.md](05-modelos-embedding.md).
4. **Limitação nova a declarar:** o corpus é formado apenas por acórdãos que
   originaram enunciados do JurisTCU — documentos previamente selecionados como
   jurisprudencialmente relevantes. A coleção é enviesada nesse sentido, e a
   tarefa é mais fácil que buscar no acervo completo.
5. **Limitação nova a declarar:** os qrels do JurisTCU vêm de um *pool* (BM25 +
   BERT + reranker T5), então documentos que nenhum daqueles sistemas recuperou
   nunca foram julgados. É um argumento a mais para reportar Recall@100 ao lado
   do nDCG@10.
6. **Limitação já reconhecida, manter:** a relevância foi julgada sobre o
   excerto e transferida ao acórdão íntegro que o contém.
