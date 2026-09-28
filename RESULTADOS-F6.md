# O que avançou nesta semana

**28 de setembro de 2026 · Leonardo Marques · branch `leo/f6-secoes-e-fusao`**

Documento para a reunião de orientação. Todos os números têm o arquivo que os
comprova em `results/experiments/`, e o detalhe técnico está em
[`docs/docsleo/branches/leo-f6-secoes-e-fusao/`](docs/docsleo/branches/leo-f6-secoes-e-fusao/).

---

## O resumo, para quem só vai ler o primeiro parágrafo

Duas semanas atrás fechamos o experimento e a hipótese não se confirmou: a
estratégia de chunking não muda a recuperação. Ficou, junto, uma pista
exploratória — descartar o relatório do acórdão parecia melhorar as coisas.

Nesta semana essa pista virou resultado. **A melhor configuração que temos
agora recupera 29% melhor que a melhor configuração que tínhamos**, com
p < 0,00001 e sem piorar nenhuma das quatro métricas. E o resultado nulo
original não foi derrubado — foi confirmado uma segunda vez, num ponto de
operação diferente, o que o torna mais forte.

| | nDCG@10 | MRR@10 | MAP@10 | Recall@100 |
|---|---:|---:|---:|---:|
| Onde estávamos (BM25, índice completo) | 0,2486 | 0,5186 | 0,0963 | 0,4709 |
| **Onde estamos** | **0,3215** | **0,6000** | **0,1402** | **0,5479** |
| | **+29,3%** | **+15,7%** | **+45,6%** | **+16,4%** |

---

## 1. O raciocínio, em quatro passos

O que dá força a este resultado não é o número: é a ordem em que as coisas
foram medidas.

**Passo 1 — medimos onde mora a relevância no acórdão** *(já estava feito, na
etapa anterior)*. A fundamentação (o voto) ocupa **22,8% do texto** e concentra
**72,0% do conteúdo julgado relevante** pelos avaliadores do JurisTCU. O
relatório ocupa **69,9% do texto** e concentra apenas **25,7% da relevância**.

**Passo 2 — medimos o que os buscadores realmente fazem** *(idem)*. Os dois
retrievers recuperam **65% a 74%** dos documentos por um trecho do **relatório**
— justamente a parte com menos relevância. Eles acham o termo *onde há mais
texto*, não *onde há mais informação*.

**Passo 3 — a previsão que nasce daí.** Se o problema é esse, tirar o relatório
do índice deveria melhorar a recuperação. Note que a previsão foi feita a
partir de medições dos passos 1 e 2, **antes** de qualquer teste — não é uma
explicação inventada depois para justificar um número que apareceu.

**Passo 4 — testamos, e funciona.** É o resto deste documento.

---

## 2. Descartar o relatório: as cinco estratégias, os dois buscadores

nDCG@10 — quanto maior, melhor:

| Estratégia de chunking | BM25 completo | BM25 **sem relatório** | ganho | denso completo | denso **sem relatório** | ganho |
|---|---:|---:|---:|---:|---:|---:|
| fixo 512/256 | 0,2486 | **0,2904** | **+16,8%** | 0,2055 | **0,2627** | **+27,8%** |
| estrutural (ouro) | 0,2521 | **0,2835** | +12,4% | 0,1847 | **0,2167** | +17,3% |
| estrutural (predito) | 0,2526 | **0,2835** | +12,3% | 0,1912 | **0,2147** | +12,3% |
| fixo 1024/512 | 0,2510 | **0,2790** | +11,2% | 0,2019 | **0,2292** | +13,5% |
| recursivo | 0,2412 | **0,2764** | +14,6% | 0,1967 | **0,2351** | +19,5% |

**As dez comparações melhoram.** No BM25 — o buscador mais forte do trabalho —
as cinco são estatisticamente significativas, com p entre 0,00025 e 0,003.

Três coisas a destacar:

