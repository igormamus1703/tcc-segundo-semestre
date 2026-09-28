# O bug dos empates: por que o mesmo arquivo dava dois números

**Data:** 28/09/2026 · **Autor:** Leonardo Marques
**Arquivos:** `src/analysis.py` (`per_query_scores`),
`tests/test_analysis_determinismo.py`, `tests/dados/empate_*.trec`

---

## Como apareceu

Montei a tabela principal duas vezes — a segunda só para acrescentar uma
condição nova. O recorte "consulta real de log" do **mesmo arquivo TREC**, o
`fixed_512_256__bm25.trec`, deu:

- **0,132231** na primeira tabela
- **0,133556** na segunda

Mesmo arquivo, mesmos qrels, mesmo `n = 50`. E o nDCG@10 global do mesmo run,
na mesma linha da mesma tabela, era **idêntico nas duas** (0,24855276…).

Um número que muda sem que nada tenha mudado é motivo para parar tudo.

## O que era

Não era aleatoriedade, nem índice trocado. Era **empate de score na fronteira
do corte da métrica**.

Na consulta `6`, três documentos empatam em **5,295338** e ocupam as posições
9, 10 e 11 do ranking. Um dos três é relevante, com grau 3:

| posição | score |
|---:|---:|
| 8 | 5,327050 |
| **9** | **5,295338** |
| **10** | **5,295338** ← um destes três é relevante |
| **11** | **5,295338** |
| 12 | 5,252744 |

Para o nDCG@**10**, isso decide tudo: se o relevante fica em 9 ou 10, a
consulta vale 0,066; se é empurrado para 11, vale **0**.

E o ranx não fixa esse desempate. O `Run.sort()` ordena por valor com um sort
instável (numpy usa quicksort acima de um certo tamanho de vetor), e reordenar
o que já estava ordenado **permuta os empatados**. Resultado: o score da
consulta passa a depender de o objeto `Run` já ter sido avaliado antes ou não.

No `src/evaluate.py`, o `main` avalia todos os runs (etapa 1) e só depois
calcula os recortes (etapa 3), sobre os mesmos objetos. O estado da etapa 1
vazava para a etapa 3.

## Por que ninguém tinha percebido

Porque o erro **não aparece na média global**. O score da consulta 6 entra na
soma das 150 dos dois jeitos; a média muda na quinta casa decimal. O
`main_results.csv` — que é a tabela que mais olhamos — nunca denunciou nada.

Ele só aparece nos **recortes**, onde cada consulta vai para um grupo: um score
trocado muda a média de um grupo de 50 em ~1%. E nos ICs por bootstrap, e na
análise de poder, e na escolha do peso da fusão por validação cruzada — tudo o
que consome score **por consulta** em vez da média.

É a definição de erro silencioso: plausível, pequeno, e vai para o artigo.

## A correção

Desempatar por `doc_id`, do nosso lado, antes de entregar ao ranx:

```python
completo = Run(run.to_dict(), name=run.name).make_comparable(qrels)
canonico = Run(
    {qid: dict(sorted(docs.items(), key=lambda kv: (-kv[1], kv[0])))
     for qid, docs in completo.to_dict().items()},
    name=run.name,
)
canonico.sorted = True   # impede o ranx de reordenar e desfazer o desempate
```

Três decisões, e cada uma tem motivo:

1. **Cópia.** `make_comparable` mexe no objeto recebido. Uma função de leitura
   não pode deixar o run do chamador diferente do que era.
2. **Desempate por `doc_id`.** O critério é arbitrário — e é esse o ponto:
   precisa ser arbitrário e **fixo**. Não existe resposta "certa" para qual de
   três documentos igualmente pontuados merece a 9ª posição; existe a
   obrigação de responder sempre a mesma coisa.
3. **`sorted = True`.** Sem isso o ranx reordena e desfaz o desempate.

## A verificação

Antes de confiar na correção, calculei o nDCG@10 da consulta 6 **à mão** —
ganho, log, DCG, IDCG — a partir do arquivo TREC. Deu 0,066254, que é o valor
que aparecia *depois* de `evaluate_runs`. Ou seja: **a primeira tabela era a
errada**, não a segunda, e minha intuição inicial (de que a segunda estava
corrompida) estava invertida.

Isso também derrubou uma hipótese que eu tinha seguido por um tempo — a de que
o problema era desalinhamento entre o vetor de scores e `get_query_ids()`.
Não era; a ordem das chaves é estável. Registro aqui porque a hipótese errada
custou mais tempo que a certa.

Com o desempate fixo, a consulta 6 passa a valer **0,063621** de forma
estável: o documento relevante fica na 10ª posição em vez da 9ª, porque é
assim que o `doc_id` ordena. Nem melhor nem pior que 0,066254 — apenas sempre
o mesmo.

## O teste

`tests/test_analysis_determinismo.py`, sete testes. Quatro deles **falham** com
a implementação anterior — conferido revertendo o arquivo e rodando.

A fixture é **dados reais**, em `tests/dados/empate_*.trec`: as 20 primeiras
posições das consultas 1 e 6 da rodada `20260906-0515_bm25`. Tentei reproduzir
com dados sintéticos e não consegui — com poucos documentos o numpy usa
insertion sort, que é estável, e o bug não aparece. Vinte posições por consulta
é o menor recorte que ainda reproduz.

## O que mudou nos números do trabalho

| O que | Muda? |
|---|---|
| `main_results.csv` (nDCG@10, MRR, MAP, Recall médios) | **Não.** Vem direto do `ranx.evaluate`, que não passa por aqui |
| `significance.csv` (p-valores, vitórias/empates/derrotas) | **Não.** Vem do `ranx.compare` |
| Recortes (tipo de consulta, tamanho de documento, retriever) | **Sim**, na terceira casa decimal |
| IC 95% por bootstrap | **Sim**, na terceira casa |
| Análise de poder | **Sim**, na terceira casa |
| Validação cruzada da fusão (`src/tuning.py`) | **Sim** — a seleção do peso e os p-valores consomem score por consulta |

Todas as tabelas da F6 foram regeradas depois da correção. **Nenhuma conclusão
mudou**, o que era de esperar: o erro valia uma consulta em 150. Mas
"nenhuma conclusão mudou" só é uma frase honesta depois de refazer a conta.

## A lição para o resto do projeto

Empate de score não é caso raro no BM25 — é o comportamento normal quando dois
documentos casam os mesmos termos com as mesmas frequências. Qualquer métrica
com corte (`@k`) é sensível a isso na fronteira.

Vale como limitação a declarar no artigo: **os valores por consulta dependem de
um critério de desempate**, e o nosso é fixado por `doc_id`. Sem essa frase, um
revisor que reimplemente a avaliação vai obter números ligeiramente diferentes
e não vai saber por quê.
