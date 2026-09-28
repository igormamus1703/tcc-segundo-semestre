# Status do TCC — reunião de orientação

**28 de setembro de 2026 · Leonardo Marques**

Resumo do projeto e do que avançou nesta semana, escrito para ser lido antes
da reunião. O detalhe técnico, com todos os artefatos que comprovam cada
número, está em
[`docs/docsleo/branches/leo-f6-secoes-e-fusao/`](docs/docsleo/branches/leo-f6-secoes-e-fusao/).

---

## 0. Antes de tudo: o que os números querem dizer

Três coisas aparecem o tempo todo neste documento. Vale fixar o que cada uma
significa, porque é o que vamos ter de explicar na banca.

**nDCG@10** — a nota do buscador, de 0 a 1. Pergunta: *dos 10 primeiros
resultados que o sistema devolveu, quantos eram relevantes e quão no topo eles
ficaram?* Acertar em 1º lugar vale mais que acertar em 9º. Um nDCG@10 de
**0,25** quer dizer, grosseiramente, que o sistema entrega cerca de um quarto
do que um buscador perfeito entregaria naquelas 10 posições. Não é uma nota
baixa por incompetência: buscar em documentos jurídicos longos é difícil, e o
próprio JurisTCU reporta valores nessa faixa.

**Recall@100** — cobertura. *Dos documentos que eram relevantes, quantos
apareceram em algum lugar dos 100 primeiros?* Importa porque um sistema pode
acertar muito no topo e mesmo assim deixar documentos importantes de fora.

**valor-p** — a chance de a diferença observada ser só sorte. `p = 0,001`
significa "há 1 chance em 1.000 de esse ganho ter aparecido por acaso". O
limite convencional é 0,05. Quando digo que algo é **significativo**, é isso:
não é ruído, é efeito.

---

## 1. O projeto, em um parágrafo

Estamos avaliando **como fatiar acórdãos do TCU para busca jurídica**.

O problema concreto: um acórdão do TCU tem **11 mil tokens de mediana** —
umas 25 páginas. Nenhum sistema de busca indexa um documento desse tamanho
inteiro; é preciso cortá-lo em pedaços (*chunks*) e indexar os pedaços. Depois,
quando um pedaço casa com a busca, o sistema devolve o documento inteiro.

**A pergunta do TCC era:** esse corte importa? Cortar respeitando as
**macro-seções do acórdão** (ementa, relatório, fundamentação, dispositivo)
recupera melhor do que cortar em pedaços de tamanho fixo, sem olhar a
estrutura?

Corpus: **12.880 acórdãos** (2003–2023), **150 consultas** e **2.219
julgamentos de relevância** do JurisTCU. Dois buscadores: **BM25** (busca por
palavra-chave, o método clássico) e um **buscador denso** (busca por
significado, com IA — entende que "licitação" e "certame" são parecidos).

---

## 2. Onde estávamos: a hipótese não se confirmou

Rodamos o experimento completo — 5 estratégias de corte × 2 buscadores — e o
resultado foi **nulo**: nenhuma forma de cortar é significativamente melhor
que outra. De 20 comparações, só uma deu p < 0,05, e ela aponta *contra* a
hipótese (o corte fixo ganhou do estrutural).

**Isso não é um fracasso**, e é importante dizer assim na banca: responder
"não faz diferença" com medição cuidadosa é um resultado. O problema é que,
sozinho, ele não dá muito o que discutir.

**Dois achados sólidos vieram junto, e o segundo abriu a porta:**

**a) O BM25 vence o buscador denso** nas cinco estratégias, com p < 0,001. É
contraintuitivo — o denso é a tecnologia "moderna" —, e é o contrário do que o
próprio JurisTCU achou. A explicação provável: em documento longo, o embedding
de um pedaço de 770 tokens "dilui" o termo específico que a pessoa buscou,
enquanto o BM25 casa a palavra exata.

**b) A relevância mora na fundamentação — mas os buscadores procuram no
relatório.** Localizamos, dentro de cada acórdão, os trechos que os avaliadores
do TCU julgaram relevantes:

