# Implementação da F4 (indexação e runs) e F5 (avaliação)

**Data:** 2026-09-05 · **Autor:** Leonardo Marques · **Branch:** `leo/f4-indexacao-e-docs`

## O que estava faltando

Antes desta sessão, F4 e F5 eram stubs com `NotImplementedError`:
`indexing/lexical.py`, `indexing/dense.py`, `evaluate.py`, `analysis.py`; e o
`run_experiments.py` sequer existia. Só `retrieval.py` (a agregação chunk→doc)
estava pronto.

## O que foi implementado

| Arquivo | O que faz |
|---|---|
| `src/indexing/text_norm.py` | **novo** — normalização PT compartilhada por indexação e busca |
| `src/indexing/lexical.py` | BM25 via `bm25s`, com busca em lote |
| `src/indexing/dense.py` | `SentenceTransformer` + FAISS `IndexFlatIP`, com cache `.npy` |
| `src/run_experiments.py` | **novo** — orquestra estratégia × retriever → TREC runs |
| `src/evaluate.py` | métricas via `ranx`, significância pareada e o CLI das tabelas |
| `src/analysis.py` | bootstrap IC 95% + os três recortes analíticos |
| `configs/models.yaml` | resolvido o `PREENCHER`; prefixos declarados por modelo |
| `tests/test_indexing.py`, `test_evaluate.py`, `test_run_experiments.py` | **novos** — 42 testes |

Total: `pytest` passou de 39 para **110 testes**, todos verdes. (Este documento
descreve a implementação inicial; o que veio depois — checkpoint do encode,
orçamento de tempo, rastreabilidade das rodadas e figuras — está no
[09-diario-execucao.md](09-diario-execucao.md) e nos documentos de resultados.)

## Decisões de projeto (e por quê)

### 1. Normalização isolada num módulo próprio

A mesma função normaliza os chunks na indexação e as consultas na busca. Se as
duas divergirem, o BM25 não encontra os termos — e **o erro é silencioso**:
nada quebra, o recall só cai. Isolar num módulo com teste dedicado
(`test_bm25_casa_consulta_acentuada_com_texto_sem_acento`) trava esse
acoplamento.

**Remoção de acentos é decisão de conteúdo, não de estilo:** 20 anos de
publicação do TCU trazem "acórdão" e "acordao" no mesmo acervo. Sem normalizar,
viram dois termos distintos no índice.

**Stopwords embutidas** em vez de `nltk`: evita uma dependência nova e um
download em runtime para uma lista de ~200 palavras que não muda.

### 2. Números preservados na tokenização

Em acórdão, "9.1" (item do dispositivo) e o ano do processo carregam sinal de
busca. Descartá-los como "ruído" perderia recall em consultas por referência.

### 3. `IndexFlatIP` + embeddings normalizados

Com vetores normalizados, o produto interno **é** o cosseno e a busca é
**exata**. Um índice aproximado (HNSW/IVF) introduziria erro de recall que
teríamos de justificar na banca, sem nenhum ganho nesta escala.

### 4. Cache de embeddings invalida pelo conjunto de `chunk_id`

O cache só é reaproveitado se a lista de `chunk_id` bater **exatamente**. Se
aceitasse um cache "parecido", o embedding da posição *i* deixaria de
corresponder ao chunk da posição *i* e os resultados sairiam errados **sem
nenhum erro visível**. Coberto nos dois sentidos
(`test_dense_cache_evita_reencode`, `test_dense_cache_invalida_se_chunks_mudarem`).

### 5. Busca funda em chunks antes de agregar (`top_chunks=2000`)

O índice é de chunks, mas os qrels são de documentos. Um acórdão longo espalha
seus chunks pelo ranking; truncar cedo perderia o documento inteiro na
agregação. Fluxo: 2.000 chunks → agrega → top-1.000 documentos.

### 6. O recorte por tamanho de documento usa o qrel, não o run

O tercil de cada consulta vem da mediana do tamanho dos seus documentos
**relevantes** (do qrel), não dos recuperados. Se viesse dos recuperados, cada
estratégia seria avaliada sobre um subconjunto **diferente** de consultas, e as
colunas da tabela deixariam de ser comparáveis entre si.

## Três armadilhas de biblioteca encontradas

Todas do tipo que só aparece rodando. Valem menção na Discussão como custo real
de reprodutibilidade — o mesmo espírito do bug de offset que o Igor achou no
`RecursiveCharacterTextSplitter` na F3.

**1. `ranx.evaluate` aborta se o run não cobrir todas as consultas do qrel.**

```
AssertionError: Qrels and Run query ids do not match.
```

Acontece **de verdade** sempre que uma consulta não recupera nenhum documento.
Resolvido com `make_comparable=True`, que trata a consulta ausente como score 0
— a leitura correta (não recuperar nada é falhar, não é "não se aplica").

