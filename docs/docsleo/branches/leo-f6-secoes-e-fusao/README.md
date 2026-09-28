# Branch `leo/f6-secoes-e-fusao`

**Autor:** Leonardo Marques · **Aberta em:** 2026-09-28 · **Status:** 🟡 em revisão, **não mergeada**

Transforma o achado exploratório da F4/F5 — *descartar o relatório do índice
melhora a recuperação* — em resultado de pipeline, e acrescenta duas
intervenções novas. O trabalho sai de **um resultado nulo com achados em
volta** para **um resultado nulo mais uma receita que melhora o nDCG@10 em
29,3%**, validada contra um controle, sem hiperparâmetro a ajustar na versão
recomendada e com validação cruzada na versão ponderada.

## O resultado, em uma linha

| | nDCG@10 | MRR@10 | MAP@10 | Recall@100 |
|---|---:|---:|---:|---:|
| BM25, índice completo (baseline da F5) | 0,2486 | 0,5186 | 0,0963 | 0,4709 |
| **descartar o relatório + fundir BM25 com o denso** | **0,3215** | **0,6000** | **0,1402** | **0,5479** |
| | **+29,3%** | **+15,7%** | **+45,6%** | **+16,4%** |

`fixed_512_256`, 150 consultas, p < 0,00001 com correção de Bonferroni sobre
28 pares. **Todas as quatro métricas sobem** — não há trade-off a declarar. E a
configuração da linha 2 **não tem hiperparâmetro nenhum**: é a fusão de quatro
rankings com peso igual.

## Comece por aqui

| Se você tem 2 minutos | Leia |
|---|---|
| O resultado que importa | [resultados/04-tabela-principal.md](resultados/04-tabela-principal.md) |
| Por que acreditamos nele | [resultados/02-controle-aleatorio.md](resultados/02-controle-aleatorio.md) — o controle que separa "estrutura" de "índice menor" |
| Por que o número é honesto | [02-metodologia-cv.md](02-metodologia-cv.md) — o peso da fusão não foi escolhido no conjunto de teste; e a melhor configuração nem peso tem |
| O erro que quase passou | [03-empate-de-score.md](03-empate-de-score.md) — o mesmo arquivo dava 0,1322 e 0,1336 |
| Se dá para confiar nos números | [04-auditoria-de-validade.md](04-auditoria-de-validade.md) — dez ameaças testadas, nove descartadas, uma declarada |
| O que **não** funcionou | [resultados/05-negativos.md](resultados/05-negativos.md) |

## Documentos

### Decisões e método
| Doc | Assunto |
|---|---|
| [01-implementacao-f6.md](01-implementacao-f6.md) | Como as três intervenções entraram no pipeline, e as armadilhas |
| [02-metodologia-cv.md](02-metodologia-cv.md) | Validação cruzada por consulta: por que, e o que ela custou |
| [03-empate-de-score.md](03-empate-de-score.md) | ⚠️ O bug dos empates: por que o mesmo arquivo dava dois números, e o que mudou depois da correção |
| [04-auditoria-de-validade.md](04-auditoria-de-validade.md) | ⭐ **Dez ameaças ao resultado, testadas uma a uma** — inclusive a circularidade, e a limitação que fica |

### Resultados
| Doc | Assunto |
|---|---|
| [resultados/01-recorte-por-secao.md](resultados/01-recorte-por-secao.md) | 🏆 Descartar o relatório: **+11% a +17% no BM25**, +12% a +28% no denso, nas cinco estratégias |
| [resultados/02-controle-aleatorio.md](resultados/02-controle-aleatorio.md) | ⭐ O controle pareado: descartar 2/3 **ao acaso piora**; escolhendo o relatório, melhora |
| [resultados/03-fusao-hibrida.md](resultados/03-fusao-hibrida.md) | Fusão BM25 + denso: +4,4% a +8,6% sob CV — e a fusão das 4 condições, **sem hiperparâmetro**, chega a +29,3% |
| [resultados/04-tabela-principal.md](resultados/04-tabela-principal.md) | ⭐ **A tabela do artigo:** as oito condições, com significância e recortes |
| [resultados/05-negativos.md](resultados/05-negativos.md) | Ponderação por seção, RRF sem peso e `sum_top_k` — o que foi testado e descartado |

