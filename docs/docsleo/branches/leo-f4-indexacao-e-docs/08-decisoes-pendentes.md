# Decisões pendentes e próximos passos

**Última atualização:** 2026-09-06 · **Autor:** Leonardo Marques

Checklist do que **a equipe** precisa decidir (não dá para eu decidir sozinho) e
do que dá para tocar em paralelo. Ordenado por urgência: o que está no topo
bloqueia o resto.

---

## 🔴 1. Qual é o corpus oficial? — BLOQUEIA TODOS OS NÚMEROS

**Situação:** o artigo e o pôster dizem 113.827 documentos; o código produz
12.880. Detalhes e evidência em [02-achado-corpus.md](02-achado-corpus.md).

| Opção | Docs | Custo do encode denso | Consequência |
|---|---|---|---|
| **A (recomendada)** | 12.880 | ~24 h CPU / ~2 h GPU | Corrigir os números do artigo e do pôster |
| B | 113.827 | ~9 dias de CPU | Manter o texto, mas exige GPU e re-rodar tudo |
| C | ~53.000 | ~4 dias de CPU | Meio-termo (12.880 + distratores aleatórios) |

**Por que recomendo A:** o JurisTCU, de onde vêm as 150 consultas e os 2.250
qrels, avalia sobre 16.045 documentos. Um corpus de 12.880 acórdãos íntegros é o
análogo direto — muda **uma variável só** (o documento passa a ser o acórdão
inteiro em vez do enunciado+excerto), que é justamente a contribuição do
trabalho. A opção B mudaria tamanho do documento **e** tamanho da coleção ao
mesmo tempo, e aí não dá para atribuir uma diferença de nDCG@10 ao chunking.

**Contra-argumento a declarar como limitação se ficarmos com A:** a coleção fica
enviesada — todo documento nela já foi selecionado pelo TCU para virar
jurisprudência. A busca é mais fácil do que num acervo completo.

> **Atualização (06/09, com os resultados na mão):** a decisão ficou mais
> urgente, não menos. O trabalho agora tem um resultado **significativo**
> (BM25 > denso, p < 0,01) — e um resultado significativo medido no corpus
> errado é pior do que um resultado nulo, porque vai para o artigo como
> afirmação forte. Enquanto o corpus não for decidido, esse número não deve ser
> publicado.

- [ ] **Decidir com o Igor e o resto do time.**

---

## 🟠 2. Corrigir os números do artigo e do pôster

Depende da decisão 1. A tabela de substituição completa está em
[07-numeros-para-o-artigo.md](07-numeros-para-o-artigo.md). Os principais:

- [ ] 113.827 → **12.880** documentos (§Materials, Tabela I, Fig. 2, pôster)
- [ ] mediana 7.347 → **11.426** tokens/doc (p90 38.390, p99 105.313)
- [ ] match 97,9% → **98,7%**; qrels 99,2% → **99,69%**
- [ ] segmentador 92,7% → **92,2%**; fallback 1,6% → **0,0%**
- [ ] **Refazer a Figura 2** (composição por seção e distribuição de tamanho)
- [ ] "Python 3.11" → **3.13.7**
- [ ] Remover/ajustar *"~100k documents ... compatible with personal hardware and
      Google Colab"* — não se sustenta (são 9 dias de CPU nessa escala)

---

## 🟡 3. Trabalhos Relacionados — reforçar o argumento do BR-TaxQA-R

Já apurado (ver [04-referencias-verificadas.md](04-referencias-verificadas.md)):
eles compararam janela deslizante de **2.048 tokens** contra um splitter
recursivo de **1.000 caracteres** (~250 tokens), avaliando **geração** (RAGAS).

- [ ] Acrescentar ao artigo que a comparação deles **confunde estrutura com
      tamanho de chunk** (granularidade 8x diferente), que o splitter deles não
      respeita macro-seções, e que a métrica é de geração — as três limitações
      que este trabalho corrige. É a resposta pronta para a pergunta mais
      provável da banca.
- [ ] Atualizar `demartim2025ontology` para citar o **JURIX 2025** (IOS Press),
      não só o preprint arXiv.

---

## 🔴 1b. O retriever denso NÃO roda em CPU — precisamos de GPU

**Medido, não estimado** (2026-09-06):

