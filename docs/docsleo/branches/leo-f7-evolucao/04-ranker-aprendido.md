# Ranker aprendido: quanto vale cada seção, segundo os dados

**Data:** 05/10/2026 · **Autor:** Leonardo Marques
**Código:** `src/ltr.py` · **Especificação:** `configs/f7_ltr.json` · **Testes:** `tests/test_ltr.py`
**Rodada:** `results/experiments/20261005-1706_f7_ltr` (v2; a v1 está em `20261005-1659_f7_ltr`)

> **Resumo.** Um LambdaRank (LightGBM) treinado em 6.000 consultas do *treino*
> do JUÁ-Juris, com sinais de busca por seção, **transfere para o JurisTCU**,
> uma coleção que ele nunca viu: +18,6% sobre o BM25 e +16,5% sobre o mesmo
> modelo sem os sinais por seção (p < 0,0001). O SHAP mostra o que ele
> aprendeu: **um casamento no relatório vale cerca de 5× menos que o mesmo
> casamento na fundamentação**. É a decisão manual da F6 ("tire o
> relatório"), redescoberta pelos dados, sem circularidade.

---

## Por que um modelo aprendido

A F6 decidiu à mão: tira o relatório, mantém o resto. Era uma decisão binária,
tomada olhando os julgamentos do mesmo benchmark em que foi medida. A F7
mostrou que ela tem um modo de falha ([03](03-fronteira-e-criterio-toca.md)) e
que o valor do relatório depende da tarefa.

Um modelo aprendido troca o corte por **pesos estimados dos dados**. Para não
haver circularidade:

- **treino:** 6.000 consultas do split de *treino* do JUÁ-Juris (amostra fixa,
  semente 42);
- **teste:** o split de *teste* do JUÁ-Juris (1.567) e o **JurisTCU** (150),
  com outro tipo de consulta e relevância graduada, nunca tocado no treino.

É a versão aprendida do BM25F (Robertson et al. 2004), com pesos por campo
estimados por LambdaMART (Burges 2010) em vez de fixados.

## Desenho

**Estratégia:** `structural_gold`, a única em que o sinal "só a seção X" é
limpo. Nas fixas, o chunk 0 mistura ementa e relatório
([03](03-fronteira-e-criterio-toca.md)).

**Candidatos:** a união do top-100 de quatro buscas (BM25 e denso, documento
inteiro e sem relatório).

**Sinais (12):** BM25 e denso, cada um sobre o documento inteiro, sem o
relatório e sobre cada seção isolada. De cada um saem o score min-max no
top-200 da consulta e a posição (201 = ausente). Mais dois atributos do
documento: log do tamanho e fração que é relatório. **26 atributos.**

**Modelo:** `LGBMRanker`, objetivo LambdaRank, taxa 0,03, 31 folhas, até 3.000
árvores com early stopping (200) em 15% das consultas de treino separadas
**por consulta**. Hiperparâmetros fixos desde o início: nada foi ajustado
olhando o teste.

**Ablações (mesmo treino, mesmos hiperparâmetros):**

| Modelo | Sinais | Pergunta que responde |
|---|---|---|
| `ltr_secoes` | os 12 | o modelo completo |
| `ltr_sem_secoes` | BM25 e denso, documento inteiro | **a fusão aprendida "comum"**: a estrutura agrega algo? |
| `ltr_recorte_f6` | documento inteiro e sem relatório | só a informação que a F6 usava |

## Resultados (v2)

| | JUÁ-Juris (teste) | JurisTCU (nunca visto) |
|---|---:|---:|
| BM25, estrutural (ouro) | 0,2699 | 0,2523 |
| fusão das 4 da F6, estrutural (ouro) | 0,2505 | 0,3065 |
| fusão das 4 da F6, fixo 512/256 | 0,2215 | **0,3215** |
| LTR sem seções | 0,2759 | 0,2567 |
| LTR só com o recorte da F6 | **0,2881** | 0,2828 |
| **LTR com seções** | 0,2781 | 0,2991 |

| Comparação | JUÁ-Juris | JurisTCU |
|---|---:|---:|
| **LTR com seções × LTR sem seções** | +0,8% (p = 0,61) | **+16,5% (p = 0,00004)** |
| LTR com seções × BM25 | +3,1% (p = 0,06) | **+18,6% (p = 0,00001)** |
| LTR com seções × fusão das 4 (mesma estratégia) | **+11,1% (p < 10⁻⁵)** | −2,4% (p = 0,48) |
| LTR com seções × fusão das 4 (fixo 512/256) | **+25,5% (p < 10⁻¹⁵)** | −6,9% (p = 0,04) |
| LTR só com o recorte da F6 × BM25 | **+6,7%** | +12,1% |

**Leitura.**

1. **A informação de seção transfere.** Treinado só em enunciados do JUÁ, o
   modelo usa as seções de um jeito que vale **+16,5%** numa coleção e numa
   tarefa que ele nunca viu. No JUÁ, os sinais por seção não acrescentam além
   do documento inteiro (+0,8%, n.s.): a tarefa de lá se resolve bem com o
   documento todo.
2. **Nenhuma receita fixa ganha nas duas coleções; o modelo aprendido fica
   perto do melhor em ambas.** A fusão das 4 da F6 é a melhor no JurisTCU
   (0,3215), onde foi escolhida, e a pior no JUÁ (0,2215). O LTR com seções
   empata com ela no JurisTCU (mesma estratégia, p = 0,48) e ganha dela por
   11% a 25% no JUÁ.
3. **O modelo enxuto `ltr_recorte_f6` é o melhor no JUÁ** (0,2881) e o segundo
   no JurisTCU. Com 4 sinais em vez de 12, é a escolha de custo-benefício.

## A versão implantável: sem a estrutura ouro

Um acervo real não publica a estrutura em colunas. O mesmo LTR foi refeito
sobre o **`structural_pred`** (o segmentador por regras da F2), com os
atributos do documento (tamanho, fração de relatório) calculados a partir dos
chunks rotulados pelo segmentador, e não dos spans ouro
(`configs/f7_ltr_pred.json`, rodada `*_f7_ltr_pred`):

| | JUÁ-Juris (teste) | JurisTCU |
|---|---:|---:|
| LTR com seções, **ouro** | 0,2781 | 0,2991 |
| LTR com seções, **predito** | 0,2781 | 0,2976 |
| predito × ouro | −0,0% (p = 0,98) | −0,5% (p = 0,75) |
| predito × BM25 (predito) | +3,8% (p = 0,016) | **+17,8% (p < 10⁻⁵)** |
| predito × LTR sem seções | +1,9% (p = 0,20) | **+18,0% (p < 10⁻⁵)** |

**O modelo não depende da estrutura oficial do TCU.** É o mesmo resultado da
ablação ouro × predito da F5–F7, agora para o modelo aprendido.

## O que o modelo aprendeu (SHAP)

O LightGBM calcula valores SHAP exatos para árvores (`pred_contrib`).

**Participação na média de |SHAP|** (figura `__shap_secoes`; quase idêntica
nas duas coleções):

| | documento inteiro | sem relatório | ementa | relatório | fundamentação | dispositivo |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 41,1% | 26,0% | 0,4% | **2,6%** | **14,0%** | 3,3% |
| denso | 1,0% | 0,4% | 0,5% | 0,6% | 1,0% | 0,4% |

- **A evidência fora do relatório** (sem relatório, fundamentação, dispositivo
  e ementa) soma **~44%**; o relatório isolado, **2,6%**.
- O denso contribui pouco (~4%): no treino (JUÁ), ele é bem mais fraco que o
  BM25 (0,16 × 0,25), e o modelo aprende isso.

**Dependência** (figura `__shap_dependencia`): para um documento com o mesmo
score normalizado numa seção, a contribuição ao score final é **~0,75 quando o
casamento é na fundamentação e ~0,15 quando é no relatório**, nas duas
coleções. É a figura que resume o trabalho: **o mesmo casamento de termos vale
cerca de 5× menos quando acontece no relatório.**

## A v1 tinha dois defeitos (registrados, não escondidos)

A primeira versão (`20261005-1659_f7_ltr`) foi descartada depois de olhar o
JurisTCU, por dois motivos de **engenharia**, não de resultado:

1. **Normalização desalinhada.** Os sinais de treino vinham de runs com 200
   documentos por consulta; parte dos de teste, de runs com 1.000. O min-max
   sobre uma lista mais longa empurra todos os scores para cima: o modelo
   recebia no teste uma distribuição que nunca viu. Sintoma: o "LTR sem
   seções" ficava **29% abaixo do próprio BM25** no JurisTCU (0,1796), o que é
   impossível para um modelo que recebe o score do BM25 como atributo e
   aprendeu bem no JUÁ. Correção: cortar todo sinal no top-200 **antes** do
   min-max. Travado por `test_normalizar_corta_antes_do_minmax`.
2. **Atributo sem cobertura.** O tamanho da consulta: o treino só tem
   enunciados (10 a 60 palavras), e o JurisTCU tem consultas de 3. Uma árvore
   extrapola uma divisão aprendida em "12 palavras" para um regime que nunca
   viu. Removido.

Números da v1, para o registro: JUÁ 0,2810 / 0,2685 / 0,2870; JurisTCU
0,2924 / 0,1796 / 0,2788 (com seções / sem seções / recorte F6). **A conclusão
principal não mudou entre as versões:** com seções > sem seções no JurisTCU,
nas duas.

**Ressalva honesta:** as duas correções foram decididas *depois* de ver os
números da v1 no JurisTCU. Elas corrigem defeitos objetivos (o sintoma do
primeiro é aritmeticamente impossível), mas o leitor deve saber que a v2 não é
cega ao teste.

## Detalhes que importam para reproduzir

- 1.195.522 pares (consulta, documento) de treino; melhor iteração 262.
- O nDCG@10 de validação (0,758) é muito maior que o de teste: a validação vem
  da distribuição natural do JUÁ (fácil), e o teste foi estratificado por
  dificuldade (ver [03](03-fronteira-e-criterio-toca.md), §3). Além disso, o
  LightGBM conta como 1 o nDCG de consultas sem relevante entre os candidatos.
- `python -m src.ltr --spec configs/f7_ltr.json` treina, aplica e gera as
  figuras; `--figuras-de <rodada>` regera só as figuras.