## Código entregue

| Entrega | Onde |
|---|---|
| Recorte e ponderação por macro-seção, e o controle aleatório pareado | `src/sections.py` |
| Fusão de rankings (RRF e soma normalizada) | `src/fusion.py` |
| Escolha do peso da fusão por validação cruzada | `src/tuning.py` (`validacao_cruzada`) |
| Escolha de **configuração** por CV (qual seção indexar) | `src/tuning.py` (`selecao_por_cv`) |
| Encadeamento de etapas pelo rótulo exato da rodada | `src/experiment.py` (`ultima_rodada`) |
| Cache de embeddings servindo **subconjunto** de chunks | `src/indexing/dense.py` |
| `--secoes`, `--pesos`, `--amostra-igual-a` no orquestrador | `src/run_experiments.py` |
| `--runs`: tabela de comparação a partir de runs avulsos | `src/evaluate.py` |
| Figura de progressão de condições | `src/plots.py` (`fig_condicoes`) |
| Etapa F6 no script de rodada completa | `scripts/rodada_completa.ps1` |

## Testes: 182 passando

Eram **115** antes desta branch. Os 67 novos seguem a mesma regra das fases
anteriores: travar o que **falha em silêncio**.

- **alinhamento embedding × chunk** — o cache agora serve um subconjunto, e a
  linha `i` da matriz tem de continuar sendo o chunk `i` da lista pedida. Fora
  de ordem, a busca devolve o `chunk_id` errado sem levantar nada.
- **cache somente leitura** — indexar um recorte de uma estratégia ainda não
  encodada gravaria um cache parcial por cima do completo, de 10 h de GPU.
- **vazamento na validação cruzada** — um teste espiona quais consultas entram
  na escolha do peso e exige que a dobra de teste nunca apareça. É o bug que
  não quebra nada: só infla o número.
- **colisão de nome de run** — dois runs escolhidos podem ter o mesmo nome de
  arquivo vindo de rodadas diferentes; o segundo apagava o primeiro e a tabela
  saía com uma linha a menos. **Bug real, encontrado em execução.**
- **colapso de condições na figura** — `partes_do_run` agrupava "BM25 completo"
  e "BM25 sem relatório" na mesma barra, e uma das duas sumia do gráfico.
  **Bug real, encontrado ao olhar a figura gerada.**
- **escala na fusão** — somar score de BM25 (dezenas) com cosseno (0,x) sem
  normalizar produz uma "fusão" que é o BM25 com passos extras.
- **empate de score na fronteira da métrica** — o mesmo arquivo TREC dava dois
  valores no mesmo recorte, conforme a ordem das chamadas. **Bug real,
  encontrado em execução**, e o mais sério dos três: ver
  [03-empate-de-score.md](03-empate-de-score.md). A fixture do teste são dados
  reais (`tests/dados/empate_*.trec`) — sinteticamente não reproduz.

