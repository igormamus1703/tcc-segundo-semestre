# Branch `leo/f7-enxuta` — a validação externa da F6, no essencial

**Autor:** Leonardo Marques · **Data:** 06/10/2026 · **Status:** ✅ mergeada na `main` em 06/10/2026

A F7 completa (validação externa, ranker aprendido, reranker, fine-tune,
painel) foi feita na branch **`leo/f7-evolucao`**, que fica **guardada como
arquivo, sem merge**. Esta branch traz para a `main` só o que muda o artigo:

1. **o critério `toca`** do recorte por seção (a correção de um defeito da F6);
2. **o `jua.py`**, que reproduz a validação em 7.567 consultas novas;
3. **o `mecanismo.py`**, que sustenta a explicação do defeito.

Todo o resto está resumido no §5 ("já testamos, não repetir"), com os
números e onde encontrar o detalhe.

---

## 1. O que aconteceu, em quatro linhas

- O JUÁ-Juris (Pereira et al. 2026) usa a mesma base de jurisprudência do TCU
  e as mesmas chaves de documento do JurisTCU. Com isso, **7.567 consultas
  novas** foram ligadas aos nossos 12.880 acórdãos, sem reencodar nada.
- O recorte da F6 ("tirar o relatório") **perdeu 12,6%** nas consultas
  difíceis do JUÁ. A causa: no corte fixo, o primeiro pedaço junta a **ementa**
  com o relatório, é rotulado "relatório" e sai junto.
- O critério **`toca`** (descartar só pedaços **100% relatório**) corrige o
  defeito: **não perde em nenhuma amostra** e mantém o ganho no JurisTCU.
- Com 10× mais consultas, **o corte estrutural vence** o fixo e o recursivo,
  porque isola a ementa. É a resposta à pergunta original do TCC, que com 150
  consultas tinha dado empate.

## 2. Para o artigo: o parágrafo e a tabela

**Parágrafo (proposta):**

> *Validamos a seleção de conteúdo em 7.567 consultas adicionais do
> JUÁ-Juris [pereira2026jua] sobre os mesmos acórdãos: 1.567 do conjunto de
> teste, estratificado pelos autores segundo a dificuldade para o BM25, e uma
> amostra de 6.000 do conjunto de treino, em distribuição natural. Remover os
> chunks rotulados pela maioria dos caracteres como relatório falha nas
> consultas difíceis (−12,6%): nas estratégias que não respeitam a fronteira
> entre seções, o primeiro chunk reúne a ementa e o início do relatório e é
> descartado com ela. Remover apenas os chunks inteiramente de relatório
> elimina esse modo de falha e não piora o resultado em nenhuma das amostras.*

**Tabela** (BM25, `fixed_512_256`, nDCG@10; Δ contra o índice completo;
p com Bonferroni sobre 23 comparações por coleção):

| Coleção | n | completo | sem relatório (F6, maioria) | sem relatório (`toca`) | `toca` × F6 |
|---|---:|---:|---:|---:|---:|
| JurisTCU | 150 | 0,2490 | 0,2893 (+16,2%, p = 0,006) | 0,2878 (+15,6%, p = 0,004) | −0,5% (n.s.) |
| JUÁ natural | 6.000 | 0,6549 | 0,7078 (+8,1%, p < 10⁻⁵⁵) | 0,7182 (+9,7%, p < 10⁻⁹⁴) | +1,5% (p < 10⁻¹¹) |
| JUÁ difícil | 1.567 | 0,2497 | 0,2182 (**−12,6%**, p = 0,0002) | 0,2634 (+5,5%, p = 0,24¹) | **+20,7%** (p < 10⁻¹⁷) |

¹ p = 0,012 sem correção. A versão com fusão BM25 + denso do `toca` dá
**0,3225** no JurisTCU, empatada com a fusão das 4 da F6 (0,3215).

**Sobre a "pré-registração":** a hipótese do `toca` foi registrada (commit
`1e017f5`, branch `leo/f7-evolucao`) **antes** de rodar a amostra natural.
Pode ser citada no texto como confirmação em dados não vistos.

## 3. O mecanismo (uma figura, se couber)

Dividindo as consultas pela fração dos seus termos que aparecem na ementa do
acórdão certo (`src/mecanismo.py`, rodada `*_f7_mecanismo`):

| Quartil | JUÁ difícil: F6 | JUÁ difícil: `toca` | JUÁ natural: F6 | JUÁ natural: `toca` |
|---|---:|---:|---:|---:|
| Q1–Q3 (consulta pouco parecida com a ementa) | −5% a +2% | −3% a +4% | +9% a +11% | +9% a +11% |
| **Q4 (consulta ≈ ementa)** | **−28,4%** | **+12,5%** | **+2,4%** | **+9,3%** |

O defeito da F6 está **inteiro** no quartil em que a consulta repete a ementa.

## 4. A pergunta original, agora com poder

BM25, índice completo, estrutural **predito** (o segmentador) contra cada
alternativa (rodada `*_f7_replicacao_final`, `equivalencia.csv`):

| | JurisTCU (150) | JUÁ natural (6.000) | JUÁ difícil (1.567) |
|---|---:|---:|---:|
| × fixo 512/256 | +1,4% (n.s.) | **+1,2%** (p = 0,005) | **+7,3%** (p = 0,0001) |
| × recursivo | +4,8% (n.s.) | **+2,4%** (p < 10⁻⁸) | **+9,9%** (p < 10⁻⁵) |
| × estrutural ouro | **equivalentes** (TOST ±0,01) | **equivalentes** | **equivalentes** |