⚠️ **Sutileza perigosa:** `make_comparable=True` **altera o `Run` in-place**,
preenchendo as consultas faltantes. Logo, `run.get_query_ids()` só fica
alinhado com o vetor de scores **depois** da chamada a `evaluate`. Ler os ids
antes produz um pareamento consulta↔score errado, silenciosamente. Está
comentado no código e coberto por
`test_per_query_scores_alinha_score_com_a_consulta_certa`.

**2. A estrutura de `Report.comparisons` não é a que a documentação sugere.**
É um `FrozensetDict` indexado por `frozenset({a, b})`, não um dicionário
aninhado `[a][b]`. E o `win_tie_loss` é indexado pela **tupla ordenada**
`(a, b)` — que é o que dá o *sentido* da diferença: o p-valor diz que há
diferença, não diz quem ganhou.

**3. `print(report)` do ranx quebra no Windows.**

```
UnicodeEncodeError: 'charmap' codec can't encode character 'ᵇ'
```

O relatório usa superscritos Unicode que o console cp1252 do Windows não
encoda. Por isso ele é gravado em arquivo (`significance_report.txt`, UTF-8) em
vez de impresso.

## Divergência entre o contrato do plano e o `ingest.py`

O `plano_implementacao.md` §2 especifica o `corpus_docs.jsonl` assim:

```
{"doc_id": str, "text": str, "n_tokens": int, "gold_spans": [...], "ano": int, ...}
```

Mas o `ingest.py` **não grava `n_tokens`**. Os campos reais são
`doc_id, text, gold_spans, ano, colegiado, tipo_processo`. O `corpus_stats()`
até calcula as contagens de token para o EDA — e as **descarta** depois.

Isso quebrou o recorte por tamanho de documento (`KeyError: 'n_tokens'`), que é
um dos três recortes obrigatórios da F5.

**Como resolvi, sem mexer no `ingest.py`:** `load_doc_lengths()` usa o campo
quando ele existe e, quando não existe, conta os tokens e **cacheia** em
`data/interim/doc_lengths.json` (tokenizar 780 MB leva minutos, e o recorte não
muda entre execuções). Assim o pipeline funciona com o corpus atual e continua
correto se o `ingest.py` passar a gravar o campo.

> 📌 **A decidir com o Igor:** o certo a longo prazo é o `ingest.py` gravar
> `n_tokens`, como o plano manda — ele já tem o número em mãos no
> `corpus_stats()`. Não fiz porque exigiria re-rodar o join dos 6 GB, e a
> orientação foi não mexer na estrutura antes de confirmar com ele.

Nota menor, do mesmo tipo: o `ingest.py` chama `tiktoken` diretamente, embora o
plano diga que "todo módulo que precisa contar ou janelar por token importa
[de `src/tokenization.py`], nunca chama tiktoken direto". Hoje é inofensivo
(ambos usam `cl100k_base`), mas é o tipo de duplicação que faz o tokenizer
divergir sem ninguém perceber.

## Correção de significância — ponto forte para a banca

`ranx.compare` aplica correção para comparações múltiplas. Comparar 10 runs
dois a dois são **45 testes**: sem correção, ~2 "diferenças significativas"
apareceriam **só por acaso** a p<0,05. É exatamente o erro que uma banca procura
numa tabela de significância, e a nossa já está protegida — vale dizer isso
explicitamente no artigo.

## Como rodar

```bash
python -m src.chunkers.run --strategy all           # F3 (pré-requisito)
python -m src.run_experiments --strategy all --retriever bm25
python -m src.run_experiments --strategy all --retriever dense
python -m src.evaluate                              # avalia a rodada mais recente
python -m src.plots                                 # gera as figuras dessa rodada
```

Smoke test antes do corpus inteiro:

```bash
python -m src.chunkers.run --strategy all --limit-docs 500
python -m src.run_experiments --strategy all --retriever bm25 --limit-queries 10
```

Artefatos gerados, todos dentro de
`results/experiments/<AAAAMMDD-HHMM>_<rótulo>/`:

- `runs/*.trec` e `runs/*__chunks.jsonl` (o chunk vencedor de cada documento)
- `tables/main_results.csv`, `significance.csv`, `significance_report.txt`,
  `power_analysis.csv` e os quatro recortes (`slices_query_type`,
  `slices_doc_length`, `slices_retriever`, `slices_section`)
- `figuras/<rodada>__*.pdf` e `.png`
- `manifest.json` e `execucao.log`

Cobrem os itens 3, 4 e 5 do "Definition of done" do `plano_implementacao.md`.
A caracterização do corpus (`eda_stats.json`, `segmenter_validation.json`) vive
separada, em `results/corpus/`, porque só muda quando o corpus muda.

## O que ainda falta

- [ ] Rodar sobre o corpus real (dependia do download de 6 GB, concluído hoje).
- [ ] Decidir o corpus oficial ([02-achado-corpus.md](02-achado-corpus.md)) — bloqueia os números finais.
- [ ] Notebooks 01–03, que só consomem `results/`.
