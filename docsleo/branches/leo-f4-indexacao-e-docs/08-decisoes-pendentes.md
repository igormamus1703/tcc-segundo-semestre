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

Já apurado (ver [03-referencias-verificadas.md](03-referencias-verificadas.md)):
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

## 🟢 4. Execução (posso tocar sozinho)

- [x] Ambiente, datasets (6 GB) e corpus montado
- [x] F4 e F5 implementadas, 84 testes passando
- [x] Chunking do corpus completo: 2.200.767 chunks nas 5 estratégias
- [ ] Runs BM25 (5 estratégias) → **primeiro nDCG@10**
- [ ] Runs densos (5 estratégias) — ~24 h de CPU, ou ~2 h se alguém tiver GPU
- [ ] Tabelas finais: `main_results.csv`, `significance.csv`, os 3 recortes
- [ ] Análise de sensibilidade da agregação (`sum_top_k` vs `max_pooling`)
- [ ] Notebooks 01–03 (só consomem `results/`)

**Pergunta prática para o time:** alguém tem GPU disponível, ou usamos Colab? O
encode denso é o único passo que realmente demora. Com o cache `.npy`
implementado, só precisa rodar **uma vez** por modelo.

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
