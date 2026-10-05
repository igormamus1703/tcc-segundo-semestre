# Branch `leo/f7-evolucao`

**Autor:** Leonardo Marques · **Aberta em:** 2026-10-05 · **Status:** 🟡 em validação, **não mergeada** (o merge depende de aprovação)

A F6 terminou com um ganho grande (+29% de nDCG@10), medido em **150
consultas**, com a decisão principal ("tire o relatório") tomada olhando o
mesmo benchmark. A F7 submete esse resultado ao teste mais duro disponível
(**uma segunda coleção, 10× maior, sobre os mesmos acórdãos**) e, a partir do
que deu errado, constrói três coisas novas: uma correção do método, um modelo
que aprende o peso de cada seção, e um reranker ajustado ao domínio.

Tudo foi pré-registrado antes de rodar ([00-preregistro.md](00-preregistro.md)),
inclusive as previsões que erraram.

## O resultado, em cinco linhas

1. **O recorte da F6 não replica como estava.** No JUÁ-Juris (1.567 consultas
   difíceis), ele piora as estratégias fixas e a recursiva em 13% a 21%.
2. **A causa é um artefato de fronteira, e foi corrigida.** O chunk 0 junta a
   ementa com o relatório e sai junto. O critério `toca` (descartar só chunks
   100% relatório) **não perde em nenhuma amostra** e ganha com significância em duas: +15,6% no
   JurisTCU, +9,7% em 6.000 consultas naturais (hipótese pré-registrada,
   p < 10⁻⁹⁵) e +5,5% nas difíceis.
3. **Chunking estrutural importa quando se seleciona conteúdo.** Isolada, a
   estratégia de corte pouco importa; com seleção por seção, só o corte que
   respeita a fronteira é seguro. É a resposta nova para a pergunta original.
4. **Um ranker aprendido redescobre a regra sozinho.** Treinado no JUÁ, ele
   transfere para o JurisTCU (+18,6% sobre o BM25) e mostra, via SHAP, que **o
   mesmo casamento vale ~5× menos no relatório que na fundamentação**.
5. **O valor do relatório depende da tarefa.** Ele atrapalha quem busca os
   acórdãos *de uma tese* (JurisTCU) e ajuda em parte de quem busca *o*
   acórdão de um enunciado (JUÁ), inclusive dentro de um reranker neural.

## Comece por aqui

| Se você tem 2 minutos | Leia |
|---|---|
| O achado principal | [03-fronteira-e-criterio-toca.md](03-fronteira-e-criterio-toca.md) |
| O modelo que aprende os pesos | [04-ranker-aprendido.md](04-ranker-aprendido.md) |
| O que foi previsto antes, e o que errou | [00-preregistro.md](00-preregistro.md) e o placar em [02-replicacao.md](02-replicacao.md) |
| Tudo numa figura | o painel `results/experiments/*_f7_painel/figuras/*__painel.png` (também em [`docs/apresentacao/f7.html`](../../../apresentacao/f7.html)) |

## Documentos

| Doc | Assunto |
|---|---|
| [00-preregistro.md](00-preregistro.md) | 🔒 Hipóteses H1–H7, critério de merge, e os adendos (H8) |
| [01-colecao-jua.md](01-colecao-jua.md) | Como o JUÁ-Juris virou uma segunda coleção sobre os mesmos acórdãos |
| [02-replicacao.md](02-replicacao.md) | As hipóteses, uma a uma, em quatro amostras de consultas |
| [03-fronteira-e-criterio-toca.md](03-fronteira-e-criterio-toca.md) | ⭐ O defeito do recorte, o mecanismo, a correção e a confirmação |
| [04-ranker-aprendido.md](04-ranker-aprendido.md) | ⭐ LambdaRank com sinais por seção, ablação e SHAP |
| [05-reranker.md](05-reranker.md) | Cross-encoder zero-shot e ajustado com LoRA |
| [06-pergunta-original.md](06-pergunta-original.md) | A comparação entre estratégias de chunking, com poder e teste de equivalência, e a ablação da ementa |
| [07-texto-para-o-artigo.md](07-texto-para-o-artigo.md) | ✍️ Rascunho de resumo, contribuições, resultados, discussão e limitações |

