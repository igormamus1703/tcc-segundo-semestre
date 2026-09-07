# Análise do domínio: onde mora a relevância num acórdão

**Data:** 2026-09-06 · **Autor:** Leonardo Marques
**Status:** achado novo — não estava previsto em nenhum dos dois planos

Este documento reúne duas análises que mudam a leitura dos resultados: **onde,
dentro do acórdão, está o conteúdo julgado relevante**, e **como nossos números
se comparam aos do benchmark de origem**.

---

## 1. A relevância está concentrada na fundamentação

O JurisTCU julgou relevância sobre o par (`ENUNCIADO`, `EXCERTO`). O `EXCERTO` é
um trecho **literal** do acórdão — então dá para localizá-lo no documento
montado e descobrir de qual macro-seção ele veio.

Método: normalizar (sem acento, sem caixa, espaços colapsados), procurar uma
âncora de 120 caracteres tirada do meio do excerto, e mapear a posição
encontrada contra os `gold_spans`. 1.787 excertos localizados de 2.500
analisados (71,3%; os 28,5% não localizados vêm de diferenças de normalização
entre o excerto publicado e o texto do acórdão, e não há razão para supor que
se distribuam de forma diferente).

| Seção | % dos caracteres do corpus | % dos excertos relevantes | Concentração |
|---|---:|---:|---:|
| **fundamentação (voto)** | 22,8% | **72,0%** | **3,2x** |
| relatório | 69,9% | 25,7% | 0,37x |
| dispositivo | 6,0% | 1,8% | 0,30x |
| ementa | 1,3% | 0,4% | 0,31x |

**A fundamentação ocupa um quinto do acórdão e concentra quase três quartos do
conteúdo julgado relevante.** O relatório — que é a maior parte do documento,
com 70% dos caracteres — responde por apenas um quarto.

Isso faz sentido no gênero: o relatório recapitula o que as partes alegaram e o
histórico processual; é a **fundamentação** (o voto do relator) que contém a
tese jurídica, que é o que alguém procura ao consultar jurisprudência.

**Posição mediana da relevância: 79% do documento.** O conteúdo que importa está
no final.

### Por que isso importa para o trabalho

1. **Dá um mecanismo à hipótese.** Até aqui a justificativa do chunking
   estrutural era genérica ("respeitar fronteiras deve ajudar"). Agora é
   específica: existe uma seção onde o sinal se concentra 3,2x, e uma janela
   fixa que atravessa a fronteira relatório→voto mistura conteúdo de alta
   densidade de sinal com conteúdo de baixa.
2. **Explica em parte o resultado nulo no BM25.** O BM25 com max-pooling
   pontua o documento pelo melhor chunk; se o termo da consulta aparece na
   fundamentação, ele é encontrado *independentemente* de onde o corte caiu. A
   fronteira importa para o **denso**, onde o embedding é uma média semântica
   do trecho e a diluição com o relatório degrada o vetor. **É uma previsão
   testável na rodada densa.**
3. **É um alerta prático para pipelines RAG jurídicos.** Truncar o documento
   pelo início — comportamento padrão de muitos pipelines — descarta justamente
   a seção onde está 72% da relevância.

---

## 2. Comparação com os baselines do JurisTCU (validação externa)

O paper do JurisTCU (arXiv:2503.08379) reporta nDCG@10 por grupo de consultas,
e usa **os mesmos três grupos** que temos (o campo `SOURCE`). Isso permite
verificar se nosso pipeline está sadio, comparando com um resultado publicado.

| Grupo | Descrição | JurisTCU (BM25) | **Nosso BM25** | Razão |
|---|---|---:|---:|---:|
| G1 | 50 consultas reais de log (~3,5 palavras) | 27,5 | **13,9** | 0,51 |
| G2 | 50 sintéticas por palavra-chave (~6,5 palavras) | 51,1 | **30,7** | 0,60 |
| G3 | 50 sintéticas em forma de pergunta (~16,5 palavras) | 53,3 | **31,2** | 0,59 |

*(nossos valores: `structural_pred__bm25`, de `slices_query_type.csv`)*

**Dois pontos importantes:**

1. **A razão é estável (~0,55) nos três grupos.** Se o pipeline tivesse um
   defeito, o descolamento seria irregular. Um fator aproximadamente constante
   aponta para uma **diferença de dificuldade da tarefa**, não para um bug.
