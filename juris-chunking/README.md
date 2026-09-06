# juris-chunking

Segmentação estrutural de acórdãos para RI jurídica — TCC.

Comparação de estratégias de chunking (fixo, recursivo, estrutural) na
recuperação de informação sobre acórdãos do TCU, avaliando BM25 e um
retriever denso com nDCG@10, MRR@10, MAP@10 e Recall@100.

Ver `plano_implementacao.md` (na raiz do repositório) para o plano de
execução fase a fase — é o documento a seguir para saber "o que fazer
agora"; `plano_tecnico.md` traz a arquitetura, o cronograma e o roteiro de
leitura completos.

## Setup (para quem está entrando no projeto agora)

1. **Clone o repositório e crie o venv de preferência fora de pastas
   sincronizadas por nuvem** (OneDrive/Drive/Dropbox) — o corpus ocupa
   vários GB e o cliente de sincronização atrapalha tanto o download dos
   dados quanto o `.venv`. Se o repo em si já está numa pasta sincronizada
   (como este), pelo menos mantenha `data/` e `.venv/` fora, com link
   simbólico (ver `scripts/README.md`).

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Baixe os datasets** (na raiz do repositório, não aqui dentro):

   ```bash
   python scripts/download_datasets.py juristcu
   python scripts/download_datasets.py tcu_acordaos   # ~6 GB, demora
   ```

   Detalhes, tamanhos e a recomendação de onde colocar `data/` estão em
   `scripts/README.md`.

3. **Monte o corpus** (a partir desta pasta, `juris-chunking/`):

   ```bash
   python -m src.ingest
   ```

   Isso faz o join JurisTCU × acórdãos do TCU, monta os documentos com os
   spans ouro por seção e grava `data/interim/corpus_docs.jsonl`,
   `queries.jsonl`, `qrels.trec` e `join_report.json`. Verifica sozinho o
   gate de qualidade (match ≥ 90%, qrels preservados ≥ 90%) e levanta
   `RuntimeError` se falhar — não segue silenciosamente com corpus ruim.
   Demora alguns minutos (lê ~6 GB de CSV).

4. **Confirme que está tudo certo:**

   ```bash
   pytest
   ```

## Status (ver `plano_implementacao.md` seção 3 para os critérios de cada fase)

- [x] **F0 — Ambiente**: `.venv` + `requirements.txt`.
- [x] **F1 — Ingestão**: corpus = acórdãos íntegros do TCU + qrels do
      JurisTCU remapeados. Gate passou: **98,7%** match de docs, **99,69%**
      qrels preservados, **12.880** documentos
      (`results/tables/eda_stats.json`, `join_report.json`).
- [x] **F2 — Segmentador**: regras calibradas contra o texto real,
      validadas automaticamente contra os spans ouro do corpus inteiro —
      **92,2%** de acurácia por caractere, **0,0%** de fallback
      (`results/tables/segmenter_validation.json`; curva de iteração
      documentada no docstring de `src/segmenter/rules.py`). As regras foram
      calibradas sobre 113k acórdãos e mantêm a acurácia neste subconjunto
      sem recalibração.
- [x] **F3 — Chunkers**: `fixed` (2 configs), `recursive` e `structural`
      (`gold`/`pred`) — 5 estratégias, validadas ponta a ponta contra o
      corpus real (invariante `doc.text[start:end] == chunk.text` conferida,
      zero divergências). Achado: o `add_start_index` nativo do
      `RecursiveCharacterTextSplitter` quebra com `length_function` em
      tokens — corrigido com cursor manual (`src/chunkers/recursive.py`).
- [x] **F4 — Indexação + runs**: BM25 (`bm25s`) e denso
      (`sentence-transformers` + FAISS `IndexFlatIP`, com cache `.npy`),
      agregação chunk→doc e CLI `src/run_experiments.py` que grava os TREC
      runs. `configs/models.yaml` resolvido: `pt_compact` =
      `embeddinggemma-300m` (13º de 93 no MTEB-BR com 308M parâmetros) e
      default sem gate = `multilingual-e5-base`.
- [x] **F5 — Avaliação, significância e recortes**: métricas via `ranx`,
      comparação pareada com correção para comparações múltiplas, bootstrap
      (IC 95%) e os três recortes. `python -m src.evaluate` gera as tabelas.

> ⚠️ **Corpus:** o `eda_stats.json`/`segmenter_validation.json` versionados
> foram regerados em 05/09 sobre o corpus que o `ingest.py` produz hoje
> (**12.880** acórdãos, não 113.827 — ver `docsleo/branches/leo-f4-indexacao-e-docs/02-achado-corpus.md`). A
> escolha do corpus oficial ainda está pendente de decisão da equipe, e os
> números do artigo dependem dela.

## Uso

```bash
python scripts/download_datasets.py juristcu tcu_acordaos  # (raiz do repo)
python -m src.ingest                  # monta o corpus + roda EDA
python -m src.segmenter.validate      # mede acurácia do segmentador contra o gabarito
python -m src.chunkers.run --strategy all --limit-docs 500  # smoke test
python -m src.chunkers.run --strategy all                   # corpus inteiro
python -m src.run_experiments --strategy all --retriever bm25    # F4: runs BM25
python -m src.run_experiments --strategy all --retriever dense   # F4: runs densos
python -m src.evaluate                # F5: gera results/tables/*.csv
pytest                                # roda a suíte de testes
```

Smoke test da F4 antes de rodar o corpus inteiro:

```bash
python -m src.run_experiments --strategy all --retriever bm25 --limit-queries 10
```

**Retriever denso — um passo manual, e só se quiser o modelo melhor.** O
`pt_compact` (`google/embeddinggemma-300m`) é *gated* no Hugging Face: exige
conta, aceite da licença Gemma e `hf auth login`. O **default do pipeline é o
`multilingual_ref`** (`intfloat/multilingual-e5-base`, MIT, sem gate), então
tudo roda ponta a ponta sem nenhum cadastro. Para usar o gated:

```bash
hf auth login
python -m src.run_experiments --strategy all --retriever dense --embedder pt_compact
```

## Estrutura

Ver seção 2 do `plano_implementacao.md` para os formatos de dados
(contratos entre fases) e seção 1 do `plano_tecnico.md` para a árvore
completa do código e o contrato `Chunk` compartilhado entre os módulos.
