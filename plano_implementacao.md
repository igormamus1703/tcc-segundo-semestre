# Plano de Implementação — juris-chunking

Plano de execução do código, escrito para ser executado fase a fase (Sonnet 5).
Complementa o `plano_tecnico.md` (arquitetura e cronograma) e o **substitui onde
houver conflito**, porque incorpora achados empíricos medidos no corpus real.

**Estado do código em 18/08:** o esqueleto de módulos em `juris-chunking/src/`
(stubs com `NotImplementedError`) segue a arquitetura do `plano_tecnico.md` e
continua válido na forma — os contratos (`Chunker`, `Chunk`, agregação
chunk→doc) não mudam. O que fica obsoleto e será reescrito na F1/F2: as regex
de `segmenter/rules.py` (assumem marcadores que não existem no corpus) e o
corpus-alvo de `ingest.py` e `configs/chunkers.yaml` (4→5 estratégias). Nada
disso foi commitado ainda, então a F1 pode reescrever livremente.

---

## 0. Decisão de corpus (gate da Semana 3, antecipado e decidido em 18/08)

Verificado diretamente sobre os dados:

1. **O JurisTCU cru não contém acórdãos íntegros.** Cada um dos 16.045 docs é um
   enunciado de jurisprudência (`ENUNCIADO`, mediana 279 chars) + um excerto do
   julgado (`EXCERTO`, mediana 3,5k chars) — total mediano ~1k tokens, na
   fronteira do gate de viabilidade. Marcadores tipográficos (`^EMENTA` etc.)
   existem em <2% dos docs.

2. **Decisão: corpus enriquecido — acórdãos íntegros do TCU + qrels do JurisTCU.**
   98,7% dos docs do JurisTCU identificam seu acórdão de origem via
   (`NUMACORDAO`, `ANOACORDAO`, `COLEGIADO`) → **12.881 acórdãos únicos**,
   anos 2003–2023. O TCU publica os acórdãos completos em dados abertos, um CSV
   por ano:
   `https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/acordao-completo-{ANO}.csv`
   (separador `|`, aspas duplas; verificado no arquivo de 2020).

3. **Os CSVs do TCU trazem cada seção em coluna separada** — estrutura "ouro"
   de graça: `SUMARIO`, `ACORDAO`, `RELATORIO`, `VOTO`, `DECLARACAOVOTO`,
   `VOTOCOMPLEMENTAR`, `VOTOMINISTROREVISOR`, + metadados (`NUMACORDAO`,
   `ANOACORDAO`, `COLEGIADO`, `RELATOR`, `TIPOPROCESSO`...). O texto das colunas
   vem SEM o cabeçalho da seção (ex.: coluna `ACORDAO` começa em "VISTOS,
   relatados..."), com HTML leve (`<p>`, `<br>`, tags de citação
   `<acordao_decisao_tcu>`, `<processo>`).

4. **Qrels reaproveitados por remapeamento.** As 150 queries (com tipo em
   `SOURCE`) e os julgamentos graduados (1–3) do JurisTCU são mantidos;
   `qrel.DOC_ID → KEY do doc → acórdão de origem`. Quando 2+ docs apontam para o
   mesmo acórdão (2.034 casos), o score da dupla (query, acórdão) é o **máximo**.
   Caveat metodológico a discutir no TCC: a relevância foi julgada sobre o
   enunciado/excerto, e é transferida ao acórdão-documento que o contém
   (defensável: o excerto é parte do acórdão; relevância em nível de documento).

5. **Gate residual (F1):** se o join falhar em >10% dos acórdãos ou os CSVs do
   TCU estiverem indisponíveis/incompletos para anos antigos, voltar ao plano
   JurisTCU-cru: usar enunciado+excerto como documento e segmentar pelos
   cabeçalhos HTML em negrito (`<b>Acórdão</b>` presente em 91,5% dos docs,
   `<b>Voto</b>` em 83%), convertidos em marcadores canônicos na normalização.
   Alternativas descartadas: `brazilian_court_decisions` (só ementas, sem
   qrels), `jurisprudencias_stj` (sem qrels).

**Consequência metodológica (upgrade):** com estrutura ouro por coluna, o
segmentador por regras é validado **automaticamente contra ~13k acórdãos** (a
anotação manual de 80 docs vira uma checagem de sanidade de ~20 docs), e o
chunker estrutural ganha uma ablação valiosa: `structural-gold` (spans das
colunas) vs. `structural-pred` (spans do segmentador) vs. baselines.