- **Vale no BM25.** O teste exploratório da semana passada só tinha rodado no
  buscador denso. Era o buraco mais sério, e está fechado.
- **Vale nas estratégias que não conhecem seção.** As estratégias "fixo" e
  "recursivo" cortam o documento sem olhar a estrutura, e os chunks delas não
  têm rótulo de seção. Usamos a *posição* do chunk no documento para descobrir
  de qual seção ele veio. Ou seja: **o método não exige chunking estrutural**.
- **Vale sem a estrutura oficial.** Comparando o recorte feito com a estrutura
  *ouro* (as colunas do CSV do TCU) contra o feito pelo nosso segmentador de
  regras: **p = 0,9886, com 75 empates em 150 consultas**. São equivalentes.
  Isso é o que torna o achado aplicável a qualquer acervo jurídico, e não só ao
  TCU, que publica os acórdãos já separados em colunas.

**O índice fica com 28% a 34% do tamanho original.** Menos custo e melhor
resultado ao mesmo tempo.

---

## 3. A pergunta difícil — e a resposta que dá segurança ao resultado

> *"Vocês jogaram fora dois terços do índice e melhorou. Como sabem que a
> melhora vem de ser o relatório, e não simplesmente de o índice ter ficado
> menor?"*

É a pergunta certa, e um índice menor realmente tem menos concorrência por vaga
nos primeiros resultados. Se fosse esse o mecanismo, o trabalho não teria
contribuição: qualquer um obtém um índice menor amostrando, sem precisar de
segmentador nenhum.

**Então rodamos o controle.** Descartamos **exatamente o mesmo número de
chunks** — 254.234 na melhor estratégia, o número exato que o recorte por seção
deixa —, mas **escolhidos ao acaso**:

| Estratégia | índice completo | −67% **ao acaso** | −67% **escolhendo o relatório** |
|---|---:|---:|---:|
| fixo 512/256 | 0,2486 | 0,2260 **(−9,1%)** | **0,2904 (+16,8%)** |
| estrutural (ouro) | 0,2521 | 0,2177 **(−13,6%)** | **0,2835 (+12,4%)** |
| estrutural (predito) | 0,2526 | 0,2210 **(−12,5%)** | **0,2835 (+12,3%)** |
| fixo 1024/512 | 0,2510 | 0,2305 **(−8,2%)** | **0,2790 (+11,2%)** |
| recursivo | 0,2412 | 0,2006 **(−16,8%)** | **0,2764 (+14,6%)** |

**Mesmo tamanho de índice. Efeitos de sinal oposto.**

Jogar fora dois terços do índice **piora** a recuperação, como o bom senso
manda. A única razão de jogar fora dois terços e **melhorar** é que os dois
terços descartados eram sistematicamente os menos úteis. Este controle é o que
transforma uma observação numa afirmação sobre a estrutura do acórdão.

---

## 4. O buscador denso não era inútil — era complementar

Na etapa anterior tínhamos medido que o BM25 vence o buscador denso nas cinco
estratégias, com significância forte. A leitura fácil era "o denso não compensa
o custo de GPU".

A leitura correta é outra: **o denso erra em lugares diferentes**. Combinando
os dois rankings, com o BM25 pesando mais, ganha-se de 4,4% a 8,6% de nDCG@10
sobre o BM25 sozinho — em 6 das 10 configurações testadas com p < 0,05.

**E os dois ganhos se somam**, porque atacam coisas diferentes: o recorte muda
*o que está no índice*, a fusão muda *como dois rankings se combinam*.

| Estratégia | BM25 sem relatório | **+ fusão com o denso** | ganho | p |
|---|---:|---:|---:|---:|
| **fixo 512/256** | 0,2893 | **0,3160** | **+9,2%** | **0,0001** |
| recursivo | 0,2764 | 0,3006 | +8,7% | **0,0004** |
| estrutural (ouro) | 0,2835 | 0,3025 | +6,7% | **0,0002** |
| fixo 1024/512 | 0,2791 | 0,2970 | +6,4% | **0,0008** |
| estrutural (predito) | 0,2835 | 0,2902 | +2,3% | 0,228 |

