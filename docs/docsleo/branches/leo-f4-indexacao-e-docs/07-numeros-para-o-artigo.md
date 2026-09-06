# Números medidos × números publicados no artigo

**Data:** 2026-09-05 · **Autor:** Leonardo Marques
**Origem:** rodada completa do pipeline nesta data (download 6 GB → `src.ingest`
→ `src.segmenter.validate`), com o código como está no `main`.

> Este documento existe para uma coisa só: **nenhum número entra na versão final
> do artigo sem estar nesta tabela.** Os valores da coluna "artigo hoje" vêm de
> uma rodada de agosto sobre um corpus que o código não produz mais
> (ver [02-achado-corpus.md](02-achado-corpus.md)).

## Tabela de substituição

| Item | Artigo/pôster hoje | **Medido (05/09)** | Onde corrigir |
|---|---|---|---|
| Documentos indexáveis | 113.827 | **12.880** | §Materials, Tabela I, Fig. 2, pôster |
| Mediana de tokens/doc | 7.347 | **11.426** | §Materials, Fig. 2, pôster |
| p90 de tokens/doc | 24.163 | **38.390** | §Materials, Fig. 2 |
| p99 de tokens/doc | 71.480 | **105.313** | §Materials, Fig. 2 |
| Média de tokens/doc | 11.651 | **18.174** | (não citada, mas usada em custo) |
| Match do join (F1) | 97,9% | **98,7%** | §Stages F1, pôster |
| Qrels preservados (F1) | 99,2% | **99,69%** | §Stages F1, pôster |
| Acurácia do segmentador (F2) | 92,7% | **92,2%** | §Stages F2, pôster |
| Taxa de fallback (F2) | 1,6% | **0,0%** | §Stages F2, pôster |
| Python | 3.11 | **3.13.7** | §Infrastructure |
| Composição por seção | relatório 72,5%, ementa 1,0% | **a refazer** (Fig. 2) | §Materials, Fig. 2 |

Artefatos que comprovam: `results/tables/eda_stats.json`,
`results/tables/segmenter_validation.json`,
`juris-chunking/data/interim/join_report.json`.

## O que os números novos dizem (e é bom para o TCC)

### 1. Os documentos são MAIORES do que pensávamos — a premissa fica mais forte

A mediana subiu de 7.347 para **11.426 tokens** (+55%), e a média de 11.651
para 18.174. Não é erro: os acórdãos que originaram enunciados de
jurisprudência no JurisTCU são justamente os mais substantivos do acervo, não
os típicos.

Isso **reforça** a motivação do trabalho. O gate de viabilidade do
`plano_tecnico.md` exigia mediana acima de ~1.000 tokens para que a estratégia
de chunking tivesse efeito mensurável — estamos **11x acima** desse piso. Com
p99 de 105 mil tokens, há acórdãos que geram mais de 400 chunks sozinhos.

### 2. O segmentador não perdeu nada com a troca de corpus

| | 113k docs (agosto) | 12.880 docs (agora) |
|---|---|---|
| Acurácia por caractere | 92,7% | **92,2%** |
| Fallback | 1,6% | **0,0%** |

Meio ponto percentual de diferença — dentro do que se espera ao trocar a
amostra. E o **fallback caiu para zero**: todo documento do corpus teve pelo
menos um marcador estrutural reconhecido, nenhum caiu no caso "documento
inteiro como indefinido".

> 📝 Isso é um argumento a usar na banca: a regra de segmentação foi calibrada
> num corpus de 113 mil acórdãos e **generaliza** para o subconjunto sem
> recalibração. Não é overfitting nas regras.

### 3. A cobertura estrutural é quase perfeita

| Seção | Presença nos docs |
|---|---|
| dispositivo | **100,0%** |
| relatório | 99,98% |
| fundamentação | 99,88% |
| ementa | 99,87% |

Contra 97,4%–99,9% no corpus de 113k. Ou seja: o corpus filtrado é
**estruturalmente mais completo** — o que faz sentido, já que são os acórdãos
que o próprio TCU selecionou para virar jurisprudência.

### 4. Ponto fraco a discutir com honestidade: precisão da ementa

| Seção | Cobertura | Precisão |
|---|---|---|
| relatório | 92,2% | 98,3% |
| fundamentação | 91,1% | 96,4% |
| dispositivo | 98,7% | **74,3%** |
| ementa | 93,6% | **50,2%** |