## Código entregue

| Entrega | Onde |
|---|---|
| JUÁ-Juris → acórdãos do corpus, com a seção da resposta | `src/jua.py` |
| Critério `toca` do recorte (`--secoes-criterio`) | `src/sections.py`, `src/run_experiments.py` |
| Reranker com cross-encoder, três variantes, cache com checkpoint | `src/rerank.py` |
| Fine-tune LoRA do reranker com supervisão de passagem | `src/finetune_reranker.py` |
| Ranker aprendido (LambdaRank) + SHAP | `src/ltr.py` |
| Replicação entre coleções: efeito, IC, estratos, TOST, forest plots | `src/replicacao.py` |
| Painel configuração × coleção | `src/painel.py` |
| Rodada da F7 encadeada | `scripts/rodada_f7.ps1` |
| Especificações versionadas | `configs/f7_*.json` |

**Nada mudou em `ingest.py`, `segmenter/` ou `chunkers/`.** A única mudança
em código existente é o parâmetro `criterio` em `sections.filtrar`, cujo padrão
(`maioria`) reproduz a F6 byte a byte.

## Testes

**221 passando** (eram 191 na F6). Os 30 novos travam o que falha em silêncio:

- **offset do excerto** no texto dobrado × texto original (`test_jua.py`);
- **o reranker** não perde documento sem passagem, nem lê relatório na
  variante que o proíbe (`test_rerank.py`);
- **o TOST** não declara equivalência por falta de poder (`test_replicacao.py`);
- **o LTR** não mistura consulta entre treino e validação, e corta o sinal
  **antes** de normalizar: o bug real da v1 (`test_ltr.py`);
- **o critério `toca`** mantém o chunk misto ementa+relatório e respeita o
  rótulo das estruturais (`test_sections.py`);
- **o fine-tune** nunca usa um trecho do acórdão relevante como negativo
  (`test_finetune_reranker.py`).

## Bugs e erros encontrados no caminho

1. **LTR v1: normalização desalinhada** entre treino (top-200) e teste
   (top-1.000). Sintoma: o modelo "sem seções" 29% abaixo do próprio BM25.
   Corrigido e travado por teste ([04](04-ranker-aprendido.md)).
2. **Previsão errada (H8a):** eu previ que o recorte da F6 pioraria também nas
   consultas naturais do JUÁ; ele melhora 8%. O dano estava concentrado no
   teste do JUÁ, estratificado por dificuldade. Registrado como errado.
3. **Uma fila de LTR montada sobre `fixed_512_256`** foi descartada no meio,
   quando o artefato da ementa mostrou que os sinais "só a seção X" dessa
   estratégia estavam contaminados. Refeita sobre `structural_gold`.

## Pontos de atenção para quem revisar

1. **A recomendação do artigo muda:** de "tire o relatório" para "tire só os
   chunks 100% relatório (`toca`), ou use chunking estrutural".
2. **A tabela principal da F6 continua válida no JurisTCU**, mas a manchete de
   +29% precisa da ressalva de que a mesma receita perde 12% nas consultas
   difíceis do JUÁ. A versão com `toca` empata com ela no JurisTCU (0,3225 ×
   0,3215) e não tem esse modo de falha.
3. **O JUÁ-Juris mede outra tarefa** (*known-item*: achar o acórdão de um
   enunciado). As duas coleções juntas são mais fortes que qualquer uma
   sozinha, mas não são intercambiáveis ([01](01-colecao-jua.md)).
4. **As consultas reais de log continuam sem poder** (n = 50): nenhuma
   configuração é significativa nelas, embora todas melhorem na direção certa.