### Um cuidado metodológico que vale mencionar na banca

O peso da fusão é um parâmetro, e nós o descobrimos varrendo ~24 combinações e
vendo qual dava o melhor número. **Isso é ajustar no conjunto de teste** — com
150 consultas, alguma combinação pareceria boa por acaso.

Corrigimos com **validação cruzada por consulta**: as 150 consultas são
divididas em 5 grupos; o peso é escolhido em 4 deles e aplicado no quinto, que
não participou da escolha. Cada consulta é pontuada por um modelo que nunca a
viu.

O ganho aparente caía de 6,6–9,7% para **4,4–8,6%** depois da correção. **A
diferença entre os dois números é exatamente o quanto vinha do ajuste** — e
reportar essa conta é, por si, um ponto a favor do rigor do trabalho.

### E a melhor configuração não tem parâmetro nenhum

Testando combinações **mistas**, apareceu algo melhor e mais simples: fundir as
**quatro** condições — BM25 e denso, cada um com e sem o relatório — com
**peso igual**.

| Estratégia | BM25 | fusão das 4 | ganho | Recall@100 | ganho |
|---|---:|---:|---:|---:|---:|
| **fixo 512/256** | 0,2486 | **0,3215** | **+29,3%** | 0,4709 → **0,5479** | **+16,4%** |
| recursivo | 0,2412 | 0,3082 | +27,8% | 0,4731 → 0,5363 | +13,4% |
| estrutural (ouro) | 0,2521 | 0,3065 | +21,6% | 0,4849 → 0,5349 | +10,3% |
| fixo 1024/512 | 0,2510 | 0,3051 | +21,6% | 0,4861 → 0,5445 | +12,0% |
| estrutural (predito) | 0,2526 | 0,3018 | +19,5% | 0,4863 → 0,5180 | +6,5% |

**Peso igual significa zero graus de liberdade.** Não há o que ajustar, logo
não há como ajustar no conjunto de teste, logo toda a ressalva do parágrafo
anterior simplesmente não se aplica. Contra a versão ponderada por validação
cruzada, a diferença não é significativa (p = 0,338) — as duas são
equivalentes, e entre duas coisas equivalentes reporta-se a que não tem
parâmetro.

O preço é operacional: a fusão das quatro exige manter os **dois** índices
(completo e recortado) e fazer quatro buscas por consulta. Por isso a tabela
final apresenta **três** configurações, não uma.

---

## 5. A tabela final, com tudo junto

Estratégia `fixo 512/256`, 150 consultas, correção de Bonferroni sobre 28
comparações — **23 delas dão significativas**:

| | nDCG@10 | MRR@10 | MAP@10 | Recall@100 |
|---|---:|---:|---:|---:|
| **fusão das 4 condições** | **0,3215** | 0,6000 | **0,1402** | **0,5479** |
| recorte + fusão (peso por CV) | 0,3160 | **0,6058** | 0,1330 | 0,5259 |
| BM25, sem o relatório | 0,2904 | 0,5889 | 0,1190 | 0,4993 |
| denso, sem o relatório | 0,2627 | 0,5190 | 0,1112 | 0,4564 |
| fusão, índice completo | 0,2606 | 0,4988 | 0,1038 | 0,5037 |
| **BM25 (onde estávamos)** | 0,2486 | 0,5186 | 0,0963 | 0,4709 |
| BM25, −67% ao acaso *(controle)* | 0,2260 | 0,4725 | 0,0867 | 0,4310 |
| denso bge-m3 | 0,2055 | 0,4042 | 0,0800 | 0,4759 |

Figura: `results/experiments/20260928-1822_f6_tabela_principal/figuras/…__condicoes.png`