```
intfloat/multilingual-e5-base, CPU (10 threads torch), batch 64, chunks reais
128 chunks em 26,7s  ->  4,8 chunks/s
```

Minha estimativa anterior era de ~25 chunks/s. **Errei por 5x.** Com a taxa
real:

| Cenário | Chunks | Tempo em CPU |
|---|---:|---|
| Corpus 12.880, as 5 estratégias | 2.200.767 | **127 h ≈ 5,3 dias** ❌ |
| Só `structural_gold` + `fixed_1024_512` | 737.475 | 43 h |
| Só `structural_gold` | 286.689 | 17 h |

Numa GPU T4 (Colab) a mesma carga sai em ~2 h — a diferença é de ~60x.

**Opções, em ordem de preferência:**

1. **Rodar o encode no Colab com GPU** e trazer os `.npy` de volta. O cache já
   está implementado (`emb_<modelo>.npy` + `chunk_ids_<modelo>.json` por
   estratégia), então é só copiar os arquivos para `data/processed/<estrategia>/`
   e o `run_experiments` os reaproveita sem reencodar. **É o caminho que
   recomendo.**
2. Alguém do time com GPU local roda e compartilha os `.npy`.
3. Reduzir o escopo do denso para 2 ou 3 estratégias (o plano já prevê isso:
   *"se o encode em CPU passar de ~6h, reduzir a 1 modelo denso e registrar a
   decisão"* — `plano_implementacao.md` §F4). Perderíamos parte da comparação.
4. Deixar 5,3 dias de CPU rodando. Só viável se ninguém precisar da máquina.

- [ ] **Definir com o time: quem tem GPU, ou vamos de Colab?**

> Isso também **reforça** a recomendação do corpus de 12.880 (item 1): com
> 113.827 documentos seriam ~19,5 M chunks, ou seja, **~47 dias de CPU** /
> ~18 h de GPU. Inviável de qualquer ângulo sem GPU dedicada.

---

## 🟢 4. Execução (posso tocar sozinho)

- [x] Ambiente, datasets (6 GB) e corpus montado
- [x] F4 e F5 implementadas, **110 testes** passando
- [x] Chunking do corpus completo: 2.200.767 chunks nas 5 estratégias
- [x] Runs BM25 (5 estratégias) → **primeiro nDCG@10**, reproduzido idêntico em 2 rodadas
- [x] Tabelas: `main_results.csv`, `significance.csv`, `power_analysis.csv`, os 4 recortes
- [x] Figuras autocontidas (`src/plots.py`)
- [x] GPU resolvida: RTX 5060 + `torch cu130`, bge-m3 fp16, ~10 h para o denso completo
- [x] Runs densos, 3 de 5 (`20260906-0547_dense_bge_m3`, 4,94 h) — **BM25 vence o denso com p < 0,01**
- [ ] Runs densos das duas estratégias fixas — em execução, reaproveitando o cache
- [ ] Análise de sensibilidade da agregação (`sum_top_k` vs `max_pooling`)
- [ ] Notebooks 01–03 (só consomem `results/`)

A pergunta sobre GPU está respondida: a RTX 5060 do Leo dá conta. O item 1b
abaixo fica como registro do que foi medido.

---

## 🔵 5. Melhorias no código que dependem de aval do Igor

Não mexi porque a orientação foi não alterar a estrutura antes de confirmar:

- [ ] `ingest.py` gravar `n_tokens` no `corpus_docs.jsonl`, como manda o
      contrato do `plano_implementacao.md` §2 (hoje o `corpus_stats()` calcula e
      descarta). Contornei com cache em `doc_lengths.json`, mas o certo é na
      fonte.
- [ ] `ingest.py` importar de `src/tokenization.py` em vez de chamar `tiktoken`
      direto — o plano pede tokenizer único centralizado.

---

## Uma nota sobre o cronograma

O `plano_tecnico.md` põe o "primeiro número na tabela" na **Semana 7** e a
tabela final fechada na **Semana 11**. Com F4 e F5 já implementadas e o corpus
montado, o gargalo restante deixou de ser código e passou a ser **decisão
(item 1) + tempo de GPU/CPU (item 4)**. São ~4 meses até a entrega: dá folga
confortável, desde que a decisão do corpus não fique parada — porque **tudo**
que for medido antes dela terá de ser refeito depois.
