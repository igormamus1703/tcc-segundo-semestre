# A segunda coleção: JUÁ-Juris sobre os mesmos 12.880 acórdãos

**Data:** 05/10/2026 · **Autor:** Leonardo Marques
**Código:** `juris-chunking/src/jua.py` · **Testes:** `tests/test_jua.py`

---

## Por que uma segunda coleção

Até a F6, tudo foi medido em **150 consultas** do JurisTCU. Isso trava o
trabalho em dois pontos:

- **Poder estatístico.** O efeito mínimo detectável entre estratégias de
  chunking ficou em ~0,02 de nDCG@10. "Não deu diferença" com esse MDE quer
  dizer pouco.
- **Circularidade.** A decisão de tirar o relatório veio de olhar os mesmos
  julgamentos usados para medir o ganho. A validação cruzada da F6 mostrou
  estabilidade *dentro* das 150 consultas, não fora delas.

Uma segunda coleção resolve os dois problemas, desde que use os **mesmos
documentos**: com outros documentos, mudariam duas variáveis ao mesmo tempo.

## A descoberta que tornou isso barato

O JUÁ-Juris (Pereira et al. 2026, arXiv:2604.06098) vem da mesma base de
jurisprudência selecionada do TCU que o JurisTCU. Cada instância é um par
(enunciado, excerto): o enunciado vira a consulta, e o excerto é o relevante.

Os ids do JUÁ têm a forma `JURISPRUDENCIA-SELECIONADA-<N>`, e **`<N>` é o mesmo
`KEY` do `doc.csv` do JurisTCU**. A partir do `KEY`, o mesmo join da ingestão
(`NUMACORDAO`, `ANOACORDAO`, `COLEGIADO`) leva cada excerto ao acórdão íntegro
que o contém, e esse acórdão já está no nosso corpus.

**Custo: zero reencode.** Os índices BM25 e os embeddings da F4 servem como
estão; só as consultas são novas.

## Números da construção

| | teste | treino |
|---|---:|---:|
| pares no JUÁ-Juris | 1.714 | 15.433 |
| fora do nosso corpus (sem acórdão ou sem join) | 147 | 1.216 |
| **consultas mapeadas** | **1.567** | **14.217** |
| acórdãos distintos | 1.526 | 11.662 |

**Protocolo:** consulta = enunciado; relevante = o acórdão que contém o
excerto, com relevância binária (*known-item*). Outros acórdãos podem ser
relevantes e não estão julgados; os valores absolutos são um limite inferior,
e a comparação pareada entre sistemas continua válida.

## Onde mora a resposta

Para cada consulta, o excerto é localizado **dentro** do acórdão, com o mesmo
método da análise de domínio da F4 (âncora de 120 caracteres, texto sem acento
e sem caixa), e mapeado contra os spans ouro.

| Seção do excerto | teste | % |
|---|---:|---:|
| fundamentação | 938 | 59,9% |
| dispositivo | 198 | 12,6% |
| relatório | 148 | 9,4% |
| ementa | 8 | 0,5% |
| não localizado | 275 | 17,5% |

A seção vai no campo `source` da consulta. Com isso, todo recorte "por tipo de
consulta" do `src.evaluate` vira, sem código novo, um recorte "por seção onde
mora a resposta", que é o teste direto da limitação declarada na F6.

**Um detalhe que pegou na implementação.** A âncora é procurada no texto
*dobrado* (sem acento, espaços colapsados), mas os spans estão em offsets do
texto *original*. `mapa_dobrado` guarda, para cada caractere dobrado, a
posição de onde ele veio. Sem isso, a seção seria resolvida com o offset
errado e o recorte por seção mediria outra coisa, sem levantar erro. Isso está
travado por `test_excerto_com_acento_e_espacos_diferentes_cai_na_secao_certa`.

## Independência em relação ao JurisTCU

As consultas sintéticas do JurisTCU também vieram de enunciados (os dos 50
documentos mais acessados). Nada é treinado nelas, então não há vazamento; mas
a coleção não é 100% independente da que guiou a F6.

**Medido:** 194 das 1.567 consultas de teste (12,4%) apontam para acórdãos que
são relevantes para alguma consulta do JurisTCU. A **coleção independente**
(`queries_test_indep.jsonl`, 1.373 consultas) tira essas 194, e toda análise da
F7 é reportada também nela.

## Treino

O split de treino (14.217 consultas) nunca entra na avaliação. Uma amostra fixa
de 6.000 delas (`queries_train_amostra.jsonl`, semente 42) é usada para treinar
o ranker aprendido (`src/ltr.py`). Ver [04-ranker-aprendido.md](04-ranker-aprendido.md).

## Diferença de tarefa (importante para ler os resultados)

| | JurisTCU | JUÁ-Juris |
|---|---|---|
| consulta | log real (G1), palavras-chave e pergunta sintéticas | enunciado (a tese, em uma frase) |
| relevância | graduada 0–3, julgada por LLM + especialista sobre um pool | binária, *known-item*: o acórdão de onde saiu o excerto |
| relevantes por consulta | ~15 | 1 |
| pergunta que mede | "quais acórdãos firmam esta tese?" | "qual é o acórdão que firmou esta tese?" |

As duas são tarefas legítimas de busca de jurisprudência, mas **não são a mesma
tarefa**. Isso vai importar: ver [02-replicacao.md](02-replicacao.md).
