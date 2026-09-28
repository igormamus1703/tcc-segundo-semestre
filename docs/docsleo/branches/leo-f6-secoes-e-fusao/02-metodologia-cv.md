# Validação cruzada: por que o peso da fusão não podia ser escolhido olhando o resultado

**Data:** 28/09/2026 · **Autor:** Leonardo Marques

---

## O problema

A fusão ponderada de BM25 com o denso melhora o nDCG@10. Descobri isso
varrendo ~24 configurações (dois métodos × cinco pesos × quatro valores de `k`)
e olhando qual dava o maior número **no conjunto de avaliação**.

Com 150 consultas e 24 configurações, alguma delas ia parecer boa por acaso. É
o erro clássico de ajustar no conjunto de teste. Reportar o melhor da varredura
como se fosse um achado é o tipo de coisa que a banca procura numa tabela em
que um método novo ganha do baseline por poucos pontos percentuais — e ela
estaria certa em procurar.

Não é um detalhe: entre o ganho da varredura (6,6–9,7%) e o ganho após
correção (4,4–8,7%) há uma diferença que **era ajuste**.

## A alternativa que eu descartei

O JurisTCU tem três fontes de consulta (log real, pergunta sintética, expressão
sintética), 50 cada. Dava para escolher o peso num grupo e reportar noutro.

Descartei porque os três grupos têm dificuldades muito diferentes — nDCG@10 de
0,13 nas reais contra 0,32 nas sintéticas. Um peso ajustado nas sintéticas não
é necessariamente o certo para as reais, e o resultado misturaria "o peso não
generaliza" com "os grupos são diferentes". Ficaria impossível saber qual dos
dois o número está medindo.

## O que foi feito

**Validação cruzada por consulta, 5 dobras, semente fixa em 42.** Em cada
dobra, o peso é escolhido pelo melhor nDCG@10 nas outras quatro e aplicado na
dobra que não participou da escolha. O número reportado é a média das 150
consultas, cada uma pontuada por um modelo que nunca a viu.

Implementação em `src/tuning.py`. O que importa no desenho:

- **O baseline é medido nas MESMAS consultas de teste**, uma a uma. Comparar a
  média da CV com a média global do BM25 compararia dois números calculados
  sobre conjuntos diferentes; o pareamento por consulta é o que dá poder ao
  teste.
- **A semente é fixa e explícita.** Sem isso, dois autores rodando o mesmo
  comando publicariam números diferentes e nenhum saberia por quê.
- **A partição não depende da ordem de entrada.** As consultas vêm de um dict;
  se a ordem mudasse a partição, a CV deixaria de ser reprodutível entre
  execuções. As consultas são ordenadas antes de embaralhar.
- **Os pesos escolhidos em cada dobra vão para a tabela.** Se as cinco dobras
  escolherem pesos muito diferentes, o "melhor peso" é ruído, e o que se pode
  afirmar é que *alguma* fusão ponderada ajuda — não que 0,7 seja o número
  certo. (Foi mais ou menos o que aconteceu: os pesos ficam entre 0,6 e 0,8.)
- **Um run TREC cruzado é gravado**: para cada consulta, o ranking do peso
  escolhido sem ela. É o artefato que comprova o número, avaliável pelo
  `src.evaluate` como qualquer outro run — a linha da tabela e o arquivo nunca
  podem divergir.

## O teste que protege isso

O bug de vazamento não levanta exceção: ele só infla o número. O teste em
`tests/test_tuning.py::test_consulta_de_teste_nao_participa_da_escolha_do_peso`
substitui a função de pontuação por um espião, registra quais consultas entram
em cada chamada de seleção, e exige que a dobra de teste nunca apareça entre
elas.

É o tipo de teste que o `README.md` da raiz manda priorizar: trava o erro que
passa direto e vai parar no artigo.

## O que isso custou e o que comprou

**Custou:** os ganhos caem de 6,6–9,7% para 4,4–8,7%, e uma das dez
configurações deixa de ser significativa.

**Comprou:** o número é defensável. E a diferença entre os dois —
"ganho aparente" e "ganho após CV" — vira ela própria um resultado a reportar,
porque quantifica quanto da melhoria vinha do ajuste. Poucos trabalhos de TCC
mostram essa conta.

## O que a CV NÃO cobre nesta branch

A decisão de **descartar o relatório** não passou por validação cruzada, e é
honesto dizer por quê:

- ela não veio de uma varredura, veio de uma medição do domínio feita **antes**
  (a concentração de relevância por seção, F5) — é uma hipótese
  pré-registrada, não um resultado pescado;
- mas a escolha de descartar *o relatório* entre as quatro seções foi
  informada pelo teste exploratório de 07/09, sobre o mesmo conjunto de
  avaliação.

O que protege esse resultado não é CV, é o **controle aleatório pareado**
([resultados/02-controle-aleatorio.md](resultados/02-controle-aleatorio.md)):
um índice do mesmo tamanho, sorteado, **piora** o nDCG@10. Nenhuma pescaria de
configuração explicaria dois efeitos de sinal oposto com o mesmo tamanho de
índice.