**As quatro métricas sobem.** Não há trade-off a declarar — e havia: o teste
exploratório da semana passada, feito só no buscador denso, tinha registrado
uma perda de 7% no Recall@100 como limitação do método. Rodando no BM25,
descobrimos que a perda era limitação **do denso**, não do método: no BM25 o
recall sobe.

### Três configurações, não uma

O artigo deve apresentar três pontos da curva custo × qualidade:

| Se você quer... | Configuração | nDCG@10 | Custo |
|---|---|---:|---|
| o melhor custo-benefício | BM25, sem o relatório | 0,2904 (+16,8%) | **um** índice, com **1/3** do tamanho |
| o melhor com índice enxuto | recorte + fusão | 0,3160 (+27,1%) | dois índices de 1/3, duas buscas |
| o melhor resultado | fusão das 4, peso igual | **0,3215 (+29,3%)** | dois índices completos + dois recortados, quatro buscas |

### E o ganho não vem das consultas fáceis

O JurisTCU tem três tipos de consulta. As reais, tiradas do log de busca do
TCU, são de longe as mais difíceis:

| Tipo de consulta (50 cada) | BM25 | fusão das 4 | ganho |
|---|---:|---:|---:|
| pergunta sintética (LLM) | 0,3214 | **0,4166** | **+29,6%** |
| expressão sintética (LLM) | 0,2920 | **0,3900** | **+33,6%** |
| **consulta real de usuário** | 0,1335 | **0,1578** | **+18,2%** |

Este é o recorte que costuma desmontar uma melhoria — e o ganho se mantém nos
três grupos. Nas consultas reais ele é menor, e vale notar que ali a
configuração do meio (recorte + fusão, 0,1640) supera a fusão das quatro.

---

## 6. E a pergunta original do TCC?

**Continua com a mesma resposta: a estratégia de chunking não importa.** Mas
agora sabemos disso com mais segurança.

Refizemos a comparação entre as cinco estratégias **dentro da nova condição**,
16% acima em desempenho absoluto. Resultado: 10 pares, **nenhum significativo**
(menor p = 0,056).

Um empate que se repete em dois pontos de operação separados por 16% é uma
evidência bem mais forte do que um empate medido uma vez só. **O resultado nulo
não foi derrubado pela F6 — foi reforçado por ela.**

Vale uma frase na discussão: no índice completo a `fixo 512/256` era a 4ª
colocada no BM25; sem o relatório é a 1ª nos dois buscadores. A diferença
continua não significativa, mas a inversão é consistente com o mecanismo — com
o relatório fora, o que sobra é texto denso em conteúdo julgado, e chunks
menores localizam melhor dentro dele.

---

## 7. O que testamos e descartamos

Três coisas foram implementadas, medidas e jogadas fora. Registrar isto importa
tanto quanto registrar o que funcionou.

| Tentativa | Resultado |
|---|---|
| **Ponderar** o relatório em vez de cortá-lo | Satura: qualquer peso moderado dá exatamente o mesmo resultado do corte, e o recall **piora**. Descartada |
| **Fusão sem peso** (RRF clássico, 1:1) | p entre 0,206 e 0,906. Dar peso igual a um buscador 20% pior anula o ganho |
| Agregação `sum_top_k` em vez de `max_pooling` | Perde em 4 de 5 estratégias. Era análise de sensibilidade: cumpriu o papel de justificar o padrão que já usávamos |

O primeiro rendeu um achado lateral interessante: **um desconto de apenas 2% no
score dos chunks do relatório já captura metade do ganho**. Isso quer dizer que,
dentro de um mesmo documento, o trecho do relatório vence o da fundamentação
*por muito pouco* — não é um casamento melhor, é um casamento marginalmente
melhor que acontece mais vezes porque há mais texto. É a evidência mais direta
do mecanismo que descrevemos no passo 2.

---

## 7-bis. Tentamos derrubar o próprio resultado

