# Auditoria de validade: tentando derrubar o próprio resultado

**Data:** 28/09/2026 · **Autor:** Leonardo Marques
**Motivo:** antes de propor o merge, atacar o resultado da F6 pelos pontos
onde ele é mais frágil. O que está aqui são as verificações, **incluindo as
que quase deram errado** e a limitação que não tem como ser resolvida com
este corpus.

---

## Resumo: o que sobreviveu

| # | Ameaça verificada | Veredito |
|---|---|---|
| 1 | O filtro descarta documentos inteiros e "limpa" o índice de não-relevantes | ✅ **Não.** 4 documentos de 12.880 somem, **nenhum relevante** |
| 2 | Os números não são reproduzíveis | ✅ **São.** Reexecutar dá tabelas byte-idênticas |
| 3 | Os números são artefato da biblioteca de avaliação | ✅ **Não.** Reimplementei o nDCG@10 do zero e bate casa a casa |
| 4 | O ganho depende da variante da métrica | ✅ **Não.** +16,5% (ganho linear) × +16,9% (exponencial) |
| 5 | O ganho vem de recuperar mais fundo, não de conteúdo melhor | ✅ **Não.** O controle recupera **mais** documentos e vai **pior** |
| 6 | O efeito é do relatório ou de qualquer corte? | ✅ **É do conteúdo.** Dose-resposta em 10 condições |
| 7 | 🔴 A decisão de cortar o relatório veio dos próprios rótulos de relevância | ⚠️ **Sim, e é real.** Testado por CV: o ganho sobrevive (+16,2%) |
| 8 | O controle aleatório depende da semente sorteada | ✅ **Não.** Três sementes, mesmo sinal |
| 9 | O resultado nulo entre estratégias é falta de poder | ✅ **Declarado.** Todos os efeitos abaixo do MDE |
| 10 | 🟠 A conclusão vale para qualquer busca em acórdãos | ❌ **Não se pode afirmar.** Ver "A limitação que fica" |

---

## 1. O filtro poderia estar "limpando" o índice

A pior hipótese possível: se o recorte descartasse documentos inteiros e esses
documentos fossem justamente os não-relevantes, o ganho seria artefato puro.

```
docs no corpus com gold_spans : 12.880 de 12.880  (100%)
chunks com seção indefinida   : 0
documentos no índice completo : 12.880
documentos no índice recortado: 12.876
documentos que sumiram        : 4  →  relevantes em algum qrel: 0
```

Quatro documentos em 12.880, nenhum deles relevante para nenhuma consulta.
Não há limpeza.

Vale registrar por que isto **poderia** ter dado errado: `sections.filtrar`
descarta chunks cuja seção não é resolvível, e um documento sem spans perderia
todos os seus chunks. Neste corpus todo documento tem spans (o TCU publica em
colunas), então o caso não ocorre — mas num acervo onde o segmentador falhe em
alguns documentos, ele ocorreria. Fica como aviso para quem reaplicar o método.

## 2 e 3. Reprodutibilidade e independência da biblioteca

Reexecutar `src.evaluate` sobre a mesma rodada produz `main_results.csv` e
`slices_query_type.csv` **idênticos byte a byte**.

Mais forte: reimplementei o nDCG@10 do zero — ganho, logaritmo, DCG, IDCG, sem
usar o `ranx` — e comparei:

| condição | minha implementação | `ranx` |
|---|---:|---:|
| BM25 completo | 0,2490 | 0,2486 |
| BM25 sem relatório | 0,2900 | 0,2904 |
| controle aleatório | 0,2260 | 0,2260 |
| fusão das 4 | 0,3215 | 0,3215 |

As diferenças residuais (4ª casa) são o desempate de empates de score, já
documentado em [03-empate-de-score.md](03-empate-de-score.md). **Os números não
são artefato de biblioteca.**

## 4. E se a métrica fosse outra?

O `ranx` usa ganho **linear** no nDCG. Muita implementação usa ganho
**exponencial** (`2^rel − 1`), que dá mais peso aos documentos de relevância 3.
Recalculei tudo nas duas versões:

| comparação | ganho linear | ganho exponencial | `ranx` |
|---|---:|---:|---:|
| sem relatório vs completo | **+16,5%** | **+16,9%** | +16,8% |
| controle aleatório vs completo | −9,2% | −10,3% | −9,1% |
| fusão das 4 vs completo | +29,1% | +28,0% | +29,3% |

A conclusão não depende da escolha da fórmula.

## 5. O ganho poderia ser só profundidade de recuperação