**Taxonomia de seções (coluna TCU → rótulo `Section`):**

| Coluna TCU | Rótulo `Section` |
|---|---|
| `SUMARIO` | `ementa` |
| `RELATORIO` | `relatorio` |
| `VOTO`, `DECLARACAOVOTO`, `VOTOCOMPLEMENTAR`, `VOTOMINISTROREVISOR` | `fundamentacao` |
| `ACORDAO` | `dispositivo` |

---

## 1. Montagem do documento e estratégia de normalização

**Texto do documento = concatenação "natural" das colunas de seção**, na ordem
canônica (`SUMARIO`, `RELATORIO`, `VOTO`, `DECLARACAOVOTO`, `VOTOCOMPLEMENTAR`,
`VOTOMINISTROREVISOR`, `ACORDAO`), separadas por `\n\n`, **sem injetar
cabeçalhos** — como o texto corrido de um acórdão real. Isso evita
circularidade: o segmentador precisa recuperar as fronteiras a partir de pistas
textuais genuínas ("É o relatório", "Ante o exposto", "VISTOS, relatados e
discutidos", "ACORDAM os Ministros", "9.1."...), e é validado contra as
fronteiras ouro conhecidas da montagem.

Normalização de cada coluna (função pura `normalize_html`):
1. `html.unescape` das entidades.
2. `<acordao_decisao_tcu ...>texto</acordao_decisao_tcu>` e
   `<processo ...>texto</processo>` → manter só `texto`.
3. `</p>`, `</td>`, `</tr>`, `<br>` → quebra de linha; demais tags → remover.
4. Colapsar espaços múltiplos; 3+ quebras → `\n\n`; `strip()`.

Durante a montagem, registrar os offsets (start, end) de cada seção no texto
final → **spans ouro**, gravados junto ao doc. Colunas vazias são puladas.
Invariante em todo o pipeline: `doc.text[start:end] == chunk.text`.

---

## 2. Formatos de dados (contratos entre fases)

- `data/tcu_acordaos/acordao-completo-{2003..2023}.csv` — download bruto (não versionar).
- `data/interim/corpus_docs.jsonl` — 1 acórdão/linha:
  `{"doc_id": "<NUMACORDAO>-<ANOACORDAO>-<colegiado_slug>", "text": str, "n_tokens": int, "gold_spans": [{"section", "start", "end"}], "ano": int, "colegiado": str, "tipo_processo": str}`
- `data/interim/queries.jsonl` — `{"query_id": str, "text": str, "source": str}` (do `query.csv` do JurisTCU).
- `data/interim/qrels.trec` — `qid 0 doc_id score` já **remapeado** para os novos doc_ids (máximo por par).
- `data/interim/join_report.json` — taxa de match do join, docs sem acórdão, qrels perdidos.
- `juris-chunking/data/processed/{estrategia}/chunks.jsonl` — campos do dataclass `Chunk`.
- `juris-chunking/data/processed/{estrategia}/emb_{modelo}.npy` + `chunk_ids.json` — cache de embeddings.
- `results/runs/{estrategia}__{retriever}[__{agregacao}].trec` — TREC run: `qid Q0 docid rank score nome`.
- `results/tables/` — `eda_stats.json`, `segmenter_validation.json`, `main_results.csv`, `significance.csv`, `slices_*.csv`.
- Tokenizer único: **tiktoken `cl100k_base`** (wrapper em `src/tokenization.py`).

---

## 3. Fases de implementação

Cada fase termina com testes (`pytest`), um smoke-run e um artefato verificável.
**Não começar a fase seguinte sem fechar a anterior.**

### F0 — Ambiente (30 min)
- Instalar `requirements.txt` no `.venv` do `juris-chunking` (hoje só tem pytest).
- Maior risco: `ranx` (numba) no Python 3.13 — testar primeiro; fallback: venv
  com Python 3.11/3.12.
- Aceite: `python -c "import faiss, bm25s, tiktoken, ranx, sentence_transformers"`.

### F1 — Download, join e montagem do corpus (`scripts/` + `src/ingest.py`)
- Estender `scripts/download_datasets.py` com o dataset `tcu_acordaos`: baixa os
  21 CSVs anuais (2003–2023) da URL da seção 0 para `data/tcu_acordaos/`
  (arquivo temporário + rename; retomável; alguns anos são grandes).
- `src/ingest.py`:
  - Ler os CSVs do TCU (separador `|`, `csv.field_size_limit` alto), indexar por
    (`NUMACORDAO`, `ANOACORDAO`, `COLEGIADO`) normalizados (número sem `.0`,
    colegiado sem acento/caixa).
  - Join com `doc.csv` do JurisTCU (mesma chave) → conjunto dos 12.881 acórdãos
    referenciados. Montar texto + spans ouro (seção 1), gravar
    `corpus_docs.jsonl`, `queries.jsonl`, `qrels.trec` remapeado e
    `join_report.json`.
  - **Gate residual:** match ≥ 90% dos acórdãos e ≥ 90% das entradas de qrel
    preservadas; senão, parar e discutir.
  - `corpus_stats()` → tokens/doc (mediana, p90, p99) do NOVO corpus, presença
    de cada seção (fração de docs com RELATORIO, VOTO etc. não vazios),
    cobertura dos qrels → `results/tables/eda_stats.json`.
- Testes: `normalize_html` (fixtures com tag de citação, entidades, `<p>`);
  normalização de chave de join; remapeamento de qrel com máximo por par.
- Aceite: `python -m src.ingest` ponta a ponta; conferir 2–3 docs no olho e o
  `join_report.json`.

### F2 — Segmentador (`src/segmenter/`)
- `rules.py`: reescrever para pistas textuais reais de acórdão íntegro
  (a validar/iterar contra os spans ouro): início de `relatorio` ≈ padrões de
  abertura de relatório; fronteira relatório→voto ≈ "É o relatório";
  `fundamentacao`→`dispositivo` ≈ "VISTOS, relatados e discutidos" /
  "ACORDAM os Ministros"; encerramento de voto ≈ "Ante o exposto", "Isto posto".
  Manter o dicionário padrão→`Section`.
- `segment.py`: matches ordenados, dedupe, spans contíguos; sem marcador →
  doc inteiro `indefinido`; reportar `fallback_rate`.
- `validate.py`: **validação automática contra `gold_spans`** de todo o corpus —
  acurácia por caractere + precisão/cobertura por seção →
  `results/tables/segmenter_validation.json`. Amostra manual: 20 docs só para
  sanidade da montagem (não 80 — o gabarito agora é derivado das colunas).
- Testes: docs sintéticos (todas as seções; só voto+acórdão; sem marcador).
- Aceite: `python -m src.segmenter.validate` imprime acurácia global e por
  seção; iterar regras até estabilizar (reportar a curva de iterações no TCC).

### F3 — Chunkers (`src/chunkers/`)
- `src/tokenization.py`: `count_tokens`, e
  `token_windows(text, size, stride) -> [(start_char, end_char)]` via `encode` +
  `decode_tokens_bytes` cumulativo (cuidado com fronteiras UTF-8; testar com
  acentos).
- `fixed.py`: janelas por token; janela final parcial incluída.
- `recursive.py`: `RecursiveCharacterTextSplitter` (separadores do YAML,
  `length_function=count_tokens`); offsets via `str.find` com cursor móvel.
- `structural.py`: recebe spans (parâmetro: ouro do `corpus_docs.jsonl` OU
  preditos pelo `Segmenter` — **duas variantes de run**); span ≤
  `max_section_tokens` → 1 chunk rotulado; maior → subjanelas com overlap
  propagando o rótulo; nunca cruzar fronteira. `indefinido` → `section=None`.
- `chunk_id = f"{doc_id}::{estrategia}::{i:04d}"`.
- CLI `python -m src.chunkers.run --strategy all` → 5 estratégias:
  `fixed_512_256`, `fixed_1024_512`, `recursive_default`, `structural_gold`,
  `structural_pred` (atualizar `configs/chunkers.yaml`).
- Testes: invariante de offsets; não-cruzamento; propagação de rótulo; stride.

### F4 — Indexação + runs (`src/indexing/`, `src/run_experiments.py`)
- `lexical.py`: `bm25s` — lowercase + sem acentos + stopwords PT.
- `dense.py`: `SentenceTransformer`, `normalize_embeddings=True`, lotes de 64,
  `faiss.IndexFlatIP`, cache `.npy`; prefixos `query:`/`passage:` se e5.
- `configs/models.yaml`: `pt_compact` = `intfloat/multilingual-e5-base` como
  default executável (trocar por modelo PT do topo do MTEB-BR só após conferir
  o paper). **Atenção ao volume**: corpus agora é de acórdãos íntegros —
  estimar nº de chunks na F3; se o encode em CPU passar de ~6h, reduzir a 1
  modelo denso e registrar a decisão.
- `src/run_experiments.py`: para cada estratégia × retriever: top-2000 chunks →
  agregação (`max_pooling` padrão; `sum_top_k(3)` sensibilidade) → top-1000
  docs → run TREC. 10 runs principais (5 estratégias × 2 retrievers).
- Smoke: `--limit-docs 500 --limit-queries 10` antes do corpus cheio; encode
  denso em background.
- Aceite ("primeiro número"): BM25 × 5 estratégias com nDCG@10.

### F5 — Avaliação, significância e recortes (`evaluate.py`, `analysis.py`)
- `evaluate.py`: `ranx` → nDCG@10, MRR@10, MAP@10, Recall@100;
  `paired_significance` via `ranx.compare` (pareado, correção múltipla) →
  `main_results.csv`, `significance.csv`.
- `analysis.py`: `bootstrap_ci` (reamostrar queries, 10k, IC 95%); recorte por
  tipo de consulta (`SOURCE`); por tamanho de doc (filtrar qrels por tercil de
  `n_tokens` e reavaliar); por retriever (runs separadas).
- Notebooks 01–03 por último, só consumindo `results/` — sem cálculo pesado.
- Aceite: tabela final 5 estratégias × 2 retrievers com IC e significância +
  três recortes em CSV.

---

## 4. Roteiro de execução com o Sonnet (controle de custo)

Restrição: **orçamento total da conta ≤ US$ 100**; o planejamento (Fable) já
consumiu parte. Regras para as sessões de execução:

1. **Uma fase por sessão**, com `/clear` entre fases. Abrir a sessão com:
   "implemente a fase FX do plano_implementacao.md" — o plano tem contexto
   suficiente; não reler o corpus nem redescobrir os achados.
2. Nunca imprimir CSVs/JSONLs grandes no chat; inspecionar com scripts que
   imprimem só agregados ou 2–3 exemplos.
3. Não ler `.venv/`, `data/` cru, nem `.pyc`.
4. Downloads e encodes longos em background (custo é compute local, não token).
5. Estimativa por fase, com disciplina: F0 ≈ US$ 1–2; F1 ≈ US$ 5–8 (a mais
   delicada: join + montagem); F2 ≈ US$ 4–6; F3 ≈ US$ 4–7; F4 ≈ US$ 5–8;
   F5 ≈ US$ 4–6. Total ≈ US$ 23–37. Se uma sessão passar de ~US$ 10, parar e
   dividir a fase.
6. Zero API paga de LLM/embedding no pipeline.

---

## 5. Riscos específicos

| Risco | Mitigação |
|---|---|
| CSVs anuais do TCU indisponíveis ou schema diferente em anos antigos | F1 valida schema por arquivo; gate residual de 90%; fallback: plano JurisTCU-cru (histórico git) |
| Join < 90% (formatos de número/colegiado divergentes) | Normalizar chave (sem `.0`, sem acento); relatório de não-casados para inspeção |
| Volume: 21 CSVs (possivelmente vários GB) no OneDrive | Baixar para `data/` com tmp+rename; se OneDrive travar, mover `data/` para fora da pasta sincronizada e apontar via config |
| `ranx`/numba incompatível com Python 3.13 | Testar na F0; fallback venv 3.11/3.12 |
| Offsets token→char com UTF-8 (tiktoken) | Decodificar bytes acumulados; teste com acentos |
| Encode denso lento (corpus agora é grande) | Cache `.npy`; smoke com subset; 1 modelo se necessário; rodar à noite |
| Relevância julgada no excerto, transferida ao acórdão | Discutir como limitação; é relevância em nível de documento (defensável) |

---

## 6. Definition of done global

1. `join_report.json` com match ≥ 90% e qrels preservados ≥ 90%.
2. `results/tables/segmenter_validation.json` — acurácia contra spans ouro no corpus inteiro.
3. `results/tables/main_results.csv`: 5 estratégias × 2 retrievers × 4 métricas.
4. `results/tables/significance.csv` com testes pareados corrigidos.
5. `results/tables/slices_{query_type,doc_length,retriever}.csv`.
6. `pytest` verde; README com comandos de reprodução atualizados.