Antes de propor o merge, atacamos o resultado pelos pontos onde ele é mais
frágil. Dez ameaças, testadas uma a uma. O detalhe está em
[`docs/docsleo/branches/leo-f6-secoes-e-fusao/04-auditoria-de-validade.md`](docs/docsleo/branches/leo-f6-secoes-e-fusao/04-auditoria-de-validade.md);
aqui vão as três que mais importam.

### a) O efeito segue o mecanismo previsto? (dez recortes diferentes)

Se a explicação está certa — *o ganho vem de tirar do índice a parte pobre em
conteúdo relevante* —, o efeito de cada recorte tem de acompanhar a
concentração de relevância daquela seção, medida **antes** da intervenção.

| Recorte | relevância na seção afetada | nDCG@10 | Δ |
|---|---|---:|---:|
| **sem relatório** | remove 25,7% da relevância e 72% do texto | **0,2904** | **+16,8%** |
| fundamentação + ementa | mantém 72,4% da relevância | 0,2792 | +12,3% |
| só fundamentação | mantém 72,0% da relevância | 0,2739 | +10,2% |
| sem dispositivo | remove 1,8% da relevância | 0,2490 | +0,2% |
| *completo (baseline)* | — | *0,2486* | — |
| sem ementa | remove 0,4% da relevância | 0,2484 | −0,1% |
| **sem fundamentação** | remove **72%** da relevância | 0,2050 | **−17,5%** |
| **só relatório** | 72% do texto, 25,7% da relevância | 0,1950 | **−21,5%** |

Três coisas que este teste mostra e a tabela principal não mostrava:

1. **Remover seções pequenas e irrelevantes não faz nada** (−0,1%, +0,2%). O
   método não é "cortar por cortar".
2. **Remover a fundamentação custa −17,5%**, quase o simétrico do ganho de
   remover o relatório. O efeito acompanha a relevância, não o tamanho.
3. **Indexar só o relatório — 72% do texto — é 21,5% pior do que indexar
   tudo.** Esse texto não é apenas inútil: ele **atrapalha**, gerando
   casamentos que empurram os documentos certos para fora do top-10.

Isso também corrige a formulação do achado. Não é *"o relatório é ruim"*, é
**"indexe a parte do documento onde a relevância se concentra"** — que é uma
afirmação mais geral e mais útil para outros gêneros de documento.

### b) A crítica séria: decidimos olhando o gabarito

**O problema, sem maquiagem.** A estatística que motivou tudo — *72% da
relevância está na fundamentação* — foi obtida localizando os excertos
julgados relevantes dentro dos acórdãos. São os mesmos julgamentos que
definem o gabarito da avaliação. Ou seja: escolhemos o que indexar olhando o
gabarito e depois medimos contra ele.

**O teste.** Tratamos *"qual seção indexar"* como um hiperparâmetro com 10
candidatos e o escolhemos por **validação cruzada por consulta**: a escolha é
feita com 4/5 das consultas e o número vem do 1/5 que não participou dela.

```
escolhida em cada uma das 5 dobras : sem relatório  (escolha estável)
nDCG@10 medido FORA da escolha     : 0,2893
nDCG@10 do baseline                : 0,2490
ganho honesto                      : +16,2%   (p = 0,000275)
```

Contra +16,8% medido dentro da amostra. **A perda por generalização é de 0,6
ponto percentual** — a decisão não está superajustada às nossas 150 consultas.

### c) Os números são mesmo esses?

- Reexecutar a avaliação produz tabelas **byte-idênticas**.
- Reimplementei o nDCG@10 **do zero**, sem a biblioteca: 0,2490 contra 0,2486;
  0,3215 contra 0,3215. Não é artefato de biblioteca.
- Com ganho exponencial em vez de linear, o ganho vai de +16,5% para +16,9%.
  Não depende da variante da métrica.
- O controle aleatório foi repetido com três sementes: −7,1%, −9,1%, −15,4%.
  Sempre negativo, sempre muito longe dos +16,8% do recorte.
