# O recorte da F6 tinha um defeito, e a estrutura do acórdão o resolve

**Data:** 05/10/2026 · **Autor:** Leonardo Marques
**Código:** `src/sections.py` (`toca_alguma`, `filtrar(..., criterio=)`), `--secoes-criterio` no `src.run_experiments`
**Testes:** `tests/test_sections.py` (três testes novos)

> **Resumo.** No JUÁ-Juris, o recorte "sem relatório" da F6 **piorou** as
> estratégias fixas e a recursiva (−13% a −21%). A causa é um artefato de
> fronteira: o chunk 0 junta a ementa com o começo do relatório, é rotulado
> "relatório" pela maioria dos caracteres e sai junto com a ementa. Um critério
> que só descarta chunks **100% relatório** (`toca`) corrige o defeito: o
> recorte passa a ganhar **nas três amostras de consultas**, inclusive em
> 6.000 consultas nunca usadas em análise, onde a hipótese foi pré-registrada.

---

## 1. O que apareceu

Primeira rodada do JUÁ-Juris (1.567 consultas de teste), BM25, recorte da F6:

| Estratégia | completo | sem relatório (F6) | Δ | p |
|---|---:|---:|---:|---:|
| structural_gold | 0,2699 | 0,2699 | −0,0% | 0,996 |
| structural_pred | 0,2679 | 0,2569 | −4,1% | 0,05 |
| recursive_default | 0,2437 | 0,1917 | **−21,3%** | 10⁻¹² |
| fixed_1024_512 | 0,2407 | 0,1920 | **−20,2%** | 10⁻¹¹ |
| fixed_512_256 | 0,2497 | 0,2182 | **−12,6%** | 10⁻⁵ |

No JurisTCU, as mesmas cinco linhas eram **+11% a +16%**, todas
significativas. O padrão salta aos olhos: o recorte só destrói as estratégias
que **não respeitam a fronteira entre seções**.

## 2. O mecanismo: a ementa sai junto

Caso típico (consulta `jua-32845`, acórdão `1856-2007-primeira_câmara`):

- A consulta é o enunciado: *"Contra decisão genérica e abstrata, tomada no
  âmbito da jurisdição objetiva, não deve ser conhecido o recurso interposto
  por quem apenas se considera ameaçado pelo julgamento..."*
- A **ementa** do acórdão (326 caracteres) diz quase o mesmo: *"Não se
  conhece de recurso contra decisão genérica e abstrata, tomada no âmbito da
  jurisdição objetiva, se interposto por quem apenas se considera ameaçado..."*
- No `fixed_512_256`, o **chunk 0** junta esses 326 caracteres de ementa com
  ~1.700 de relatório. Pela maioria dos caracteres, é "relatório".
- BM25 completo: o acórdão certo fica em **1º**, ganhando pelo chunk 0.
  Recorte da F6: o chunk 0 sai, e o acórdão cai para **393º**.

**Medido em escala** (BM25, `fixed_512_256`, acórdão relevante no top-10 do
índice completo):

| Chunk que ganhou o acórdão certo | todos (n = 640) | nas 105 perdas grandes do recorte |
|---|---:|---:|
| rotulado relatório, **contendo a ementa** | 120 | **57 (54%)** |
| relatório puro | 198 | 48 (46%) |
| fundamentação, ementa, dispositivo | 322 | 0 |

**Mais da metade das perdas grandes é esse artefato.** O restante é
relatório puro, um sinal genuíno que discuto no §5.

No `structural_gold`, onde a ementa é sempre um chunk próprio, a ementa é o
trecho que ganha o acórdão certo em **33%** dos acertos (216 de 659). No JUÁ,
cuja consulta é um enunciado, a ementa é evidência de primeira linha, e o
recorte da F6 a jogava fora sem querer.

## 3. A correção: descartar só o que é 100% relatório

`--secoes-criterio toca` mantém um chunk se **qualquer** trecho dele for de uma
seção mantida. Para as estratégias estruturais nada muda (o rótulo define o
chunk). Nas fixas e na recursiva, os chunks de fronteira ficam: são ~26 mil a
mais no `fixed_512_256` (279.974 contra 254.234), cerca de 3% do índice
completo.

### O teste causal (a correção resolve?)

| Estratégia | Coleção | completo | maioria (F6) | **toca** | toca × maioria |
|---|---|---:|---:|---:|---:|
| fixed_512_256 | JUÁ (teste) | 0,2497 | 0,2182 (−12,6%) | **0,2634 (+5,5%, p = 0,012)** | +20,7%, p = 10⁻¹⁹ |
| fixed_1024_512 | JUÁ (teste) | 0,2407 | 0,1920 (−20,2%) | **0,2550 (+6,0%, p = 0,006)** | +32,8%, p = 10⁻²⁶ |
| recursive_default | JUÁ (teste) | 0,2437 | 0,1917 (−21,3%) | **0,2547 (+4,5%, p = 0,032)** | +32,9%, p = 10⁻²⁶ |
| fixed_512_256 | JurisTCU | 0,2490 | 0,2893 (+16,2%) | **0,2878 (+15,6%)** | −0,5%, p = 0,60 |
| fixed_1024_512 | JurisTCU | 0,2510 | 0,2791 (+11,2%) | **0,2768 (+10,3%)** | −0,8%, p = 0,45 |
| recursive_default | JurisTCU | 0,2410 | 0,2764 (+14,7%) | **0,2760 (+14,5%)** | −0,2%, p = 0,90 |

**A correção transforma as perdas no JUÁ em ganhos e não custa nada no
JurisTCU** (onde a ementa carrega só 0,4% da relevância, então perdê-la nunca
doeu).

### A confirmação em dados não vistos (H8, pré-registrada)