| Seção do acórdão | % do texto | % da relevância |
|---|---:|---:|
| **fundamentação** (o voto do relator) | 22,8% | **72,0%** |
| relatório (histórico do caso) | 69,9% | 25,7% |
| dispositivo | 6,0% | 1,8% |
| ementa | 1,3% | 0,4% |

Faz todo sentido no gênero: o **relatório** recapitula o que as partes
alegaram e o histórico processual; a **fundamentação** é onde o ministro
raciocina e firma a tese jurídica — que é o que alguém procura ao consultar
jurisprudência.

**Só que**: quando fomos ver de onde vinha o trecho que fazia cada documento
ser recuperado, **65% a 74% das vezes era o relatório**. Ou seja, os dois
buscadores acham o termo **onde há mais texto**, não onde há mais informação.

---

## 3. O que avançou nesta semana

Peguei esse descompasso e testei a intervenção óbvia: **e se simplesmente
tirarmos o relatório do índice?**

Atenção ao que isso significa na prática: o documento continua inteiro para o
usuário. O que muda é que os pedaços vindos do relatório **não entram na
busca** — eles deixam de competir por vaga nos primeiros resultados.

| | nDCG@10 | MRR@10 | MAP@10 | Recall@100 |
|---|---:|---:|---:|---:|
| Onde estávamos (BM25, índice completo) | 0,2486 | 0,5186 | 0,0963 | 0,4709 |
| **Onde estamos** | **0,3215** | **0,6000** | **0,1402** | **0,5479** |
| | **+29,3%** | +15,7% | **+45,6%** | **+16,4%** |

**+29% de nDCG@10, com p < 0,00001. E nenhuma métrica piora** — nem a
cobertura, que é o que normalmente se sacrifica quando se ganha precisão.

Traduzindo o que 0,2486 → 0,3215 quer dizer: em **100 das 150 consultas** o
sistema novo entrega um top-10 melhor que o antigo; em 30 entrega pior; nas
20 restantes empata. Não é uma média puxada por poucos casos extremos.

São **duas** intervenções que se somam, porque atacam coisas diferentes:

1. **Descartar o relatório do índice** (+17%). Muda *o que está no índice*.
   Funciona nas **cinco** estratégias de corte e nos **dois** buscadores, e de
   quebra o índice fica com **um terço do tamanho** — menos disco, busca mais
   rápida.
2. **Combinar os rankings do BM25 e do denso** (+12% em cima disso). Muda
   *como os resultados são ordenados*. O denso não era inútil: ele errava em
   **lugares diferentes** do BM25, então juntar os dois recupera o que cada um
   sozinho perdia.

Um detalhe de que gosto: a melhor configuração **não tem nenhum parâmetro para
ajustar** — ela combina quatro rankings com peso igual. Isso importa porque
elimina a acusação de que ficamos mexendo em botões até o número subir.

---

## 4. Por que podemos confiar nesse número

Essa é a parte que mais quero discutir na reunião. Antes de dar o resultado
por bom, tentei derrubá-lo.

### A pergunta óbvia que a banca vai fazer

> *"Vocês jogaram fora dois terços do índice e melhorou. Não é só porque o
> índice ficou menor e sobrou menos coisa para atrapalhar?"*

É a pergunta certa. Se fosse esse o mecanismo, o TCC não teria contribuição
nenhuma — qualquer um encolhe um índice sorteando pedaços, sem precisar de
segmentador nenhum.

**Então rodei o controle.** Descartei **exatamente o mesmo número de pedaços**
(254.234, o número exato que o corte por seção deixa de fora), mas escolhidos
**ao acaso**:

| Condição | nDCG@10 | |
|---|---:|---|
| índice completo | 0,2486 | referência |
| **−67% sorteados ao acaso** | **0,2260** | **piora 9%** |
| **−67% escolhendo o relatório** | **0,2904** | **melhora 17%** |

**Mesmo tamanho de índice. Efeitos de sinal oposto.** Jogar coisa fora ao acaso
piora, como o bom senso manda. A única razão de jogar fora dois terços e
*melhorar* é que os dois terços descartados eram sistematicamente os menos
úteis. Repeti o sorteio com três sementes diferentes: −7%, −9%, −15%. Sempre
negativo.