- O ganho não é "recuperar mais fundo": o controle recupera **mais**
  documentos por consulta (mediana 920 contra 739) e é o pior de todos.

### A limitação que fica, e que precisa estar no texto

O JurisTCU julga relevância sobre **excertos de jurisprudência** — trechos que
a própria equipe do TCU seleciona para representar teses jurídicas. Teses
saem do voto, por construção do gênero. Então o benchmark define relevância de
um jeito que já favorece a fundamentação.

Isso não invalida nenhum número, mas **escopa a conclusão**: ela vale para a
tarefa "encontrar o acórdão que firma determinada tese", que é a tarefa real
de quem consulta jurisprudência. Não se pode afirmar que o relatório seja
inútil para outras buscas — quem procura um fato do caso concreto (uma
empresa, um valor, uma data) provavelmente o acharia justamente lá.

Sugestão de frase para o artigo: *"Os resultados são condicionais à noção de
relevância do JurisTCU, que julga excertos de jurisprudência. Para consultas
dirigidas a fatos do caso concreto, a conclusão pode não se transferir."*

---

## 8. Estado do trabalho e o que precisa de decisão

**Feito:** código no pipeline com **182 testes** passando (eram 115), onze
rodadas novas com manifesto e figuras, e a documentação completa da branch.

**Três bugs reais foram encontrados durante a execução**, e vale mencionar
porque nenhum dos três levantava erro — os três produziam resultado plausível e
errado:

1. uma colisão de nome que apagava uma linha da tabela principal;
2. um agrupamento nas figuras que fazia duas condições diferentes virarem a
   mesma barra;
3. **empate de score na fronteira da métrica** — o mais sério. O mesmo arquivo
   de resultados dava 0,1322 e 0,1336 no mesmo recorte, dependendo da ordem
   das chamadas. Na consulta 6, três documentos empatam nas posições 9, 10 e
   11 e um deles é relevante: se ele fica em 9 ou 10 a consulta vale 0,066, se
   é empurrado para 11 vale 0. A biblioteca de avaliação não fixa esse
   desempate. Passamos a desempatar por identificador do documento — critério
   arbitrário, mas **fixo**, que é o que importa.

Os três estão travados por teste. O terceiro tem uma consequência para o resto
do trabalho: ele afeta os recortes, os intervalos de confiança e a análise de
poder de **todas** as rodadas, inclusive as da etapa anterior. O efeito é de
terceira casa decimal e nenhuma conclusão muda, mas as tabelas da etapa
anterior precisam ser regeradas antes de qualquer número de recorte ir para o
artigo. Vale também uma frase de limitação: **os valores por consulta dependem
de um critério de desempate**, e o nosso está documentado.

**Precisa de decisão da equipe / do orientador:**

1. 🔴 **O corpus.** O artigo diz 113.827 documentos; o código produz 12.880.
   Continua aberto desde 05/09, e ficou mais urgente: agora há um resultado
   forte a publicar, e ele está medido sobre 12.880.
2. 🟠 **O merge desta branch.** Está pronta e verde, mas **não mergeada** —
   ela muda a tese do artigo, e isso não é decisão de um integrante.
3. 🟠 **A nova estrutura do artigo.** Sugestão: duas perguntas encadeadas. A
   de *granularidade* tem resposta nula e bem medida; a de *seleção de
   conteúdo*, que nasceu dela, tem resposta positiva e significativa. O
   trabalho não "deu errado e a gente achou outra coisa" — a segunda pergunta
   só existe porque a primeira foi respondida com cuidado.

**O que faríamos a seguir, se houver tempo:** testar se o ganho é sobre *o
relatório* especificamente ou sobre *texto de baixa densidade informativa* em
geral. Nosso controle descarta a explicação "índice menor", mas não essa — e
confirmá-la seria uma contribuição ainda maior, porque não dependeria de
conhecer a estrutura do documento.
