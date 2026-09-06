# Resultados preliminares — BM25 (5 estratégias)

**Data:** 2026-09-06 · **Autor:** Leonardo Marques
**Status:** primeiro número da tabela — marco da Semana 7 do cronograma ✅
**Corpus:** 12.880 acórdãos · 150 consultas · 2.219 pares de qrel

> ⚠️ Estes números valem para o corpus de 12.880 documentos. Se a equipe decidir
> mudar o corpus ([08-decisoes-pendentes.md](../08-decisoes-pendentes.md), item 1),
> tudo aqui precisa ser refeito.

## Tabela principal

```bash
python -m src.run_experiments --strategy all --retriever bm25   # ~25 min
python -m src.evaluate
```

| Estratégia | nDCG@10 | MRR@10 | MAP@10 | Recall@100 |
|---|---|---|---|---|
| **structural_pred** | **0,2526** | 0,5010 | 0,1017 | 0,4863 |
| structural_gold | 0,2521 | 0,5068 | **0,1024** | 0,4849 |
| fixed_1024_512 | 0,2510 | 0,5061 | 0,1013 | **0,4861** |
| fixed_512_256 | 0,2486 | **0,5186** | 0,0963 | 0,4709 |
| recursive_default | 0,2412 | 0,4731 | 0,0931 | 0,4731 |

Artefatos: `results/tables/main_results.csv`, `significance.csv`,
`results/runs/*.trec`.

## O resultado honesto: nenhuma diferença é significativa

Todos os 10 pares comparados, com correção para comparações múltiplas:

| Par | p-valor | Significativo? |
|---|---|---|
| fixed_1024_512 × recursive_default | 0,097 | ❌ |
| recursive_default × structural_pred | 0,114 | ❌ |
| recursive_default × structural_gold | 0,122 | ❌ |
| fixed_512_256 × recursive_default | 0,282 | ❌ |
| fixed_512_256 × structural_pred | 0,638 | ❌ |
| fixed_512_256 × structural_gold | 0,686 | ❌ |
| fixed_1024_512 × fixed_512_256 | 0,770 | ❌ |
| fixed_1024_512 × structural_pred | 0,808 | ❌ |
| structural_gold × structural_pred | 0,827 | ❌ |
| fixed_1024_512 × structural_gold | 0,860 | ❌ |

**Nenhum p < 0,05.** As estratégias estruturais aparecem no topo, mas a
diferença para o `fixed_1024_512` é de 0,0016 em nDCG@10 — ruído. Não é
possível afirmar, com BM25, que o chunking estrutural melhora a recuperação.

Isso é um **resultado nulo bem medido**, que o `plano_tecnico.md` §7 já
antecipava como desfecho legítimo: *"Nada disso exige que a hipótese se
confirme. Um resultado nulo bem medido, com recortes que mostram onde cada
estratégia ganha, é um TCC completo."*

## Dois achados que valem a pena, apesar do resultado nulo

### 1. O erro do segmentador não custa desempenho — e isso é um resultado

`structural_gold` (spans ouro das colunas do CSV) × `structural_pred` (spans do
nosso segmentador, 92,2% de acurácia):

- nDCG@10: **0,2521 vs 0,2526** — o *predito* fica marginalmente **à frente** do ouro
- p = 0,827
- **97 empates em 150 consultas** — em ~2/3 das consultas o ranking é idêntico
- contagem de chunks: 286.689 vs 285.308 (**0,48%** de diferença)

Ou seja: **não é preciso ter a estrutura ouro**. Um segmentador por regras com
92% de acurácia entrega exatamente o mesmo resultado de recuperação que a
estrutura perfeita. Para quem for aplicar isso num acervo real — onde não existe
coluna `SUMARIO`/`RELATORIO`/`VOTO` pronta — essa é a conclusão prática mais
útil do trabalho.

É também o que separa este trabalho do BR-TaxQA-R, que não tem essa ablação.

### 2. O recursivo é consistentemente o pior

`recursive_default` fica por último em nDCG@10, MRR@10 e MAP@10, e é o único
par que chega perto da significância contra as demais (p = 0,097–0,122). A
tendência é consistente, só não tem força estatística com 150 consultas.

Interessante porque o recursivo é **o padrão de facto** dos pipelines RAG (é o
`RecursiveCharacterTextSplitter` que todo tutorial usa). Se a tendência se
confirmar no retriever denso, o achado vira: *o default do mercado é a pior
opção das cinco* — que é uma mensagem forte e acionável.

## Por que BM25 provavelmente é o cenário MENOS favorável à hipótese

Vale registrar antes de rodar o denso, para não parecer racionalização depois.

O BM25 casa **termos**. Com agregação por `max_pooling`, basta que o termo da
consulta caia em **algum** chunk do documento para o documento pontuar — e a
fronteira do chunk quase não altera isso, já que o termo continua presente onde
quer que o corte aconteça. O chunking mexe sobretudo na normalização por
tamanho do documento (o `avgdl` do BM25), não em quais termos existem.