### O efeito segue exatamente o mecanismo previsto

Se a explicação está certa, o efeito de cada corte tem de acompanhar **quanta
relevância** aquela seção carrega. Testei dez cortes diferentes:

| O que foi removido do índice | relevância que havia ali | efeito no nDCG@10 |
|---|---|---:|
| a ementa | 0,4% | −0,1% (nada) |
| o dispositivo | 1,8% | +0,2% (nada) |
| **o relatório** | 25,7% | **+16,8%** |
| **a fundamentação** | 72,0% | **−17,5%** |
| | | |
| *indexar só o relatório* (72% do texto!) | 25,7% | **−21,5%** |

Leia essa tabela de baixo para cima, porque é ela que fecha o argumento:

- **Remover seções pequenas e pobres não faz efeito nenhum.** O método não é
  "cortar por cortar" — se fosse, a ementa e o dispositivo também ajudariam.
- **Remover a fundamentação custa −17,5%**, quase o espelho do ganho de
  remover o relatório. O efeito acompanha a relevância, não o tamanho.
- **Indexar só o relatório é 21,5% pior do que indexar o acórdão inteiro.**
  Esse é o achado mais forte: aquele texto — 72% do documento — não é apenas
  inútil, ele **atrapalha ativamente**. Ele gera casamentos de palavra que
  empurram os documentos certos para fora do top-10.

### A crítica mais séria, e como respondi

A decisão de cortar o relatório veio da estatística dos 72%. Mas essa
estatística foi calculada **usando os próprios julgamentos de relevância** que
depois usamos para avaliar. Ou seja: olhamos o gabarito para decidir o que
fazer, e depois nos medimos contra o mesmo gabarito. **Isso é circular**, e um
avaliador atento vai apontar.

Então tratei *"qual seção indexar"* como uma escolha a ser validada, com 10
candidatos, usando **validação cruzada**: divido as 150 consultas em 5 grupos;
escolho a configuração usando 4 grupos; meço no 5º, que **não participou da
escolha**; repito 5 vezes.

```
escolhida em cada uma das 5 rodadas : "sem relatório" — sempre a mesma
ganho medido FORA da escolha        : +16,2%   (p = 0,000275)
ganho medido dentro da amostra      : +16,8%
```

As cinco rodadas escolheram a mesma coisa sozinhas, e a diferença entre
escolher olhando e escolher às cegas é de **0,6 ponto percentual**. A decisão
generaliza — não está viciada nas nossas 150 consultas.

### E os números são mesmo esses?

- Rodar a avaliação de novo dá tabelas **byte a byte idênticas**.
- Reimplementei a métrica **do zero**, sem usar a biblioteca, e deu igual
  (0,2490 contra 0,2486). Não é bug de ferramenta.
- O ganho **não é** "recuperar mais fundo": o controle aleatório recupera
  *mais* documentos por consulta e é o pior de todos.

---

## 5. A limitação que precisa estar no artigo

O JurisTCU julga relevância sobre **excertos de jurisprudência** — trechos que
a própria equipe do TCU seleciona para representar teses jurídicas. E tese
jurídica sai do voto, por construção do gênero.

Então o benchmark já define relevância de um jeito que favorece a
fundamentação. **Isso não invalida nenhum número**, mas **limita o alcance da
conclusão**: ela vale para a tarefa *"achar o acórdão que firma determinada
tese"* — que é a tarefa real de quem consulta jurisprudência, e é para isso
que o TCU mantém a base.

O que **não** podemos afirmar: que o relatório seja inútil em qualquer busca.
Quem procura um **fato do caso concreto** — o nome de uma empresa, um valor,
uma data, um órgão — provavelmente vai encontrá-lo justamente no relatório, e
para esse tipo de consulta o corte poderia até piorar.

**Prefiro dizer isso antes que perguntem.** É uma limitação de escopo, não um
defeito de método.

---

## 6. E a pergunta original do TCC?

**Continua com a mesma resposta — e agora com mais segurança.**

Refiz a comparação entre as cinco estratégias de corte **dentro da nova
condição**, 16% acima em desempenho. Resultado: nenhuma diferença
significativa (menor p = 0,056), e todos os efeitos abaixo do mínimo que 150
consultas conseguem detectar.

