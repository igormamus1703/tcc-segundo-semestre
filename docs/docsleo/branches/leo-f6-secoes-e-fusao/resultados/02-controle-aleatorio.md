# O controle: é a estrutura, ou é só um índice menor?

**Data:** 28/09/2026 · **Autor:** Leonardo Marques
**Status:** ✅ controle pareado, rodado nas cinco estratégias

---

## A pergunta que a banca faria

Descartar o relatório melhora o nDCG@10 em até 16,8% **e** encolhe o índice
para um terço. São duas coisas ao mesmo tempo, e só uma delas é a contribuição
do trabalho.

Um índice menor tem menos concorrência por vaga no top-k. Se um recorte
**aleatório** do mesmo tamanho melhorasse tanto quanto o recorte por seção, o
achado não seria sobre a estrutura do acórdão — seria sobre o tamanho do
índice, que qualquer um obtém amostrando, sem precisar de segmentador nenhum.
A contribuição do TCC desapareceria.

Sem este controle, o resultado é uma correlação com duas explicações.

## Como o controle foi construído

Não é "descartar 30% dos chunks". É **casar o número exato de chunks** que o
recorte por seção deixa, **em cada estratégia** — a fração equivalente varia de
28,0% (`fixed_512_256`) a 33,7% (`structural_pred`), e um número único na linha
de comando daria um controle desalinhado justamente onde a comparação precisa
ser exata.

```bash
python -m src.run_experiments --strategy all --retriever bm25 \
    --amostra-igual-a sem:relatorio --label bm25_controle_amostra
```

O pipeline calcula quantos chunks o recorte deixaria e sorteia esse mesmo
número, com semente fixa (42). A amostra é uniforme sobre os chunks, não sobre
os documentos: assim as duas condições têm o mesmo tamanho de índice e, nas
duas, todo documento continua alcançável por alguma fração dos seus chunks.

| Estratégia | chunks no completo | no recorte = no controle | fração |
|---|---:|---:|---:|
| structural_gold | 286.689 | 95.300 | 33,2% |
| structural_pred | 285.308 | 96.219 | 33,7% |
| recursive_default | 270.070 | 78.548 | 29,1% |
| fixed_1024_512 | 450.786 | 126.392 | 28,0% |
| fixed_512_256 | 907.914 | 254.234 | 28,0% |

## O resultado

**As duas condições têm exatamente o mesmo tamanho de índice. Os efeitos vão em
direções opostas.**

| Estratégia (BM25) | completo | −67% **aleatório** | −67% **relatório** |
|---|---:|---:|---:|
| structural_gold | 0,2521 | 0,2177 (−13,6%) | **0,2835 (+12,4%)** |
| structural_pred | 0,2526 | 0,2210 (−12,5%) | **0,2835 (+12,3%)** |
| recursive_default | 0,2412 | 0,2006 (−16,8%) | **0,2764 (+14,6%)** |
| fixed_1024_512 | 0,2510 | 0,2305 (−8,2%) | **0,2790 (+11,2%)** |
| fixed_512_256 | 0,2486 | 0,2260 (−9,1%) | **0,2904 (+16,8%)** |

Na `fixed_512_256`, com correção de Bonferroni sobre 21 pares:

| Comparação | p | vitórias / empates / derrotas |
|---|---:|---|
| controle aleatório × completo | **0,0284** | 53 / 27 / 70 — o controle **perde** |
| controle aleatório × sem relatório | **0,0000** | 40 / 24 / 86 — o controle **perde feio** |

O Recall@100 conta a mesma história: cai de 0,4709 para 0,4310 no controle e
sobe para 0,4993 no recorte.

## A leitura

Jogar fora dois terços do índice **piora** a recuperação, como o bom senso
manda. A única razão de jogar fora dois terços e **melhorar** é que os dois
terços descartados eram sistematicamente os menos úteis.

Isso encadeia com o que a F5 já tinha medido, na ordem certa:

1. **antes da intervenção**, medimos que a fundamentação ocupa 22,8% do texto e
   concentra 72,0% da relevância, enquanto o relatório tem 69,9% do texto e
   25,7% da relevância;
2. medimos que os retrievers recuperam 65–74% pelo relatório — buscam onde há
   volume de texto, não onde há informação;
3. a intervenção derivada dessas duas medições funciona;
4. e o controle mostra que ela **não** funciona por um motivo trivial.

É a diferença entre "achamos uma configuração que melhora o número" e
"identificamos um mecanismo, previmos uma intervenção e ela se confirmou contra
um controle".

## O que o controle não cobre

Ele descarta a explicação "índice menor". Não descarta uma explicação
intermediária: *qualquer* corte que remova texto de baixa densidade informativa
funcionaria, e o relatório é só o maior bloco desse tipo no acórdão. Essa
hipótese é compatível com o nosso resultado e **seria uma contribuição ainda
maior** se confirmada — testá-la exigiria um critério de densidade independente
da estrutura (comprimento de sentença, densidade de termos jurídicos, etc.), e
fica registrado como trabalho futuro em
[../README.md](../README.md).