A busca traz os 2.000 melhores **chunks**, que depois viram documentos. Num
índice três vezes menor, esses 2.000 chunks cobrem mais documentos distintos —
então parte do ganho poderia ser "o recorte enxerga mais fundo", e não
"o recorte enxerga melhor".

| condição | documentos recuperados por consulta (mediana) | nDCG@10 |
|---|---:|---:|
| BM25 completo | 551 | 0,2486 |
| BM25 sem relatório | 739 | **0,2904** |
| controle aleatório | **920** | **0,2260** |

**O controle aleatório é o que recupera mais fundo e o que vai pior.** A
profundidade está descartada como explicação.

## 6. O efeito segue o mecanismo previsto? (dose-resposta)

Se a hipótese está certa — *o ganho vem de tirar do índice a parte pobre em
conteúdo relevante* —, o efeito de cada recorte deve acompanhar a concentração
de relevância daquela seção, medida na F5 **antes** de qualquer intervenção.

Dez condições, BM25, `fixed_512_256`:

| Configuração | % da relevância na seção removida/mantida | nDCG@10 | Δ |
|---|---|---:|---:|
| **sem relatório** | remove seção com 25,7% da relevância e 72% do texto | **0,2904** | **+16,8%** |
| fundamentação + ementa | mantém 72,4% da relevância | 0,2792 | +12,3% |
| só fundamentação | mantém 72,0% da relevância | 0,2739 | +10,2% |
| sem dispositivo | remove seção com 1,8% da relevância | 0,2490 | +0,2% |
| *completo (baseline)* | — | *0,2486* | — |
| sem ementa | remove seção com 0,4% da relevância | 0,2484 | −0,1% |
| **sem fundamentação** | remove a seção com **72%** da relevância | 0,2050 | **−17,5%** |
| só dispositivo | mantém 1,8% da relevância | 0,1991 | −19,9% |
| **só relatório** | mantém 25,7% da relevância, **72% do texto** | 0,1950 | **−21,5%** |
| só ementa | mantém 0,4% da relevância | 0,0821 | −67,0% |

Três leituras, e a terceira é a que fecha o argumento:

1. **Remover seções irrelevantes e pequenas não faz nada** (ementa −0,1%,
   dispositivo +0,2%). O método não é "cortar por cortar".
2. **Remover a fundamentação custa −17,5%** — quase o simétrico do ganho de
   remover o relatório. A direção do efeito acompanha a concentração de
   relevância, não o tamanho da seção.
3. **Indexar só o relatório — 72% do texto do acórdão — é 21,5% pior que
   indexar tudo.** Ou seja: aquele texto não é apenas inútil, ele **atrapalha
   ativamente**, gerando casamentos que empurram documentos certos para fora
   do top-10. É o que diferencia "onde a relevância mora" (um fato sobre os
   rótulos) de "o relatório interfere" (um fato sobre a recuperação).

## 7. 🔴 A crítica séria: a decisão veio dos próprios rótulos

**O problema, sem maquiagem.** A estatística que motivou tudo — *a
fundamentação ocupa 22,8% do texto e concentra 72,0% da relevância* — foi
obtida localizando os **excertos julgados relevantes** dentro dos acórdãos.
Esses julgamentos são os mesmos que definem os qrels da avaliação. Decidimos
o que indexar olhando o gabarito, e depois medimos contra o gabarito.

O controle aleatório **não** resolve isso: ele mostra que o ganho não vem do
tamanho do índice, mas não mostra que a decisão generaliza.

**O teste.** Tratar *"qual subconjunto de seções indexar"* como um
hiperparâmetro com 10 candidatos e escolhê-lo por **validação cruzada por
consulta**: o subconjunto é escolhido usando só as consultas de treino, e o
número reportado vem só das consultas de teste, que não participaram da
escolha. Implementado em `tuning.selecao_por_cv`, com testes.

```
10 configurações candidatas · 5 dobras · 150 consultas

escolhida em cada dobra : sem relatório ×5   (escolha estável)
nDCG@10 fora da escolha : 0,2893
nDCG@10 do baseline     : 0,2490
GANHO HONESTO           : +16,2%   (p = 0,000275)
vitórias/empates/derrotas: 84 / 26 / 40
```

**As cinco dobras escolheram a mesma configuração**, e o ganho medido fora da
escolha (+16,2%) é praticamente o mesmo do ganho medido dentro dela (+16,8%).
A perda por generalização é de 0,6 ponto percentual.