O critério `toca` foi desenhado olhando o teste do JUÁ, então o resultado
acima é exploratório. A previsão foi registrada no
[pré-registro](00-preregistro.md) (adendo 2, commit `1e017f5`) **antes** de
rodar sobre a amostra de **6.000 consultas do split de treino** do JUÁ, que
nunca tinha entrado em análise nenhuma:

| Hipótese | Previsão | Resultado (n = 6.000) | |
|---|---|---|---|
| H8a: o recorte por `maioria` piora | Δ < 0 | **+8,1%** (IC 95%: +7,1% a +9,1%) | ❌ |
| H8b: o recorte por `toca` melhora | Δ > 0 | **+9,7%** (IC 95%: +8,8% a +10,6%), p < 10⁻⁹⁵ | ✅ |
| H8c: `toca` supera `maioria` | Δ > 0 | **+1,5%** (IC 95%: +1,1% a +1,9%), p < 10⁻¹² | ✅ |

**H8a errou, e o erro é informativo.** O nDCG@10 do BM25 no treino é **0,655**;
no teste, **0,250**. O teste do JUÁ não é uma amostra natural: os autores o
estratificaram pela **dificuldade no BM25** (Pereira et al. 2026, card do
dataset), concentrando consultas que o BM25 erra. O dano do recorte por
maioria mora nessas consultas difíceis. Na distribuição natural, ele ainda
ajuda, só que menos que o `toca`.

### O mecanismo consulta a consulta (`src/mecanismo.py`)

Se o defeito é "a ementa sai junto", o dano deve se concentrar nas consultas
**parecidas com a ementa** do acórdão certo. Medida: fração dos termos da
consulta (sem acento, ≥ 3 letras, sem stopwords) presentes na ementa. Efeito
dos dois recortes por quartil dessa medida (`fixed_512_256`, BM25; IC 95% por
bootstrap; rodada `*_f7_mecanismo`, figura `__mecanismo`):

| Quartil | JUÁ difícil: maioria | JUÁ difícil: toca | JUÁ natural: maioria | JUÁ natural: toca |
|---|---:|---:|---:|---:|
| Q1 (consulta quase sem termos da ementa) | −4,6% | −3,4% | +9,1% | +8,9% |
| Q2 | +0,0% | +0,3% | +10,7% | +10,8% |
| Q3 | +2,3% | +3,5% | +10,4% | +9,7% |
| **Q4 (consulta ≈ ementa)** | **−28,4%** | **+12,5%** | **+2,4%** | **+9,3%** |

**O dano da F6 mora inteiro no quartil em que a consulta repete a ementa**, nas
duas amostras, e o `toca` o conserta exatamente ali. Nos outros três quartis,
os dois critérios são indistinguíveis. É a confirmação do mecanismo no nível
da consulta, independente da contagem de chunks do §2.

## 4. O resultado consolidado

| Recorte "sem relatório", BM25, `fixed_512_256` | JurisTCU (150) | JUÁ natural (6.000) | JUÁ difícil (1.567) |
|---|---:|---:|---:|
| critério da F6 (`maioria`) | +16,2% | +8,1% | **−12,6%** |
| **critério `toca`** | **+15,6%** | **+9,7%** | **+5,5%** |

**O `toca` é o único que ganha nas três amostras.** É ele que deve ir para o
artigo como recomendação; o recorte da F6 tem um modo de falha conhecido.

## 5. O que fica em aberto: o relatório não é sempre ruído

Mesmo com o `toca`, e mesmo no `structural_gold` (sem artefato nenhum), o
relatório puro é o trecho que ganha o acórdão certo em **30%** dos acertos no
JUÁ. Ali, tirar o relatório troca 290 consultas que melhoram por 155 que
pioram, com efeito líquido zero.

A leitura que os dados sustentam:

- **JurisTCU** ("quais acórdãos firmam esta tese?"): o relatório gera
  casamentos que **competem** com os documentos certos. Tirá-lo ajuda muito.
- **JUÁ** ("qual é o acórdão desta tese?"): o relatório **também contém a
  tese** com frequência suficiente para ser a melhor evidência em 30% dos
  acertos. Tirá-lo tira evidência de algumas consultas. *Hipótese, não
  medida:* no TCU, o relatório costuma transcrever a instrução da unidade
  técnica, cuja análise o voto adota; a tese então aparece nos dois lugares.

O valor do relatório depende da tarefa. Por isso a F7 também testa um modelo
que **aprende** quanto confiar em cada seção, em vez de cortar
([04-ranker-aprendido.md](04-ranker-aprendido.md)).

## 6. O que isto muda na pergunta original do TCC

A F5 perguntou se o chunking estrutural é melhor que o fixo, e a resposta foi
"empate". A F7 encontra uma resposta mais precisa:

> **Isoladamente, a estratégia de chunking importa pouco. Mas, quando o
> pipeline seleciona conteúdo por seção, só o chunking que respeita a
> estrutura é seguro:** no corte fixo, a fronteira entre seções é atravessada
> por chunks mistos, e qualquer regra de seleção ou leva lixo, ou joga fora
> conteúdo útil.

O `toca` é a correção para quem não pode segmentar; a estrutura resolve o
problema na origem. A comparação direta entre estratégias, com o poder das
novas coleções, está em [06-pergunta-original.md](06-pergunta-original.md).

## Rodadas

| Rodada | O que é |
|---|---|
| `*_jua_bm25`, `*_jua_bm25_sec_sem_relatorio` | o achado inicial (§1) |
| `*_jua_bm25_sec_sem_relatorio_toca`, `*_bm25_sec_sem_relatorio_toca` | o teste causal (§3) |
| `*_h8_tr_bm25`, `*_h8_tr_bm25_maioria`, `*_h8_tr_bm25_toca` | a confirmação pré-registrada (§3) |
