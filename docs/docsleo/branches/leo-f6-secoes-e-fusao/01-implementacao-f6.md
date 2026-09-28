# Implementação da F6: decisões e armadilhas

**Data:** 28/09/2026 · **Autor:** Leonardo Marques

Três módulos novos (`sections.py`, `fusion.py`, `tuning.py`) e mudanças em
quatro existentes. O que está aqui são as decisões que não se leem no código e
as armadilhas que custaram tempo.

---

## 1. O cache de embeddings passou a servir um subconjunto

**O problema.** `DenseIndex._load_cache` só reaproveitava o cache quando a
lista de `chunk_ids` era **idêntica** à cacheada. Indexar só três das quatro
seções muda a lista, o cache era rejeitado, e a rodada dispararia um reencode
de ~10 h de GPU para jogar dois terços fora.

**A solução.** Quando os ids pedidos são um **subconjunto** dos cacheados,
selecionamos as linhas pelo id, na ordem de `self.chunk_ids` — que é a ordem
que a busca usa para traduzir índice do FAISS de volta em `chunk_id`.

```python
posicao = {cid: i for i, cid in enumerate(cached_ids)}
linhas = [posicao[cid] for cid in self.chunk_ids]
emb = np.load(emb_path, mmap_mode="r")
recorte = np.asarray(emb[linhas], dtype="float32")
```

O `mmap_mode="r"` importa: filtrar 95 mil linhas de um `.npy` de 3,7 GB traria
os 3,7 GB para a RAM sem ele. Com ele, só as linhas pedidas são materializadas.

**O resultado prático:** a rodada densa das cinco estratégias com recorte levou
**4 minutos**. Sem isso, seriam ~10 h.

**A armadilha que quase entrou junto.** Se o cache completo ainda não existir e
alguém rodar com `--secoes`, o caminho normal encodaria o recorte e o gravaria
como o cache da estratégia — um `.npy` com um terço dos chunks ocupando o lugar
do encode completo. Daí o parâmetro `cache_somente_leitura`, ligado sempre que
há recorte ou amostra: sem cache, encoda em memória e **não grava**.
Teste: `test_cache_somente_leitura_nao_grava_recorte_por_cima_do_completo`.

**O risco silencioso principal é a ordem.** Se as linhas saíssem fora de ordem,
a busca devolveria o `chunk_id` errado para cada resultado e nada levantaria
exceção — o nDCG só sairia menor. Travado por
`test_subconjunto_do_cache_sai_na_ordem_dos_chunks_pedidos`, que pede o
subconjunto **invertido** e compara com o encode direto.

## 2. A seção de um chunk: rótulo primeiro, offset depois

`Chunk.section` é `None` em `fixed` e `recursive`. Para o recorte valer nas
cinco estratégias, a seção é resolvida assim:

1. se o chunk tem rótulo, usa o rótulo;
2. senão, a seção com maior sobreposição de caracteres com o offset
   `(start, end)` do chunk — reusando `analysis.section_of_span`, que a F5 já
   usava para o recorte analítico.

**Por que o rótulo tem precedência.** Nas estruturais, o rótulo *é* a definição
do chunk — ele foi criado a partir daquele span. Resolver pelo offset daria o
mesmo resultado no caso normal e um resultado pior na borda: um chunk
estrutural que encoste no span vizinho por um caractere seria reatribuído.

**Chunk sem seção resolvível é descartado** quando há filtro ativo. Escolha
conservadora: mantê-lo faria o índice "sem relatório" conter trechos de
relatório de documentos cujo span falhou, e o efeito medido seria **menor** que
o real, por contaminação — um erro na direção do falso negativo, não do falso
positivo. Na ponderação é o contrário: o indefinido fica, com peso 1,0, porque
ali o conservador é deixá-lo competir sem desconto.

## 3. O nome do run carrega toda variante que muda o número

`{estrategia}__{retriever}[__{agregacao}][__sec-…][__peso-…][__amostra-…]`

Sem isso, dois runs da mesma estratégia e retriever com recortes diferentes
gravariam no mesmo arquivo e o segundo apagaria o primeiro sem aviso — o mesmo
motivo pelo qual o modelo denso já estava no nome desde a F4.

