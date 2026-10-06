# A pergunta original do TCC, agora com poder estatístico

**Data:** 05/10/2026 · **Autor:** Leonardo Marques
**Pergunta:** *chunking que respeita as macro-seções do acórdão recupera melhor que chunking fixo ou recursivo?*

> **Resumo.** Com 150 consultas (F5/F6), a resposta foi "empate", com efeito
> mínimo detectável de ~0,02. Com o JUÁ-Juris (1.567 consultas difíceis e
> 6.000 naturais, sobre os mesmos acórdãos), **o chunking estrutural vence
> todas as alternativas, com significância**: +7% a +12% nas consultas
> difíceis e +1% a +3% nas naturais. O segmentador automático é **equivalente**
> à estrutura ouro nas três coleções (teste de equivalência). O empate da F5
> era falta de poder e uma tarefa em que o efeito não aparece, não ausência de
> efeito.

---

## Método

BM25, índice completo, as cinco estratégias da F3. Para cada par:

- **diferença pareada** com t bilateral (Smucker et al. 2007);
- **teste de equivalência (TOST)** com margem ±0,01 de nDCG@10 (Schuirmann
  1987; Lakens 2017): os dois são "praticamente iguais" se o IC 90% da
  diferença couber inteiro em (−0,01; +0,01).

"Não deu diferença significativa" não prova igualdade, e o TOST existe para
isso. Com 150 consultas, quase nada passa no TOST: não há resolução para
afirmar nem diferença nem igualdade. Com 1.567 e 6.000, há.

## Resultado

### nDCG@10 por estratégia

| Estratégia | JurisTCU (150) | JUÁ difícil (1.567) | JUÁ natural (6.000) |
|---|---:|---:|---:|
| **estrutural (ouro)** | 0,2523 | **0,2699** | **0,6639** |
| **estrutural (predito)** | 0,2526 | **0,2679** | **0,6628** |
| fixo 512/256 | 0,2490 | 0,2497 | 0,6549 |
| fixo 1024/512 | 0,2510 | 0,2407 | 0,6514 |
| recursivo | 0,2410 | 0,2437 | 0,6470 |

### Estrutural (predito), o deployável, contra cada alternativa

| | JurisTCU | JUÁ difícil | JUÁ natural |
|---|---:|---:|---:|
| × fixo 512/256 | +1,4% (p = 0,64) | **+7,3% (p = 0,00014)** | **+1,2% (p = 0,005)** |
| × fixo 1024/512 | +0,6% (p = 0,81) | **+11,3% (p < 10⁻⁷)** | **+1,7% (p < 10⁻⁴)** |
| × recursivo | +4,8% (p = 0,11) | **+9,9% (p < 10⁻⁵)** | **+2,4% (p < 10⁻⁸)** |
| × estrutural (ouro) | **equivalentes** (TOST) | **equivalentes** (TOST) | **equivalentes** (TOST) |

## Leitura

1. **O efeito existe, e o tamanho depende da consulta.** Nas consultas que o
   BM25 acha difíceis, separar as seções vale 7% a 12%; nas naturais, 1% a 3%.
   No JurisTCU, com 150 consultas, não há resolução para ver nem um nem outro.
2. **O mecanismo é a ementa isolada, e foi testado.** O corte estrutural põe
   a ementa num chunk próprio, curto e denso em termos da tese, e o BM25 (com
   normalização por tamanho) o favorece quando a consulta é uma tese em uma
   frase. **Ablação:** tirando a ementa do índice estrutural, a vantagem
   desaparece e vira desvantagem:

   | | estrutural × fixo | estrutural **sem ementa** × fixo | efeito de tirar a ementa |
   |---|---:|---:|---:|
   | JUÁ difícil, ouro | +8,1% | **−20,9%** | −26,9% (p < 10⁻²⁸) |
   | JUÁ difícil, predito | +7,3% | **−18,5%** | −24,0% (p < 10⁻²⁴) |
   | JUÁ natural, ouro | +1,4% | **−2,3%** | −3,6% (p < 10⁻³¹) |
   | JUÁ natural, predito | +1,2% | **−2,2%** | −3,4% (p < 10⁻²⁸) |

   No JurisTCU, onde a ementa carrega 0,4% da relevância (F4) e tirá-la custa
   −0,1% (auditoria da F6), o efeito some — coerente com o mecanismo. Rodadas:
   `*_jua_bm25_sec_sem_ementa`, `*_juanat_bm25_sec_sem_ementa`.
3. **O segmentador por regras basta.** Ouro × predito é equivalente nas três
   coleções, com a margem de ±0,01. É o que torna o resultado aplicável a
   acervos que não publicam a estrutura em colunas, agora com prova de
   equivalência em vez de "p alto".
4. **Combinado com a seleção de conteúdo**, o estrutural é a única estratégia
   em que o recorte por seção é seguro em todas as amostras
   ([03](03-fronteira-e-criterio-toca.md)).

## A frase para o artigo

> *Isoladamente, a estratégia de chunking tem efeito pequeno, e com 150
> consultas ele é indetectável. Com 7.567 consultas adicionais sobre os mesmos
> acórdãos, o chunking que respeita as macro-seções supera o fixo e o
> recursivo de forma consistente (+1% a +3% em consultas naturais, +7% a +12%
> nas difíceis), e o segmentador automático é estatisticamente equivalente à
> estrutura oficial. O efeito cresce quando o pipeline seleciona conteúdo por
> seção: aí, só o corte estrutural evita o artefato de fronteira.*

## Rodadas

`*_bm25` (JurisTCU), `*_jua_bm25` (JUÁ difícil), `*_juanat_bm25` (JUÁ natural).
Os testes de equivalência saem de `src.replicacao` com
`configs/f7_replicacao_final.json` (figuras `__equivalencia_completo` e
`__equivalencia_toca`).