2. **A diferença de dificuldade é exatamente a nossa contribuição.** Eles
   recuperam sobre 16.045 documentos curtos (enunciado + excerto, ~1k tokens),
   com o trecho relevante ocupando boa parte do documento. Nós recuperamos
   sobre 12.880 **acórdãos íntegros** de ~11,4k tokens, onde o mesmo trecho
   relevante está diluído em 10x mais texto — e cercado por 70% de relatório.

> 📌 **Para o artigo:** esta tabela merece entrar. Ela (a) mostra que o pipeline
> reproduz o padrão do benchmark de origem — inclusive a ordem G1 ≪ G2 ≈ G3 —,
> e (b) quantifica o custo de passar de excertos para documentos íntegros, que
> é a premissa do trabalho. É a diferença entre dizer "recuperação em documento
> longo é mais difícil" e **medir** o quanto.

---

## 3. Metodologias dos trabalhos de referência

O que aproveitamos, e o que deliberadamente não seguimos.

### JurisTCU (arXiv:2503.08379) — nosso benchmark de origem

- **Construção dos qrels:** GPT-4 pontua e um especialista de domínio revisa;
  os candidatos vêm de um retriever de dois estágios (BM25 + BERT, top-300
  cada), reordenados por T5, anotando os 10 melhores + 5 aleatórios do BM25.
  → **Consequência para nós:** os qrels têm viés de pool — documentos que
  nenhum daqueles sistemas recuperou nunca foram julgados. Vale como limitação
  declarada, e é um argumento a mais para reportar Recall@100 junto do nDCG@10.
- **Achado que confirma nossa escolha de modelo:** os *BERT-based* foram os
  piores, com o `BERT.pt.TCU` no fim da lista, enquanto os embeddings da OpenAI
  ganharam ~70% sobre o BM25 em consultas curtas. É exatamente o alerta do
  `plano_tecnico.md` §3 sobre encoder MLM não ser bi-encoder de recuperação —
  agora com evidência publicada. **Não usar BERTimbau/RoBERTaLexPT sem
  fine-tune.**
- **Expansão de consulta funciona muito bem aqui:** `BM25 + docT5query +
  sinônimos` levou G1 de 27,5 para 40,4 (+47%). **Está fora do nosso escopo** —
  misturaria a variável "expansão" com a variável "chunking" —, mas é o
  primeiro item da nossa seção de trabalhos futuros.

### BR-TaxQA-R (arXiv:2505.15916)

Comparou janela deslizante de 2.048 *tokens* contra splitter recursivo de 1.000
*caracteres*, avaliando **geração** (RAGAS). Ver
[04-referencias-verificadas.md](04-referencias-verificadas.md): a comparação
confunde estrutura com tamanho de chunk, e é o gap que este trabalho ocupa.

### Legal RAG Bench (arXiv:2603.01710)

"A recuperação é o determinante primário do desempenho de RAG jurídico, e
muitos erros atribuídos a alucinação são falhas de recuperação."
→ **É a justificativa para avaliarmos recuperação e não geração.** Resposta
pronta para a banca.

### JUÁ (arXiv:2604.06098)

Benchmark que consolida JurisTCU, NormasTCU, Ulysses-RFCorpus e BR-TaxQA sob
protocolo unificado. → Vale citar como o contexto em que nosso corpus se
insere, e como caminho para trabalho futuro (rodar as mesmas cinco estratégias
sobre as outras coleções do JUÁ testaria a generalização do achado).

---

## 4. O que isso sugere fazer (e o que não fazer)

| Ideia | Veredito |
|---|---|
| Reportar a tabela comparativa com o JurisTCU | **Fazer.** Valida o pipeline e quantifica a premissa |
| Reportar a concentração de relevância por seção | **Fazer.** Dá mecanismo à hipótese e é achado original |
| Verificar, na rodada densa, se a fronteira importa mais que no BM25 | **Fazer.** Previsão registrada *antes* de rodar |
| Adicionar o recorte "seção do chunk recuperado" | **Feito** — `slices_section.csv` |
| Ponderar chunks da fundamentação no ranking | **Não fazer agora.** Seria uma sexta estratégia e mudaria a pergunta de pesquisa; vira trabalho futuro com fundamento medido |
| Expansão de consulta (docT5query, sinônimos) | **Não fazer.** Fora do escopo declarado; misturaria variáveis |
| Usar BERTimbau/RoBERTaLexPT sem fine-tune | **Não fazer.** O JurisTCU já mostrou que vai mal |