E o `evaluate.parse_run_name` passou a ler as variantes **por prefixo, não por
posição**: com `--aggregation` e `--secoes` juntos, o recorte fica na 4ª
posição, e ler por posição colocaria `sec-sem_relatorio` na coluna `agregacao`.
A tabela do artigo pivota por essas colunas.

## 4. `--secoes=-relatorio` não funciona solto (e a saída)

A forma natural de escrever "descarte o relatório" é `--secoes -relatorio`. O
argparse lê `-relatorio` como uma opção e aborta com "expected one argument".
Funciona colado (`--secoes=-relatorio`), mas isso é uma pegadinha que custa dez
minutos numa rodada de madrugada. Por isso `parse_secoes` aceita também
`sem:relatorio`, que não começa com hífen e passa em qualquer shell.

Descoberto na prática: a primeira rodada da branch morreu exatamente assim.

## 5. `--amostra-igual-a`: o controle tinha de ser pareado por construção

A fração equivalente ao recorte varia por estratégia — 28,0% na
`fixed_512_256`, 33,7% na `structural_pred`. Um `--amostra 0.3` fixo daria um
controle desalinhado justamente onde a comparação precisa ser exata.

`--amostra-igual-a sem:relatorio` calcula, em cada estratégia, quantos chunks o
recorte deixaria, e sorteia esse número. Um comando, uma rodada, contagens
idênticas às do recorte — conferidas no log.

## 6. Dois bugs encontrados em execução

Nenhum dos dois levantava exceção. Os dois produziam resultado plausível e
errado.

**a) Colisão de nome no `--runs`.** A tabela principal inclui dois runs
chamados `fixed_512_256__cv-soma_norm.trec`, de rodadas diferentes (fusão sobre
índice completo e sobre índice recortado). Copiei os dois pelo nome; o segundo
apagou o primeiro, e a tabela saiu com **6 linhas em vez de 7**. Percebi porque
o log diz "7 runs copiados" e a avaliação diz "6 runs". Corrigido prefixando
com a rodada **só quem colide**, para os nomes comuns continuarem legíveis.

**b) Colapso de condições nas figuras.** `plots.partes_do_run` agrupava por
`(estrategia, retriever)`, então "BM25 índice completo" e "BM25 sem relatório"
caíam na mesma barra e uma das duas sumia do gráfico. A figura não ficava
incompleta — ficava **errada**, mostrando um valor e omitindo o outro. Percebi
olhando a figura gerada, que tinha 3 barras para 7 condições. Agora a segunda
componente é a *condição experimental*, com as variantes da F6 incluídas.
Travado por `tests/test_plots.py`.

Um teste antigo (`test_rotulo_da_figura_ignora_o_prefixo_de_rodada`) afirmava
que a agregação era descartada do rótulo — ou seja, travava o comportamento que
causava o colapso. Foi atualizado com a justificativa no próprio teste.

## 7. Figura nova: `fig_condicoes`

A `fig_principal` agrupa por estratégia e dá uma barra vertical por condição:
ótima para 5 estratégias × 2 retrievers, ilegível para 1 estratégia × 7
condições, que é o formato da tabela principal da F6. A `fig_condicoes` põe uma
condição por linha, com a variação percentual contra uma referência explícita
(`--referencia`) ao lado de cada barra — sem referência, o pior run vira
baseline e o ganho sai exagerado.

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `src/sections.py` | **novo** — recorte, ponderação, controle aleatório |
| `src/fusion.py` | **novo** — RRF e soma normalizada, sobre runs TREC |
| `src/tuning.py` | **novo** — validação cruzada do peso da fusão |
| `src/indexing/dense.py` | cache por subconjunto + `cache_somente_leitura` |
| `src/run_experiments.py` | `--secoes`, `--pesos`, `--amostra`, `--amostra-igual-a` |
| `src/evaluate.py` | `parse_run_name` por prefixo; `--runs` para tabela de comparação |
| `src/plots.py` | condição no agrupamento; `fig_condicoes`; `--referencia` |
| `tests/` | +60 testes (115 → 175) |

**Nada foi alterado em `ingest.py`, `segmenter/` ou `chunkers/`** — as fases do
Igor ficaram intactas. O recorte lê os `gold_spans` que a ingestão já grava.