Três bugs reais foram achados **em execução, não por leitura**: a colisão de
nomes no `--runs`, o colapso de condições nas figuras e o empate de score. Os
três produziam
resultados plausíveis à vista e errados — exatamente o tipo que o
[README da raiz](../../../../README.md#fluxo-de-trabalho-obrigatório) manda
priorizar.

## Rodadas que sustentam os números

Todas em `results/experiments/`, com manifesto, log e figuras.

| Rodada | O que é |
|---|---|
| `20260928-1638_bm25_sec_sem_relatorio` | BM25, 5 estratégias, sem o relatório |
| `20260928-1650_dense_sec_sem_relatorio` | Denso, 5 estratégias, sem o relatório |
| `20260928-1652_bm25_controle_amostra` | **Controle:** mesmo tamanho de índice, sorteado |
| `20260928-1751_cv_fusao_bm25_denso` | Fusão com peso por CV, índice completo |
| `20260928-1758_cv_fusao_sec_sem_relatorio` | Fusão com peso por CV, sem o relatório |
| `20260928-1728_fusao4_peso_igual` | 🏆 Fusão das 4 condições com peso igual — **sem hiperparâmetro** |
| `20260928-1822_f6_tabela_principal` | ⭐ A tabela do artigo: 8 condições |
| `20260928-1707_bm25_sec_sumtopk` | Sensibilidade da agregação (`sum_top_k`) |
| `20260928-1635_fusao_rrf-k60` | RRF sem peso — **negativo**, mantido como registro |
| `20260928-1657_dense_peso_rel0.2` / `-1658_…0.5` / `-1701_sanidade_peso098` | Ponderação — **negativo** |
| `20260928-18xx_aud_sec_*` (8 rodadas) | **Auditoria:** dose-resposta em 10 recortes de seção |
| `20260928-19xx_aud_controle_seed*` (2 rodadas) | **Auditoria:** o controle com outras duas sementes |

## Checklist para o merge

- [x] `pytest` verde (182)
- [x] Recorte por seção reimplementado em `src/`, com testes
- [x] Rodado no **BM25** — era o buraco do achado exploratório
- [x] Rodado nas **cinco** estratégias, não só nas estruturais
- [x] Variante **ponderada** testada (negativa, documentada)
- [x] **Controle pareado** por amostra aleatória
- [x] Efeito **por tipo de consulta**, inclusive nas consultas reais de log
- [x] IC 95% por bootstrap e análise de poder
- [x] Hiperparâmetro da fusão por **validação cruzada**
- [x] Sensibilidade da agregação (`sum_top_k`) — item aberto desde a F5
- [x] Figuras regeneradas por `src.plots`, com rodapé de contexto
- [x] Bug dos empates corrigido e **todas as tabelas regeradas** depois dele
- [x] **Auditoria de validade**: dose-resposta em 10 recortes, nDCG reimplementado
      do zero, controle em 3 sementes, e a escolha da seção validada por CV
      ([04-auditoria-de-validade.md](04-auditoria-de-validade.md))
- [ ] **Revisão da equipe** — ver "Pontos de atenção"
- [ ] Merge na `main` — **aguardando aprovação**

## Pontos de atenção para quem revisar

1. **Isto muda a tese do artigo.** A pergunta deixa de ser só *"como cortar o
   documento?"* (resposta: tanto faz) e passa a ter uma segunda metade com
   resposta: *"qual parte indexar?"* — a fundamentação; o relatório atrapalha.
   A Introdução, os Resultados e a Conclusão precisam ser reescritos.
2. **O resultado nulo original não foi derrubado, foi reforçado.** Sob o
   recorte, as cinco estratégias continuam sem se separar (menor p = 0,056).
   Agora sabemos que o empate vale em dois pontos de operação diferentes.
3. **`fixed_512_256` passa a liderar.** No índice completo ela era a 4ª no
   BM25; sem o relatório é a 1ª nos dois retrievers. A diferença continua não
   significativa, mas a inversão merece uma frase na Discussão.
4. **O trade-off de recall existe no denso e não no BM25.** No BM25 o
   Recall@100 *sobe* (+1,8% a +6,0%); no denso *cai* (−4,1% a −10,5%). A
   limitação declarada no achado exploratório era do denso, e não é geral.
5. **Nada foi alterado nas fases do Igor** (`ingest.py`, `segmenter/`,
   `chunkers/`). O recorte por seção lê os spans que a ingestão já grava.
6. **A decisão de corpus continua aberta** (12.880 × 113.827). Todos os
   números desta branch são do corpus de 12.880, como os da F5.
7. **Uma correção afeta números da F5.** O bug dos empates
   ([03-empate-de-score.md](03-empate-de-score.md)) mexe nos recortes, nos IC
   95% e na análise de poder de **todas** as rodadas, inclusive as antigas.
   As tabelas da F5 em `results/experiments/2026090*` ainda não foram
   regeradas: nenhuma conclusão muda (o efeito é de terceira casa), mas quem
   for citar um número de recorte da F5 no artigo deve regerar a tabela antes.
