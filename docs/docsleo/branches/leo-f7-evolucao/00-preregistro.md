# Pré-registro da F7: hipóteses fixadas antes de rodar

**Data:** 05/10/2026 · **Autor:** Leonardo Marques
**Status:** 🔒 congelado no commit que cria este arquivo, **antes** de qualquer
rodada sobre o JUÁ-Juris. Mudanças posteriores entram como adendo datado no
fim, nunca editando o texto acima.

---

## Por que pré-registrar

A F6 deixou duas fraquezas que nenhuma análise sobre as mesmas 150 consultas
resolve:

1. **Circularidade.** A decisão de tirar o relatório veio de olhar os
   julgamentos de relevância, que depois serviram para avaliar. A validação
   cruzada mostrou que a escolha é estável *dentro* das 150 consultas, mas não
   fora delas.
2. **Poder.** Com 150 consultas, o efeito mínimo detectável (MDE) entre
   estratégias de chunking fica em ~0,02 de nDCG@10. Nas 50 consultas reais de
   log, nem o ganho do recorte é significativo (p = 0,23).

A F7 testa os achados da F6 numa **segunda coleção de consultas, independente
de tudo o que guiou as decisões**: o JUÁ-Juris (Pereira et al. 2026). São
**1.567 consultas de teste** cujo acórdão relevante já está no nosso corpus de
12.880, sobre os mesmos índices e os mesmos embeddings (`src/jua.py`).

Escrever as previsões antes é o que separa *replicação* de *mais uma busca
pelo número bom*.

## A coleção (construída antes deste documento, sem olhar nenhum ranking)

| | teste | treino |
|---|---:|---:|
| pares (enunciado, excerto) no JUÁ-Juris | 1.714 | 15.433 |
| **consultas com o acórdão no nosso corpus** | **1.567** | 14.217 |
| resposta localizada na fundamentação | 938 (59,9%) | 8.417 |
| na dispositivo | 198 (12,6%) | 1.895 |
| no relatório | 148 (9,4%) | 2.039 |
| na ementa | 8 (0,5%) | 62 |
| excerto não localizado no texto | 275 (17,5%) | 1.804 |

**Protocolo:** consulta = enunciado; relevante = o acórdão que contém o
excerto (binário). Avaliação só no split de **teste**. O split de treino fica
reservado para escolher hiperparâmetros, se algum método precisar.

## Hipóteses e previsões

Métrica principal: **nDCG@10**. Secundárias: MRR@10 e Recall@100. Testes: t
pareado bilateral com Bonferroni sobre os pares da tabela (como na F5/F6),
mais IC 95% por bootstrap.

| # | Hipótese | Previsão registrada | Confirma se |
|---|---|---|---|
| **H1** | O recorte "sem relatório" replica | BM25 sem relatório > BM25 completo nas **5** estratégias | p < 0,05 corrigido em ≥ 4 das 5 |
| **H2** | O controle replica | O mesmo número de chunks sorteados **piora** | Δ < 0 na `fixed_512_256` |
| **H3** | A fusão replica | Fusão das 4 condições > BM25 completo; recorte + fusão (peso igual, só índices recortados) > BM25 sem relatório | p < 0,05 nas duas |
| **H4** | **O recorte depende de onde mora a resposta** (a limitação declarada na F6) | Quando a resposta está no **relatório**, o recorte **piora**; quando está na fundamentação, melhora | sinal oposto nos dois estratos, com o do relatório < 0 |
| **H5** | A pergunta original, agora com poder | As 5 estratégias são **praticamente equivalentes**: \|Δ\| < 0,01 entre quaisquer duas | teste de equivalência (TOST, margem ±0,01) passa para a maioria dos pares |
| **H6** | Reranking com cross-encoder | `bge-reranker-v2-m3` sobre o top-100 melhora a melhor configuração da F6 nas **duas** coleções | p < 0,05 nas duas |
| **H7** | O recorte sobrevive ao reranker | Reranquear lendo só passagens fora do relatório ≥ reranquear lendo todas | Δ ≥ 0 nas duas coleções |

