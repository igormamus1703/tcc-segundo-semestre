# Plano de Implementação — juris-chunking

Plano de execução do código, escrito para ser executado fase a fase (Sonnet 5).
Complementa o `plano_tecnico.md` (arquitetura e cronograma) e o **substitui onde
houver conflito**, porque incorpora achados empíricos medidos no corpus real.

---

## STATUS ATUAL — 07/09/2026

**F0 a F5 concluídas. O experimento foi rodado nos dois retrievers.**

> 📍 Para o panorama do projeto, próximos passos e o que cada integrante pode
> pegar, veja o **[PLANO.md](PLANO.md)** na raiz. Este documento mantém o
> detalhe fase a fase.

| Fase | Estado | Evidência |
|---|---|---|
| F0 — Ambiente | ✅ | Python 3.13.7; `ranx`/numba rodam em 3.13, o fallback 3.11/3.12 **não foi necessário** |
| F1 — Ingestão | ✅ | **12.880** docs, join 98,7%, qrels preservados 99,69% (`results/corpus/eda_stats.json`) |
| F2 — Segmentador | ✅ | **92,2%** de acurácia por caractere, **0%** de fallback (`results/corpus/segmenter_validation.json`) |
| F3 — Chunkers | ✅ | **2.200.767** chunks nas 5 estratégias, invariante de offset conferida |
| F4 — Indexação + runs | ✅ | BM25 (`20260906-0515_bm25`) e denso (`20260906-1046_dense_bge_m3`) |
| F5 — Avaliação | ✅ | Tabelas, significância, poder estatístico e 4 recortes, nos dois retrievers |

**Marco da Semana 7 (primeiro número) e da Semana 11 (tabela fechada) —
ambos alcançados**, com semanas de antecedência.

### A resposta à pergunta de pesquisa

**O chunking estrutural NÃO melhora a recuperação.** De 20 pares entre
estratégias, **1** tem p < 0,05: `fixed_512_256` × `structural_gold` no denso
(p = 0,030) — e ele aponta **contra** a hipótese, com o chunking fixo superando
o estrutural. No BM25, 0 de 10 (menor p = 0,097). Resultado nulo bem medido,
que o `plano_tecnico.md` §7 já previa como desfecho legítimo.

**O resultado mais sólido é outro:** o BM25 supera o retriever denso nas
**cinco** estratégias, com p entre 0,000005 e 0,002.

| Estratégia | BM25 | Denso (bge-m3) |
|---|---:|---:|
| structural_pred | **0,2526** | 0,1912 |
| structural_gold | 0,2521 | 0,1847 |
| fixed_1024_512 | 0,2510 | 0,2019 |
| fixed_512_256 | 0,2486 | **0,2055** |
| recursive_default | 0,2412 | 0,1967 |

**A ordem se inverte quase perfeitamente entre os retrievers** — as duas
estruturais são 1ª e 2ª no BM25 e 4ª e 5ª no denso; as duas fixas fazem o
caminho contrário. A inversão é sistemática e é evidência **contra** um efeito
estável do chunking estrutural — mais forte do que um empate simples seria.

**Uma intervenção que funcionou:** descartar o relatório do índice melhora o
nDCG@10 em **16,9%** (p = 0,001), e o ganho se mantém com os spans preditos
pelo segmentador (p = 0,017). É exploratório — precisa ser reimplementado em
`src/` antes de ir para o artigo. Ver
`docs/docsleo/branches/leo-f4-indexacao-e-docs/resultados/05-filtragem-por-secao.md`.

### O que falta, em ordem

1. **🔴 Decidir o corpus oficial.** O artigo e o pôster dizem 113.827
   documentos; o código produz 12.880. **Ficou mais urgente**: um resultado
   significativo medido no corpus errado vai para o artigo como afirmação
   forte. Ver `docs/docsleo/branches/leo-f4-indexacao-e-docs/02-achado-corpus.md`.
2. Análise de sensibilidade da agregação (`sum_top_k` vs `max_pooling`) — o
   cache já existe, é barato.
3. Notebooks 01–03, que só consomem `results/`.
4. Corrigir os números do artigo e do pôster (lista em
   `docs/docsleo/branches/leo-f4-indexacao-e-docs/07-numeros-para-o-artigo.md`).

### Decisões técnicas tomadas depois do plano original

- **Embedder = `BAAI/bge-m3`**, não `multilingual-e5-base`. O e5 tem janela de
  512 tokens e truncaria **83%** dos chunks, descartando **37%** do conteúdo —
  e só a `fixed_512_256` caberia inteira, ganhando vantagem artificial. Com o
  bge-m3 (janela 1024) o truncamento é **zero** em todas as estratégias.
