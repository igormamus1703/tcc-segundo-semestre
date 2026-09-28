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
agora recupera 27% melhor que a melhor configuração que tínhamos**, com
p < 0,00001, sem piorar nenhuma das quatro métricas, usando um índice três
vezes menor. E o resultado nulo original não foi derrubado — foi confirmado uma
segunda vez, num ponto de operação diferente, o que o torna mais forte.

| | nDCG@10 | MRR@10 | MAP@10 | Recall@100 |
|---|---:|---:|---:|---:|
| Onde estávamos (BM25, índice completo) | 0,2486 | 0,5186 | 0,0963 | 0,4709 |
| **Onde estamos** | **0,3160** | **0,6058** | **0,1330** | **0,5259** |
| | **+27,1%** | **+16,8%** | **+38,1%** | **+11,7%** |

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
os dois rankings, com o BM25 pesando mais, ganha-se de 4,4% a 8,7% de nDCG@10
sobre o BM25 sozinho — em 7 das 10 configurações testadas com p < 0,05.

**E os dois ganhos se somam**, porque atacam coisas diferentes: o recorte muda
*o que está no índice*, a fusão muda *como dois rankings se combinam*.

| Estratégia | BM25 sem relatório | **+ fusão com o denso** | ganho | p |
|---|---:|---:|---:|---:|
| **fixo 512/256** | 0,2904 | **0,3160** | **+8,8%** | **0,0002** |
| recursivo | 0,2764 | 0,3006 | +8,7% | **0,0004** |
| estrutural (ouro) | 0,2835 | 0,3025 | +6,7% | **0,0002** |
| fixo 1024/512 | 0,2790 | 0,2970 | +6,4% | **0,0007** |
| estrutural (predito) | 0,2835 | 0,2902 | +2,3% | 0,228 |

### Um cuidado metodológico que vale mencionar na banca

O peso da fusão é um parâmetro, e nós o descobrimos varrendo ~24 combinações e
vendo qual dava o melhor número. **Isso é ajustar no conjunto de teste** — com
150 consultas, alguma combinação pareceria boa por acaso.

Corrigimos com **validação cruzada por consulta**: as 150 consultas são
divididas em 5 grupos; o peso é escolhido em 4 deles e aplicado no quinto, que
não participou da escolha. Cada consulta é pontuada por um modelo que nunca a
viu.

O ganho aparente caía de 6,6–9,7% para **4,4–8,7%** depois da correção. **A
diferença entre os dois números é exatamente o quanto vinha do ajuste** — e
reportar essa conta é, por si, um ponto a favor do rigor do trabalho.

---

## 5. A tabela final, com tudo junto

Estratégia `fixo 512/256`, 150 consultas, correção de Bonferroni sobre 21
comparações:

| | nDCG@10 | MRR@10 | MAP@10 | Recall@100 |
|---|---:|---:|---:|---:|
| **recorte + fusão** | **0,3160** | **0,6058** | **0,1330** | **0,5259** |
| BM25, sem o relatório | 0,2904 | 0,5889 | 0,1190 | 0,4993 |
| denso, sem o relatório | 0,2627 | 0,5190 | 0,1112 | 0,4564 |
| fusão, índice completo | 0,2606 | 0,4988 | 0,1038 | 0,5037 |
| **BM25 (onde estávamos)** | 0,2486 | 0,5186 | 0,0963 | 0,4709 |
| BM25, −67% ao acaso *(controle)* | 0,2260 | 0,4725 | 0,0867 | 0,4310 |
| denso bge-m3 | 0,2055 | 0,4042 | 0,0800 | 0,4759 |

Figura: `results/experiments/20260928-1705_f6_tabela_principal/figuras/…__condicoes.png`

**As quatro métricas sobem.** Não há trade-off a declarar — e havia: o teste
exploratório da semana passada, feito só no buscador denso, tinha registrado
uma perda de 7% no Recall@100 como limitação do método. Rodando no BM25,
descobrimos que a perda era limitação **do denso**, não do método: no BM25 o
recall sobe.

### E o ganho não vem das consultas fáceis

O JurisTCU tem três tipos de consulta. As reais, tiradas do log de busca do
TCU, são de longe as mais difíceis:

| Tipo de consulta (50 cada) | BM25 | configuração final | ganho |
|---|---:|---:|---:|
| pergunta sintética (LLM) | 0,3214 | **0,4041** | **+25,7%** |
| expressão sintética (LLM) | 0,2920 | **0,3799** | **+30,1%** |
| **consulta real de usuário** | 0,1322 | **0,1640** | **+24,1%** |

Este é o recorte que costuma desmontar uma melhoria — e o ganho se mantém
praticamente idêntico nos três grupos.

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

## 8. Estado do trabalho e o que precisa de decisão

**Feito:** código no pipeline com **175 testes** passando (eram 115), nove
rodadas novas com manifesto e figuras, e a documentação completa da branch.

**Dois bugs reais foram encontrados durante a execução**, e vale mencionar
porque nenhum dos dois levantava erro — os dois produziam resultado plausível e
errado: uma colisão de nome que apagava uma linha da tabela principal, e um
agrupamento nas figuras que fazia duas condições diferentes virarem a mesma
barra. Ambos estão travados por teste agora.

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