**Sobre H4:** a previsão é de sinal, não de magnitude. Com 148 consultas no
estrato do relatório, o teste tem poder para efeitos de ~0,03 ou mais.

**Sobre H5:** "não deu diferença significativa" não prova igualdade. Com
1.567 consultas o MDE cai para ~0,006, e o TOST permite afirmar
*equivalência prática*, que é a frase que a banca aceita.

## Ameaças conhecidas, declaradas antes

1. **As consultas do JUÁ-Juris são enunciados: teses jurídicas.** Isso
   favorece a fundamentação pelo mesmo mecanismo do JurisTCU. Uma replicação
   de H1 **não** prova que o recorte vale para consultas factuais. É por isso
   que H4 existe: ela mede o recorte justamente nas consultas cuja resposta
   está no relatório.
2. **Sobreposição com o JurisTCU.** As consultas sintéticas do JurisTCU vieram
   dos enunciados de 50 documentos. Se algum desses enunciados estiver no teste
   do JUÁ, a coleção não é 100% independente. Vai ser medido e reportado, e a
   análise principal é refeita sem essas consultas.
3. **Relevância esparsa.** Um relevante por consulta; outros acórdãos
   relevantes não estão julgados. Os valores absolutos são um limite inferior;
   a comparação pareada entre sistemas continua válida.
4. **17,5% de excertos não localizados.** Entram em todas as análises, exceto
   na estratificação de H4, onde formam um estrato próprio.

## Critério de "valeu a pena" para o merge

A F7 vai para a `main` se **pelo menos uma** destas valer:

- **(a)** H1 e H2 replicam, e o achado principal da F6 passa a ter validação
  externa;
- **(b)** H5 confirma equivalência, e a pergunta original ganha uma resposta
  com poder estatístico, em vez de "não deu diferença";
- **(c)** H6 dá um ganho ≥ 5% sobre a melhor configuração da F6, significativo
  nas duas coleções.

**Se nenhuma valer,** o resultado é documentado nesta pasta (negativo também é
resultado) e a `main` continua no estado da F6. Se H1 **falhar**, isso
precisa ir para o artigo mesmo assim: um achado que não replica não pode
continuar sendo a manchete.

---

## Adendos

### Adendo 1 — 05/10/2026, antes de qualquer resultado do JUÁ-Juris

Desvios do plano, todos decididos **antes** de ver os números do JUÁ (o único
resultado já visto é o do reranker no JurisTCU, a coleção da F6):

1. **H6/H7 reranqueiam o top-50, não o top-100.** O `__chunks.jsonl` que cada
   run grava só guarda o chunk vencedor dos 50 primeiros documentos, e
   regravá-lo exigiria refazer todas as rodadas. Para o nDCG@10, top-50 basta;
   o Recall@100 dos runs reranqueados herda a ordem original do 51º em diante.
2. **H7 ganha uma terceira variante, exploratória** (`sem_relatorio_preserva`).
   No JurisTCU, a variante `sem_relatorio` deixa 16,6% dos documentos sem
   passagem permitida, que são rebaixados para depois dos lidos. Isso mistura
   dois efeitos: *o que o modelo lê* e *quem é rebaixado*. A variante nova lê
   pelo relatório quem não tem outra passagem, e isola o primeiro efeito. **A
   confirmação de H7 continua sendo a da variante pré-registrada**; a nova
   serve para interpretá-la.
3. **Ameaça 2 medida:** 194 das 1.567 consultas de teste (12,4%) apontam para
   acórdãos que são relevantes para alguma consulta do JurisTCU. A
   especificação ganha uma terceira coleção, **"JUÁ-Juris (independente)"**,
   com 1.373 consultas, sem elas. É análise de sensibilidade: as hipóteses
   continuam sendo julgadas no teste inteiro.
4. **Resultado já visto no JurisTCU, registrado aqui para não parecer
   descoberto depois:** reranquear a fusão das 4 lendo **todas** as passagens
   dá 0,2704 (−15,9% contra a fusão, p < 0,0001); lendo só passagens **fora
   do relatório**, 0,3189 (+17,9% sobre ler todas, p < 0,000001). No JurisTCU,
   H7 confirma e H6 não.