Um empate que se repete em **dois pontos de operação diferentes** é evidência
bem mais forte do que um empate medido uma vez só. **O resultado nulo não foi
derrubado pela nova frente — foi reforçado por ela.**

Vale registrar outro resultado prático: cortar usando a estrutura **oficial**
do TCU (as colunas do CSV) e cortar usando o **nosso segmentador automático**
(92,2% de acurácia) dão resultados equivalentes — p = 0,99, com 75 empates em
150 consultas. **É isso que torna o método aplicável a qualquer acervo
jurídico**, e não só ao TCU, que publica os acórdãos já separados em colunas.

---

## 7. O que proponho para o artigo

O trabalho passa a ter **duas perguntas encadeadas**, e as duas com resposta:

1. *Como cortar o documento?* → **Tanto faz.** Resultado nulo, bem medido, e
   confirmado em dois pontos de operação.
2. *Qual parte do documento indexar?* → **A fundamentação.** Ganho de 17% a
   29%, significativo, com controle e validação cruzada.

E a ligação entre elas é o que dá unidade ao texto: **a segunda pergunta só
existe porque a primeira foi respondida com cuidado.** Foi investigando *por
que* o chunking não importava que descobrimos o que importa. Não é "deu errado
e a gente achou outra coisa".

Três configurações recomendadas, em pontos diferentes da curva custo ×
qualidade — e acho que o artigo deve apresentar as três, porque a escolha
depende de quanto o leitor pode gastar:

| Se quiser... | Configuração | nDCG@10 | Custo |
|---|---|---:|---|
| melhor custo-benefício | BM25 sem o relatório | 0,2904 (+17%) | **um** índice, com **1/3** do tamanho |
| melhor com índice enxuto | recorte + fusão | 0,3160 (+27%) | dois índices de 1/3, duas buscas |
| melhor resultado | fusão de 4 rankings | **0,3215 (+29%)** | dois índices completos + dois recortados |

---

## 8. O que preciso decidir com a equipe e com o senhor

1. 🔴 **O corpus.** O artigo e o pôster dizem **113.827 documentos**; o código
   produz **12.880**. É uma mudança de escopo de agosto que nunca foi
   propagada para o texto. Está aberto desde 05/09 e ficou mais urgente:
   agora há um resultado forte para publicar, e ele está medido sobre 12.880.
   **Minha recomendação é ficar com 12.880 e corrigir o texto** (são 11
   números) — subir para 113.827 mudaria duas variáveis ao mesmo tempo e
   custaria ~9 dias de GPU.
2. 🟠 **A nova estrutura do artigo**, conforme o §7.
3. 🟡 **O que atacar nas ~5 semanas que restam.** Minha ordem:
   - corrigir os números e reescrever Introdução, Resultados e Conclusão;
   - testar se o ganho é sobre *o relatório* ou sobre *texto de baixa
     densidade informativa* em geral — se for o segundo, vira uma conclusão
     que serve para qualquer tipo de documento, não só acórdão. É a
     contribuição mais ambiciosa possível com o tempo que temos;
   - reranking com modelo de reordenação, se sobrar tempo.

---

## Estado técnico

| | |
|---|---|
| Fases | F0–F6 concluídas e integradas |
| Testes automatizados | **191** passando (eram 115 há três semanas) |
| Rodadas versionadas | 20+, cada uma com manifesto (commit, hardware, versões), log e figuras |
| Reprodutibilidade | Reexecutar a avaliação dá tabelas byte-idênticas |
| Um comando | `.\scripts\rodada_completa.ps1` roda tudo, do BM25 à tabela final |

Três bugs silenciosos foram encontrados e corrigidos no caminho. Nenhum
levantava erro: os três davam um resultado plausível e **errado**. O mais
sério: empates de pontuação na fronteira do top-10 faziam o mesmo arquivo de
resultados dar dois números diferentes conforme a ordem em que as contas eram
feitas. Todos estão documentados e travados por teste, para não voltarem.

Menciono isso porque é o tipo de coisa que, se aparecesse na defesa em vez de
aqui, custaria caro.
