# Replicação: cada hipótese pré-registrada, e o que aconteceu com ela

**Data:** 05/10/2026 · **Autor:** Leonardo Marques
**Código:** `src/replicacao.py` · **Especificação:** `configs/f7_replicacao_final.json`
**Rodada:** `results/experiments/*_f7_replicacao_final` (tabelas `replicacao.csv`, `estratos.csv`, `equivalencia.csv`; figuras `forest_*`, `estratos`, `equivalencia_*`)

> Este documento julga as hipóteses **como foram escritas** no
> [pré-registro](00-preregistro.md), inclusive as que erraram. A coleção de
> julgamento das H1–H7 é o **teste do JUÁ-Juris** (1.567 consultas, "JUÁ
> difícil"); a das H8, a amostra de **treino** (6.000, "JUÁ natural").

---

## Placar

| # | Hipótese (resumo) | Veredicto | Evidência |
|---|---|---|---|
| H1 | O recorte "sem relatório" (critério da F6) melhora as 5 estratégias no JUÁ | ❌ **não replicou** | piora 3 de 5: −12,6% a −21,3% nas fixas e recursiva; ≈ 0 nas estruturais |
| H2 | O controle aleatório do mesmo tamanho piora | ✅ | −31% no `fixed_512_256` (0,1715 × 0,2497) |
| H3 | Fusão das 4 > BM25; fusão recortada > BM25 recortado | ❌ | no JUÁ, a fusão com o denso **piora** (−11%): o denso é 35% a 55% pior que o BM25 ali |
| H4 | O recorte piora quando a resposta está no relatório e ajuda quando está na fundamentação | ❌ (F6) · direção ✅ (`toca`) | a F6 piora até com a resposta na fundamentação (−15%); o `toca` dá +7% e −12% (este n.s.) |
| H5 | As 5 estratégias são praticamente equivalentes (TOST, ±0,01) | ❌ **e isso é a notícia** | o estrutural **vence** os não estruturais por 0,018 a 0,029; só ouro × predito é equivalente |
| H6 | O reranker sobre a melhor configuração melhora nas duas coleções | ❌ (zero-shot) | −15,9% no JurisTCU; +8% sobre a fusão no JUÁ, mas abaixo do BM25 |
| H7 | O reranker lendo só fora do relatório ≥ lendo tudo | ✅ JurisTCU · ❌ JUÁ | +17,9% no JurisTCU; −6,7% no JUÁ |
| H8a | (adendo 2) O recorte da F6 piora no JUÁ natural | ❌ | **+8,1%** (IC +7,1% a +9,1%) |
| H8b | (adendo 2) O recorte `toca` melhora no JUÁ natural | ✅ | **+9,7%** (IC +8,8% a +10,6%), p < 10⁻⁹⁵ |
| H8c | (adendo 2) `toca` > critério da F6 no JUÁ natural | ✅ | +1,5% (IC +1,1% a +1,9%), p < 10⁻¹² |

**Critério de merge** (escrito antes): (a) H1 e H2, (b) H5 confirmando
equivalência, ou (c) H6 com ≥ 5% nas duas coleções. **Pela letra, nenhum foi
atingido** até a avaliação do reranker ajustado (ver [05](05-reranker.md)). O
que a F7 tem de mais forte (H8b, a resposta à pergunta original e o ranker
aprendido) veio fora desse critério; está declarado assim no
[README](README.md) e no `RESULTADOS-F7.md`.

## Por que as previsões erraram (e o que isso ensinou)

**H1 e H3 erraram pelo mesmo motivo de fundo: a tarefa do JUÁ é diferente.**
No JUÁ, a consulta é uma tese em uma frase e o relevante é *um* acórdão. Duas
coisas mudam em relação ao JurisTCU:

1. **A ementa vira evidência de primeira linha**, e o recorte da F6 a jogava
   fora nas estratégias fixas (artefato de fronteira, [03](03-fronteira-e-criterio-toca.md)).
2. **O denso é muito mais fraco** (0,16 contra 0,25 do BM25), e a fusão de
   peso igual puxa o BM25 para baixo. É o mesmo motivo pelo qual o RRF sem
   peso falhou na F6.

**H5 errou na direção boa.** Eu previ equivalência porque era o que 150
consultas mostravam. Com 1.567, o efeito que estava abaixo da resolução
apareceu: **o corte estrutural vence**, e a ablação da ementa mostra o porquê
([06](06-pergunta-original.md)).

**H8a errou e corrigiu uma ideia minha.** Eu achei que o dano do recorte da F6
seria geral no JUÁ. Ele é concentrado nas consultas difíceis (o teste do JUÁ
foi estratificado por dificuldade no BM25) e, dentro delas, no quartil em que
a consulta repete a ementa ([03](03-fronteira-e-criterio-toca.md), mecanismo).

## H4: onde mora a resposta

JUÁ difícil, `fixed_512_256`, BM25, Δ contra o índice completo
(`estratos.csv`, figura `__estratos`):

| Seção onde está o excerto | n | recorte da F6 | recorte `toca` |
|---|---:|---:|---:|
| fundamentação | 938 | **−15%** (IC < 0) | **+7%** (IC > 0) |
| dispositivo | 198 | −2% | +11% (IC inclui 0) |
| relatório | 148 | **−26%** (IC < 0) | −12% (IC inclui 0) |
| não localizado | 275 | −2% | +5% |

**Veredicto: ❌ para o recorte da F6, que é o que a hipótese descrevia.** Ele
piora inclusive quando a resposta está na fundamentação, porque o artefato da
ementa ([03](03-fronteira-e-criterio-toca.md)) atinge todas as consultas
parecidas com a ementa, independentemente de onde está o excerto. **Com o
`toca`, os sinais saem como a H4 previa** (ganho onde a resposta está na
fundamentação, perda onde está no relatório), mas o estrato do relatório,
com 148 consultas, não tem poder para significância. Leitura honesta: o
mecanismo "tirar o relatório tira as respostas que moram nele" existe na
direção prevista e é pequeno perto do artefato da ementa.

## Sensibilidade: a coleção independente

Sem as 194 consultas cujo acórdão é relevante no JurisTCU (1.373 restantes),
**todos os efeitos se mantêm**, com magnitudes quase idênticas:

| Comparação | JUÁ difícil (1.567) | JUÁ independente (1.373) |
|---|---:|---:|
| recorte da F6 × completo | −12,6% | −15,0% |
| controle aleatório × completo | −31,3% | −32,8% |
| `toca` × completo | +5,5% | +5,3% |
| `toca` × recorte da F6 | +20,7% | +23,8% |
| estrutural (ouro) × fixo 512/256 | +8,1% | +8,2% |
| fusão das 4 (F6) × BM25 | −11,3% | −12,4% |
| LTR com seções × fusão das 4 (mesma estratégia) | +11,1% | +11,3% |

A sobreposição com o JurisTCU não explica nada do que a F7 encontrou.

## A correção de Bonferroni muda duas leituras

Com 23 comparações por coleção:

- **`toca` × completo no JUÁ difícil:** p = 0,012 sem correção, **0,24 com
  ela**. O `toca` não perde em nenhuma amostra e ganha com significância
  corrigida no JurisTCU e no JUÁ natural; no JUÁ difícil, o que é
  significativo mesmo corrigido é a diferença para o critério da F6 (+20,7%,
  p < 10⁻¹⁷).
- **Controle aleatório × completo no JurisTCU:** −9,4%, p = 0,57 corrigido
  (na F6, com 28 pares, era 0,028). No JUÁ, com 10× mais consultas, o
  controle é −31% (p < 10⁻²²). A conclusão da F6 ("não é o tamanho do índice")
  fica mais forte, não mais fraca.

## As figuras

| Figura | O que mostra |
|---|---|
| `__forest_recorte` | o recorte da F6, o `toca`, o controle e o recorte estrutural, nas quatro amostras |
| `__forest_fusao` | as fusões da F6 e as corrigidas |
| `__forest_reranker` | reranker zero-shot e ajustado, e as variantes de leitura |
| `__forest_ltr` | o ranker aprendido contra o BM25 e contra a fusão |
| `__estratos` | o efeito por seção da resposta (JUÁ difícil) |
| `__equivalencia_completo`, `__equivalencia_toca` | o TOST entre as estratégias, nas quatro amostras |

Marcador cheio = p < 0,05 com Bonferroni **dentro da coleção** (23 comparações).