- **`results/` reorganizado**: `results/corpus/` para a caracterização do
  corpus e `results/experiments/AAAAMMDD-HHMM_rotulo/` para cada rodada, com
  `manifest.json` (commit, hardware, versões, tempos). Ver `results/README.md`.
- **GPU**: `torch 2.14.0+cu130` (a RTX 5060 é Blackwell). O encode denso em CPU
  levaria 127 h; em GPU, ~10 h.

---

**Status anterior (24/08):** F0, F1, F2 e F3 concluídas. F1: gate passou (97,9%
match de docs, 99,2% qrels preservados). F2: segmentador validado contra o
corpus inteiro, 92,7% de acurácia por caractere (curva de iteração no docstring
de `juris-chunking/src/segmenter/rules.py`). F3: 5 estratégias de chunking
implementadas e validadas ponta a ponta contra o corpus real (offsets
conferidos, zero divergências); um bug real foi encontrado e corrigido no
recursive (offset recovery nativo do LangChain assumia unidade errada para
`chunk_overlap` — ver docstring de `src/chunkers/recursive.py`).

> ⚠️ Os números deste parágrafo de 24/08 foram medidos sobre um corpus de
> 113.827 documentos, que o código **não produz mais**. Os valores válidos são
> os da tabela acima. Ver o achado de corpus citado no item 1.

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
- `results/corpus/` — `eda_stats.json`, `segmenter_validation.json` (caracterização do corpus; muda só quando o corpus muda).
- `results/experiments/<AAAAMMDD-HHMM>_<rótulo>/` — uma pasta por rodada, com `manifest.json` (commit, hardware, versões, tempos), `execucao.log`, `runs/*.trec`, `runs/*__chunks.jsonl`, `tables/*.csv` e `figuras/*.pdf|png`. **Este layout substitui o `results/tables/` plano descrito acima**, que existia quando o plano foi escrito; ver `results/README.md`.
- Tokenizer único: **tiktoken `cl100k_base`** (wrapper em `src/tokenization.py`).

---

## 3. Fases de implementação

Cada fase termina com testes (`pytest`), um smoke-run e um artefato verificável.
**Não começar a fase seguinte sem fechar a anterior.**

### F0 — Ambiente (30 min) ✅ concluída
- Instalar `requirements.txt` no `.venv` do `juris-chunking` (hoje só tem pytest).
- Maior risco: `ranx` (numba) no Python 3.13 — testar primeiro; fallback: venv
  com Python 3.11/3.12.
- Aceite: `python -c "import faiss, bm25s, tiktoken, ranx, sentence_transformers"`.

### F1 — Download, join e montagem do corpus (`scripts/` + `src/ingest.py`) ✅ concluída
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
    cobertura dos qrels → `results/corpus/eda_stats.json`.
- Testes: `normalize_html` (fixtures com tag de citação, entidades, `<p>`);
  normalização de chave de join; remapeamento de qrel com máximo por par.
- Aceite: `python -m src.ingest` ponta a ponta; conferir 2–3 docs no olho e o
  `join_report.json`.

### F2 — Segmentador (`src/segmenter/`) ✅ concluída
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
  `results/corpus/segmenter_validation.json`. Amostra manual: 20 docs só para
  sanidade da montagem (não 80 — o gabarito agora é derivado das colunas).
- Testes: docs sintéticos (todas as seções; só voto+acórdão; sem marcador).
- Aceite: `python -m src.segmenter.validate` imprime acurácia global e por
  seção; iterar regras até estabilizar (reportar a curva de iterações no TCC).

### F3 — Chunkers (`src/chunkers/`) ✅ concluída
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

### F4 — Indexação + runs (`src/indexing/`, `src/run_experiments.py`) ✅ concluída
- `lexical.py`: `bm25s` — lowercase + sem acentos + stopwords PT (a mesma
  normalização na indexação e na busca, em `text_norm.py`). ✅
- `dense.py`: `SentenceTransformer` + `faiss.IndexFlatIP`,
  `normalize_embeddings=True`, cache `.npy` invalidado pelo conjunto de
  `chunk_id`; janela, precisão e device configuráveis. ✅
- `src/run_experiments.py`: top-2000 chunks → agregação → top-1000 docs → run
  TREC, com pasta datada e manifesto por rodada. ✅
- **Aceite ("primeiro número") — ATINGIDO:** BM25 × 5 estratégias, nDCG@10 de
  0,2412 a 0,2526 (`results/experiments/20260906-0215_bm25/`).

**Correções ao que este plano dizia, com base no que foi medido:**

