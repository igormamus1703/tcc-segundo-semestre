# Rascunho de texto para o artigo (a partir da F7)

**Data:** 05/10/2026 · **Autor:** Leonardo Marques
**Status:** rascunho para a equipe revisar. As chaves entre colchetes estão em
[`REFERENCIAS.md`](../../../../REFERENCIAS.md). Números com o artefato de
origem em cada doc desta pasta. **Nada aqui substitui a decisão de corpus**
(12.880 × 113.827), que continua aberta.

---

## Resumo (proposta, ~200 palavras)

> Acórdãos do Tribunal de Contas da União têm mediana de 11 mil *tokens*, e
> sistemas de busca os indexam em pedaços (*chunks*). Investigamos se cortar
> o documento respeitando suas macro-seções (ementa, relatório, fundamentação
> e dispositivo) melhora a recuperação, e qual parte do documento indexar.
> Sobre 12.880 acórdãos íntegros, avaliamos cinco estratégias de *chunking*,
> recuperação léxica e densa, fusão, *reranking* e um ranqueador aprendido,
> em três amostras de consultas: as 150 do JurisTCU [fernandes2025juristcu] e
> 7.567 do JUÁ-Juris [pereira2026jua], mapeadas para os mesmos documentos. Com
> poder estatístico, o *chunking* estrutural supera o fixo e o recursivo
> (+1% a +12% de nDCG@10, conforme a dificuldade da consulta), efeito que uma
> ablação atribui ao isolamento da ementa; o segmentador automático é
> estatisticamente equivalente à estrutura oficial. Remover do índice os
> trechos exclusivamente de relatório melhora o nDCG@10 nas três amostras
> (+5,5% a +15,6%), enquanto a regra ingênua de remover pedaços
> majoritariamente de relatório falha (−12,6%) por descartar a ementa junto.
> Um ranqueador treinado em consultas do JUÁ transfere ao JurisTCU (+18,6%) e
> atribui a um casamento no relatório cerca de um quinto do peso do mesmo
> casamento na fundamentação. Os resultados foram pré-registrados.

## Contribuições (lista para a Introdução)

1. **Uma avaliação com poder estatístico** do *chunking* estrutural em
   jurisprudência brasileira, com 7.717 consultas sobre os mesmos documentos,
   testes de equivalência [schuirmann1987tost; lakens2017equivalence] e
   pré-registro das hipóteses.
2. **A identificação de um modo de falha** da seleção de conteúdo por seção
   em *chunking* que não respeita fronteiras (o artefato da ementa), e de um
   critério que o corrige, confirmado em dados não vistos.
3. **A evidência, por um modelo aprendido e interpretável** [burges2010lambdamart;
   lundberg2020treeshap], de que o relatório do acórdão carrega sinal de
   recuperação muito mais fraco que a fundamentação, de forma estável entre
   coleções e tarefas.
4. **Uma alternativa sem LLM** à extração de teses [pereira2026nuggets]: a
   estrutura do gênero já entrega boa parte do que a extração busca.

## Resultados — parágrafos-base

**Chunking.** *Com 150 consultas, as cinco estratégias não se distinguem (F5).
Com as 1.567 consultas de teste do JUÁ-Juris, estratificadas por dificuldade,
o chunking estrutural supera o fixo de 512 tokens em 7,3% (p = 0,0001) e o
recursivo em 9,9% (p < 10⁻⁵); nas 6.000 consultas naturais, as diferenças
caem para 1,2% e 2,4%, ainda significativas. O segmentador por regras é
equivalente à estrutura ouro nas três amostras (TOST, margem ±0,01). A
vantagem desaparece quando a ementa é removida do índice estrutural (−20,9%
contra o fixo), o que a localiza no isolamento da ementa num chunk próprio.*

**Seleção de conteúdo.** *Remover do índice os pedaços cuja maioria dos
caracteres é de relatório melhora o nDCG@10 no JurisTCU (+16,2%) e nas
consultas naturais do JUÁ (+8,1%), mas o piora nas difíceis (−12,6%). A
análise das perdas mostra que, em 54% dos casos, o pedaço descartado continha
a ementa, que nas estratégias sem fronteira divide o primeiro chunk com o
relatório; o dano concentra-se no quartil de consultas lexicalmente mais
próximas da ementa (−28,4%). Descartar apenas pedaços inteiramente de
relatório elimina o modo de falha: +15,6%, +9,7% e +5,5% nas três amostras,
resultado pré-registrado e confirmado em consultas não usadas na análise.*

**Modelo aprendido.** *Um LambdaRank com doze sinais de busca por seção,
treinado em 6.000 consultas do JUÁ, supera o BM25 em 18,6% no JurisTCU, que
não participou do treino, e o mesmo modelo sem os sinais por seção em 16,5%
(p < 0,0001). Os valores SHAP mostram que, para o mesmo score normalizado, um
casamento na fundamentação contribui cerca de 0,75 e um no relatório cerca de
0,15 para a pontuação do documento, nas duas coleções.*

**Reranking.** *Um cross-encoder multilíngue sem ajuste [bge_reranker_v2_m3]
piora a melhor configuração no JurisTCU (−15,9%) e recupera o desempenho
quando impedido de ler passagens do relatório (+17,9%): a interferência do
relatório não é exclusiva da recuperação léxica.* **[completar com o reranker
ajustado — ver 05-reranker.md]**

## Discussão — pontos a desenvolver

- **O valor do relatório depende da tarefa.** Na busca por acórdãos que
  firmam uma tese (JurisTCU), o relatório gera casamentos que competem com os
  documentos certos; na busca por *o* acórdão de um enunciado (JUÁ), ele é a
  melhor evidência em 30% dos acertos. Um modelo aprendido reconcilia as duas
  tarefas melhor que qualquer regra fixa.
- **Estrutura e seleção interagem.** O efeito isolado do chunking estrutural
  é pequeno; seu valor aparece quando o pipeline seleciona conteúdo por
  seção. Dialoga com [qu2025semanticchunking] (chunking "inteligente" sem
  ganho consistente) e com [jimenoyepes2024financial] (chunking por elemento
  estrutural ajuda), conciliando os dois: depende do que o pipeline faz com a
  estrutura.
- **Relação com nuggets** [pereira2026nuggets]: eles extraem a tese com um
  LLM; nós a localizamos pela estrutura do gênero, sem custo de geração e com
  rastreabilidade. Medidos em documentos diferentes (excertos × acórdãos
  íntegros), os números não são comparáveis diretamente.
- **Por que BM25F** [robertson2004bm25f] explica o negativo da ponderação da
  F6: ponderar o score depois da saturação não equivale a ponderar a
  frequência antes dela. O LTR é a versão aprendida dessa ideia.

## Limitações (texto quase pronto)

> *Os resultados são condicionais às noções de relevância dos dois
> benchmarks: o JurisTCU julga excertos de jurisprudência, que tendem a vir da
> fundamentação, e o JUÁ-Juris usa enunciados como consulta, que tendem a
> espelhar a ementa. As 50 consultas reais de log do JurisTCU não têm poder
> para detectar os efeitos medidos, embora todos apontem na mesma direção.
> O teste do JUÁ-Juris foi estratificado pelos autores segundo a dificuldade
> para o BM25, o que concentra consultas atípicas; por isso reportamos também
> uma amostra natural do seu conjunto de treino. Doze por cento das consultas
> de teste apontam para acórdãos relevantes no JurisTCU; os resultados se
> mantêm sem elas.* **[conferir esta última frase com a coleção independente]**