O retriever **denso** é outra história: o embedding é uma média semântica do
trecho. Um chunk que atravessa a fronteira relatório→voto mistura "o que as
partes alegaram" com "o que o relator decidiu" — dois conteúdos que, num
acórdão, dizem coisas diferentes e às vezes opostas. É aí que respeitar a
fronteira deveria importar.

**Previsão registrada antes de rodar** (para poder ser contrariada): a
diferença entre estrutural e fixo deve ser maior no denso do que no BM25. Se
não for, a conclusão do trabalho passa a ser que o chunking estrutural não
ajuda a recuperação em acórdãos, nem no cenário mais favorável — o que continua
sendo um resultado publicável, e mais forte por ter sido testado onde deveria
funcionar.

## Recortes analíticos

### Por tipo de consulta — o efeito mais forte de todos

Os três grupos do JurisTCU, 50 consultas cada (nDCG@10):

| Estratégia | LLM (pergunta) | expressão da pergunta | **search log (usuário real)** |
|---|---|---|---|
| structural_pred | 0,3118 | **0,3069** | **0,1390** |
| structural_gold | 0,3180 | 0,2997 | 0,1386 |
| fixed_1024_512 | 0,3151 | 0,3055 | 0,1323 |
| fixed_512_256 | **0,3214** | 0,2920 | 0,1322 |
| recursive_default | 0,3139 | 0,2793 | 0,1305 |

**O achado aqui não é o chunking — é o tipo de consulta.** Consultas reais de
log de busca rendem **menos da metade** do nDCG das consultas sintéticas
(0,13 vs 0,31). A diferença entre o melhor e o pior chunking dentro de um mesmo
grupo é de ~3–10%; a diferença entre grupos de consulta é de **~130%**.

Isso merece uma frase na Discussão: **a escolha da estratégia de chunking é uma
decisão de segunda ordem perto da natureza da consulta.** Também é um alerta
metodológico para a área — avaliar RAG jurídico só com consultas sintéticas
geradas por LLM superestima o desempenho em mais de 2x em relação ao que o
usuário real obtém.

### Por tamanho de documento — a tendência que sustenta a hipótese

Tercis com 50 consultas cada (nDCG@10):

| Estratégia | curto | médio | **longo** |
|---|---|---|---|
| structural_gold | 0,2681 | 0,2394 | **0,2489** 🥇 |
| structural_pred | **0,2703** 🥇 | 0,2386 | 0,2488 🥈 |
| fixed_1024_512 | 0,2684 | **0,2532** 🥇 | 0,2313 ⬇️ **último** |
| fixed_512_256 | 0,2596 | 0,2518 | 0,2356 |
| recursive_default | 0,2555 | 0,2363 | 0,2319 |

**A ordem se inverte entre os tercis.** O `fixed_1024_512` é o **melhor** em
documentos médios e o **pior** em documentos longos; as estratégias estruturais
fazem exatamente o caminho contrário (3º/4º em médios, 1º/2º em longos).

Isso é o que a hipótese do trabalho prevê: quanto mais longo o acórdão, mais
fronteiras de seção existem para uma janela fixa atravessar, e mais custa
ignorá-las. Em documentos longos, as estruturais ficam **+7,6%** acima do
`fixed_1024_512`.

⚠️ **Mas os intervalos de confiança se sobrepõem amplamente** (ex.: longo,
structural_gold IC95 [0,194–0,305] × fixed_1024_512 [0,178–0,286]). Com 50
consultas por tercil **não há poder estatístico** para afirmar a diferença.
É uma **tendência consistente com a hipótese, não uma confirmação** — e é assim
que precisa ser escrito no artigo. O teste no retriever denso vai dizer se ela
se sustenta.

## Correção metodológica feita no caminho

A primeira versão do recorte por tamanho classificava as consultas usando os
percentis de tamanho dos **12.880 documentos do corpus**. Resultado: os tercis
saíram com **3, 67 e 80** consultas — um grupo de 3 não sustenta comparação
nenhuma.

A causa: os documentos julgados relevantes são sistematicamente **maiores** que
o acervo (são os acórdãos mais substantivos, que é justamente por isso que
viraram jurisprudência). Cortar pelos percentis do corpus joga quase todas as
consultas nos tercis superiores.

Corrigido para cortar pelos percentis da **distribuição das consultas** (a
mediana de tamanho dos relevantes de cada uma), o que dá 50/50/50 por
construção. Está em `query_length_terciles()`, com teste que trava o
comportamento.

## O que falta

- [ ] Runs densos (5 estratégias) — ~24 h de CPU ou ~2 h de GPU
- [ ] Recortes: por tipo de consulta, por tercil de tamanho, por retriever
      (já gerados para BM25 em `results/tables/slices_*.csv`)
- [ ] Sensibilidade da agregação: `sum_top_k` vs `max_pooling`
- [ ] Bootstrap dos ICs para a tabela final