1. **O embedder não é o `multilingual-e5-base`.** A janela dele é de 512
   tokens e truncaria 83% dos chunks (37% do conteúdo), e só a
   `fixed_512_256` caberia inteira — vantagem artificial que invalidaria a
   comparação. **Adotado o `BAAI/bge-m3`** (janela 1024, Apache-2.0, sem gate):
   truncamento zero em todas as estratégias.
2. **O `pt_compact` do MTEB-BR é o `google/embeddinggemma-300m`** (13º de 93
   com 308M parâmetros), mas é **gated**: exige `hf auth login`. Por isso não é
   o default — o pipeline tem que rodar sem passo manual.
3. **O gargalo é a GPU, não a CPU.** Perfil: 100% do tempo é forward,
   tokenização é 5,9%. Encode em CPU levaria 127 h; em GPU (RTX 5060, fp16),
   ~10 h. `torch.compile`, TF32 e deduplicação de chunks foram testados e não
   ajudam (0,99x, 0,99x e 0,4% de redundância).

### F5 — Avaliação, significância e recortes (`evaluate.py`, `analysis.py`) ✅ concluída
- `evaluate.py`: `ranx` → nDCG@10, MRR@10, MAP@10, Recall@100;
  `paired_significance` via `ranx.compare` (pareado, correção múltipla). ✅
- `analysis.py`: `bootstrap_ci` (10k reamostragens de consultas, IC 95%) e os
  três recortes. ✅
- Notebooks 01–03: **pendentes**, e por último, só consumindo `results/`.
- **Aceite atingido**: tabela com os dois retrievers, significância pareada com
  correção, IC 95% por bootstrap e **quatro** recortes (o de seção do acórdão
  foi acrescentado, e não estava no plano original).
- Acrescentado além do previsto: **análise de poder estatístico**
  (`power_analysis.csv`), que responde se um resultado não significativo é
  ausência de efeito ou falta de amostra.

**Duas armadilhas encontradas ao rodar (ambas silenciosas):**

1. **O `ranx` lê os arquivos TREC com o encoding da plataforma**, e todo
   doc_id acentuado virava mojibake (`plenário` → `plenÃ¡rio`). Como qrels e
   runs sofriam a mesma corrupção, as métricas fechavam — só o cruzamento com
   os tamanhos de documento falhava, e o recorte por tercil saía **vazio**.
   Corrigido lendo os dois formatos em UTF-8.
2. **Os tercis de tamanho não podem sair dos percentis do corpus.** Os
   documentos relevantes são sistematicamente maiores que o acervo, e cortar
   pelo corpus deu grupos de **3/67/80** consultas. Passou a cortar pelos
   percentis da distribuição das consultas: 50/50/50.

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
| ~~`ranx`/numba incompatível com Python 3.13~~ | **Não se materializou** — tudo instala e roda em 3.13.7 (numba 0.67) |
| Offsets token→char com UTF-8 (tiktoken) | Decodificar bytes acumulados; teste com acentos |
| Encode denso lento (corpus agora é grande) | **Confirmado e resolvido com GPU**: 127 h em CPU vs ~10 h na RTX 5060 (fp16). Cache `.npy` evita reencode; rodar à noite |
| Janela do encoder menor que o chunk | **Materializou-se**: e5-base (512) truncaria 37% do conteúdo e enviesaria a comparação. Resolvido trocando para bge-m3 (1024) |
| Números publicados divergirem do que o código produz | **Materializou-se**: artigo diz 113.827 docs, código produz 12.880. Ver o achado de corpus |
| Relevância julgada no excerto, transferida ao acórdão | Discutir como limitação; é relevância em nível de documento (defensável) |

---

## 6. Definition of done global

1. ✅ `join_report.json` com match ≥ 90% e qrels preservados ≥ 90% — **98,7% e 99,69%**.
2. ✅ `results/corpus/segmenter_validation.json` — **92,2%** de acurácia, 0% de fallback.
3. 🟡 `results/experiments/<rodada>/tables/main_results.csv`: 5 estratégias × 2
   retrievers × 4 métricas — **metade pronta** (BM25); falta o denso.
4. 🟡 `significance.csv` com testes pareados corrigidos — pronto para o BM25.
5. 🟡 `slices_{query_type,doc_length,retriever}.csv` — prontos para o BM25.
6. ✅ `pytest` verde (**98 testes**); READMEs de reprodução atualizados.
7. ⬜ **Novo:** decisão do corpus oficial registrada, e números do artigo
   corrigidos de acordo.

**Situação em 07/09:** os itens 1, 2, 3, 4, 5 e 6 estão ✅ (o item 3 com 4 das 5
estratégias no denso; a quinta rodava quando a máquina desligou e foi retomada
do checkpoint). Falta o item 7, que depende da equipe.