Conclusão: **a decisão não está superajustada a estas 150 consultas.** Se
tivéssemos decidido com 120 delas, decidiríamos o mesmo e obteríamos o mesmo
ganho nas 30 restantes.

## 8. O controle dependia de uma semente só?

O controle aleatório usava `seed=42`. Se aquele sorteio tivesse sido
azarado, o contraste estaria inflado. Rodado com mais duas sementes na
`fixed_512_256`:

| Condição | nDCG@10 | vs baseline | Recall@100 |
|---|---:|---:|---:|
| BM25 completo (baseline) | 0,2486 | — | 0,4709 |
| controle, `seed=2026` | 0,2310 | −7,1% | 0,4318 |
| controle, `seed=42` | 0,2260 | −9,1% | 0,4310 |
| controle, `seed=7` | 0,2104 | −15,4% | 0,4289 |
| **recorte sem relatório** | **0,2904** | **+16,8%** | **0,4993** |

As três sementes dão o mesmo sinal, e a pior delas (−15,4%) ainda está a 32
pontos percentuais do recorte. A variação entre sementes (−7% a −15%) mostra
que um sorteio isolado tem ruído — mas nenhum deles chega perto de explicar o
ganho, e o efeito já estava replicado nas **cinco** estratégias, que sorteiam
populações de chunks diferentes.

Rodadas: `20260928-1652_bm25_controle_amostra` (seed 42) e
`aud_controle_seed7` / `aud_controle_seed2026`.

## 9. O resultado nulo é falta de poder?

Não escondido, declarado. Sob o recorte, os 10 pares entre estratégias dão
0 significativos, e a análise de poder mostra que **todos os efeitos
observados estão abaixo do efeito mínimo detectável**:

| par | efeito observado | MDE (poder 80%) |
|---|---:|---:|
| structural_gold × structural_pred | **0,0000** | 0,0132 |
| fixed_1024_512 × recursive_default | 0,0027 | 0,0166 |
| fixed_512_256 × recursive_default | 0,0129 | 0,0192 |
| (os outros sete) | 0,0044 – 0,0102 | 0,0198 – 0,0259 |

A leitura correta é "não temos resolução para diferenças menores que ~0,02",
e não "provamos que são iguais" — com a exceção de `gold × pred`, cujo efeito
é exatamente zero.

## 10. 🟠 A limitação que fica, e que não dá para resolver aqui

O JurisTCU julga relevância sobre **excertos de jurisprudência**, que são
trechos selecionados pela própria equipe do TCU para representar teses
jurídicas. Teses jurídicas são extraídas do **voto**, por construção do
gênero: o relatório recapitula alegações e histórico processual.

Então há um sentido em que o benchmark **define** relevância de um jeito que
favorece a fundamentação. Nossa medição dos 72% é, em parte, uma medição de
como o JurisTCU foi construído.

**O que isso invalida:** nada dos números. **O que isso escopa:** a conclusão
vale para a tarefa *"encontrar o acórdão que firma determinada tese"*, que é a
tarefa real de quem consulta jurisprudência e é a tarefa que o benchmark
representa. **Não** se pode afirmar, a partir daqui, que o relatório seja
inútil para outras buscas — alguém procurando por um fato do caso concreto
(uma empresa, um valor, uma data) provavelmente o encontraria justamente no
relatório, e para essa tarefa o recorte poderia inverter de sinal.

O achado do §6 mitiga parcialmente: `só relatório` ser **pior que o índice
completo** é um fato sobre interferência na recuperação, não sobre onde os
rótulos moram. Mas a magnitude do efeito continua atrelada à noção de
relevância do benchmark.

**Frase para o artigo:** *"Os resultados são condicionais à noção de
relevância do JurisTCU, que julga excertos de jurisprudência. Para consultas
dirigidas a fatos do caso concreto, que se concentram no relatório, a
conclusão pode não se transferir — e testá-la exigiria um conjunto de
consultas com esse perfil, que não existe para este acervo."*

---

## Veredito

Os ganhos são **reais, grandes e bem sustentados**: reproduzíveis,
independentes da biblioteca e da variante da métrica, com dose-resposta
coerente com um mecanismo medido antes da intervenção, com controle pareado
que descarta as explicações triviais, e com a decisão de projeto validada
fora das consultas que a motivaram.

A branch **avança o trabalho de verdade** — de um resultado nulo para um
resultado nulo mais uma intervenção com efeito de 16% a 29%. As duas ressalvas
que sobram (§7, mitigada por CV; §10, não mitigável com este corpus) são
limitações a **declarar no texto**, não motivos para segurar o merge.