A ementa tem **50% de precisão**: o segmentador prevê como ementa cerca do
dobro de caracteres do que realmente é ementa (12,0M preditos vs 6,5M reais).
O dispositivo também super-prediz (44,2M vs 33,3M).

**Interpretação:** a ementa é a menor seção (só ~0,5% dos caracteres do corpus)
e não tem marcador textual próprio de abertura — o segmentador acaba
absorvendo o começo do relatório nela. Como o `structural_pred` nunca cruza
fronteira de seção, esse erro **desloca conteúdo entre chunks vizinhos** em vez
de perdê-lo.

É exatamente isso que a ablação `structural_gold` vs `structural_pred` foi
desenhada para medir: a diferença entre as duas **é** o custo do erro de
segmentação. Se as duas empatarem, mostramos que 92% de acurácia já é
suficiente — que é um resultado interessante por si só.

## Escala do experimento — MEDIDA no corpus completo

`python -m src.chunkers.run --strategy all` sobre os 12.880 documentos:

| Estratégia | Chunks | Chunks/doc | Tamanho em disco |
|---|---|---|---|
| fixed_512_256 | **907.914** | 70,5 | 1,7 GB |
| fixed_1024_512 | **450.786** | 35,0 | 1,6 GB |
| recursive_default | **270.070** | 21,0 | 869 MB |
| structural_gold | **286.689** | 22,3 | 920 MB |
| structural_pred | **285.308** | 22,2 | 921 MB |
| **Total** | **2.200.767** | — | **6,0 GB** |

> 📝 **Dado interessante para o artigo:** `structural_gold` (286.689) e
> `structural_pred` (285.308) produzem quantidades de chunks quase idênticas —
> diferença de **0,48%**. O segmentador, mesmo com 92,2% de acurácia, gera uma
> granularidade praticamente igual à da estrutura ouro. Se as métricas de
> recuperação também ficarem próximas, é evidência forte de que **não é preciso
> ter a estrutura ouro** para colher o benefício do chunking estrutural — o que
> é justamente o cenário realista de um pipeline em produção.

Também vale reparar que o `recursive_default` (270k) fica mais próximo das
estratégias estruturais (~286k) do que das fixas — os três operam numa faixa de
granularidade comparável, enquanto o `fixed_512_256` gera 3,4x mais chunks. Isso
**é exatamente o controle que faltou no BR-TaxQA-R** (ver
[03-referencias-verificadas.md](03-referencias-verificadas.md)).

Custo do encode denso — agora com a taxa **medida**, não estimada. Benchmark
com `multilingual-e5-base` em CPU (10 threads torch, batch 64, chunks reais):
**128 chunks em 26,7 s = 4,8 chunks/s**.

| Cenário | Chunks | CPU (4,8/s) | GPU T4 (~300/s) |
|---|---:|---|---|
| Corpus 12.880, 5 estratégias | 2.200.767 | **127 h ≈ 5,3 dias** | ~2 h |
| Corpus 113.827, 5 estratégias | ~19,5 M | ~47 dias | ~18 h |

⚠️ **O retriever denso não roda em CPU dentro do cronograma.** Precisamos de
GPU (Colab resolve) ou de reduzir o escopo do denso. Ver
[08-decisoes-pendentes.md](08-decisoes-pendentes.md), item 1b.

## Correções de texto que não são numéricas

1. **"Python 3.11"** → o pipeline roda em **3.13.7**; o risco registrado de
   incompatibilidade do `ranx`/numba com 3.13 não se materializou.
2. **"~100k documents ... compatible with personal hardware and Google Colab"**
   → não se sustenta: são 5,6 dias de CPU. Com 12.880 documentos a afirmação
   passa a ser verdadeira.
3. **Limitação a declarar (nova):** o corpus é formado apenas por acórdãos que
   originaram enunciados do JurisTCU, ou seja, documentos previamente
   selecionados como jurisprudencialmente relevantes. A coleção é enviesada
   nesse sentido, e a tarefa é mais fácil do que buscar no acervo completo.
4. **Limitação já reconhecida, manter:** a relevância foi julgada sobre o
   excerto e é transferida ao acórdão íntegro que o contém.