**Por quê:** tirando a ementa do índice estrutural, a vantagem vira
desvantagem (−20,9% contra o fixo nas difíceis; −2,3% nas naturais). O corte
estrutural ganha por **isolar a ementa**. No JurisTCU, onde a ementa carrega
0,4% da relevância, não há efeito, e isso explica o empate da F5.

**Frase para a Conclusão:** *isoladamente, a estratégia de chunking tem efeito
pequeno, que 150 consultas não detectam; com 7.567, o corte estrutural vence
de forma consistente, e é ele que torna a seleção de conteúdo por seção
segura.*

## 5. Já testamos — não repetir

A documentação completa está em [`../leo-f7-evolucao/`](../leo-f7-evolucao/README.md)
(também na `main`); o código, os testes e as rodadas, na branch-arquivo
**`leo/f7-evolucao`** do GitHub. A página visual da F7 completa está em
[`docs/apresentacao/f7.html`](../../../apresentacao/f7.html).

| O que | Resultado | Lição |
|---|---|---|
| **Ranker aprendido** (LambdaRank, 12 sinais por seção, treinado em 6.000 consultas do JUÁ) | No JurisTCU, que ele nunca viu: **+18,6%** sobre o BM25 e +16,5% sobre o mesmo modelo sem seções. Funciona igual com o segmentador (≡ ouro). SHAP: casar no relatório vale **~5× menos** que na fundamentação | **Funciona**, mas empata com a fusão das 4 no JurisTCU e acrescenta um modelo treinado ao trabalho. Ficou de fora por escopo; é o melhor candidato a trabalho futuro. Doc `04` |
| **Reranker zero-shot** (`bge-reranker-v2-m3`, top-50 da fusão) | JurisTCU: **−15,9%** contra a fusão; lendo só fora do relatório, +17,9%. JUÁ: abaixo do BM25 | Não supera o primeiro estágio. Útil só como evidência de que **até um modelo neural se deixa levar pelo relatório** (uma frase no texto). Doc `05` |
| **Fine-tune LoRA do reranker** (5 mil consultas do JUÁ, positivo = trecho do excerto) | **−60%**, inclusive no próprio JUÁ | ⚠️ **Não repetir assim.** Negativos tirados só do BM25 ensinam o atalho "casamento literal = errado" (Spearman score × sobreposição: +0,59 → −0,17). Com negativos mistos (v2), −24% a −28% contra o zero-shot. O treino precisaria ser no nível do documento. Doc `05` |
| **Fusão BM25 + denso no JUÁ** | **Piora** (−11%): o denso é 35% a 55% pior que o BM25 nessa coleção | A fusão de peso igual só ajuda quando os dois retrievers têm força parecida |
| **Recorte pela maioria dos caracteres em corte fixo** | O defeito da ementa (§1) | Use `--secoes-criterio toca` ou corte estrutural |
| **LTR v1** | Normalização desalinhada (top-200 no treino × top-1.000 no teste) fazia o modelo "sem seções" ficar 29% abaixo do BM25 | Sempre cortar cada sinal no mesmo top-k **antes** do min-max |
| **Avaliação completa (`src.evaluate`) com 1.567 consultas × 25 runs** | >50 min só nos 300 pares de significância | Para coleções grandes, usar a análise de replicação (pares escolhidos), não todos contra todos |

**Previsões que erraram** (registradas antes de rodar): o recorte da F6
replicar no JUÁ difícil (não replicou); as estratégias serem equivalentes
(o estrutural venceu); o recorte da F6 piorar também nas consultas naturais
(melhorou 8%).

## 6. Como reproduzir

```bash
cd juris-chunking
python -m src.jua                                   # consultas e qrels do JUÁ -> data/interim/jua/
python -c "from src.jua import amostra_treino; amostra_treino()"   # amostra natural (6.000)

# o recorte corrigido (qualquer coleção: troque --queries)
python -m src.run_experiments --strategy all --retriever bm25 \
    --secoes sem:relatorio --secoes-criterio toca --label bm25_sec_sem_relatorio_toca
python -m src.run_experiments --strategy all --retriever bm25 --queries data/interim/jua/queries_test.jsonl \
    --secoes sem:relatorio --secoes-criterio toca --label jua_bm25_sec_sem_relatorio_toca

# avaliar no JUÁ
python -m src.evaluate --experiment <rodada> --qrels data/interim/jua/qrels_test.trec \
    --queries data/interim/jua/queries_test.jsonl

# o mecanismo por quartil
python -m src.mecanismo --label f7_mecanismo
```

`--secoes-criterio` tem padrão `maioria`, que reproduz a F6 byte a byte.

## 7. Entregas e testes

| Arquivo | O que é |
|---|---|
| `src/sections.py`, `src/run_experiments.py` | critério `toca` (`toca_alguma`, `--secoes-criterio`) |
| `src/jua.py` | JUÁ-Juris → acórdãos do corpus, seção da resposta, amostra de treino, recorte independente |
| `src/mecanismo.py` | efeito do recorte por quartil de sobreposição consulta × ementa |
| `REFERENCIAS.md` (raiz) | bibliografia do artigo, com BibTeX e nível de verificação |
| `results/experiments/20261005-*` | as 15 rodadas que sustentam os números acima |

**201 testes** (191 da F6 + 10): o critério `toca` mantém o chunk misto
ementa+relatório e respeita o rótulo das estruturais; o offset do excerto cai
na seção certa no texto original; e a medida de sobreposição.
