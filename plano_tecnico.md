# Plano Técnico — Segmentação Estrutural de Acórdãos para RI Jurídica

Documento interno da equipe. Não é o entregável do professor.

> **Status em 28/09/2026 — leia antes de usar este documento.**
> Este é o plano de referência (arquitetura, stack, cronograma) e **não é
> atualizado a cada execução**. Para o panorama e os próximos passos, veja o
> **`PLANO.md`** na raiz; para o detalhe fase a fase, o
> **`plano_implementacao.md`**, que substitui este documento onde houver
> conflito.
>
> Em resumo: **F0–F5 concluídas** e o experimento rodado nos dois retrievers.
> A hipótese **não se confirmou** — 1 de 20 pares entre estratégias tem
> p < 0,05, e ele aponta *contra* a hipótese. O resultado mais sólido da F5 é
> que o **BM25 supera o retriever denso** nas cinco estratégias (p < 0,01).
>
> **F6 (28/09), na branch `leo/f6-secoes-e-fusao`, ainda não mergeada.** Ela
> acrescenta uma fase que não estava neste plano e **muda a pergunta do
> trabalho**: de *"como cortar o documento?"* (resposta nula, e ela se
> sustentou) para *"qual parte do documento indexar?"* — a fundamentação; o
> relatório atrapalha. Descartar o relatório do índice sobe o nDCG@10 de
> 11% a 17% no BM25 (as cinco estratégias, p entre 0,00025 e 0,003), e a
> melhor configuração chega a **0,3215 contra 0,2486 do baseline (+29,3%)**.
> Ver `RESULTADOS-F6.md` na raiz.
>
> Três escolhas deste documento mudaram por medição — o embedder, o
> cronograma e a própria lista de estágios do pipeline —, e estão marcadas
> abaixo.

---

## 1. Arquitetura do código

```
juris-chunking/
├── configs/
│   ├── chunkers.yaml          # parâmetros de cada estratégia
│   └── models.yaml            # embedders e retrievers
├── data/
│   ├── raw/                   # JurisTCU / JUÁ baixados (não versionar)
│   ├── interim/               # documentos normalizados
│   ├── processed/             # chunks serializados por estratégia
│   └── annotations/           # amostra validada manualmente (80 docs)
├── src/
│   ├── ingest.py              # download + normalização + EDA
│   ├── segmenter/
│   │   ├── rules.py           # regex das macro-seções do acórdão
│   │   ├── segment.py         # aplica regras, retorna spans rotulados
│   │   └── validate.py        # mede acurácia contra a amostra anotada
│   ├── chunkers/
│   │   ├── base.py            # interface Chunker.chunk(doc) -> List[Chunk]
│   │   ├── fixed.py           # janela deslizante, tamanho/stride param.
│   │   ├── recursive.py       # RecursiveCharacterTextSplitter
│   │   └── structural.py      # respeita fronteiras das macro-seções
│   ├── indexing/
│   │   ├── lexical.py         # BM25
│   │   └── dense.py           # sentence-transformers + FAISS (+ cache por subconjunto, F6)
│   ├── retrieval.py           # busca + agregação chunk->documento
│   ├── evaluate.py            # nDCG@10, MRR@10, MAP@10, Recall@100
│   ├── analysis.py            # bootstrap, testes pareados, recortes
│   ├── sections.py            # F6: recorte/ponderação por macro-seção + controle
│   ├── fusion.py              # F6: fusão de rankings (RRF, soma normalizada)
│   ├── tuning.py              # F6: escolha de configuração por validação cruzada
│   ├── experiment.py          # rastreabilidade: pasta datada + manifesto + log
│   ├── plots.py               # figuras do artigo, com rodapé de contexto
│   └── run_experiments.py     # orquestrador das rodadas
├── notebooks/
│   ├── 01_eda_corpus.ipynb
│   ├── 02_validacao_segmentador.ipynb
│   └── 03_resultados.ipynb
├── results/
│   ├── runs/                  # arquivos TREC run
│   └── tables/
├── tests/
├── requirements.txt
└── README.md
```

### Contrato entre módulos

```python
@dataclass
class Chunk:
    chunk_id: str
    doc_id: str          # essencial: é a chave da agregação
    text: str
    section: str | None  # "ementa" | "relatorio" | "fundamentacao" | "dispositivo" | None
    start: int
    end: int
```

Todo chunker devolve `List[Chunk]`. `section` é `None` para fixo e recursivo. Isso
permite que a análise por seção seja feita **também** nas baselines (você pode
verificar de qual seção um chunk fixo veio, mapeando pelo offset). Esse detalhe
vale uma seção inteira de discussão no TCC.

---

## 2. Pipeline em cinco estágios

**E1 — Ingestão e caracterização (`ingest.py`)**
Baixa o corpus, normaliza encoding, remove artefatos de OCR/HTML, produz
estatísticas: tokens por documento (mediana, p90, p99), presença de marcadores
seccionais, cobertura dos qrels.

> **Gate de viabilidade.** Se a mediana ficar abaixo de ~1000 tokens, a estratégia
> de chunking não terá efeito mensurável. Nesse caso, migrar para acórdãos
> íntegros (base do TCU ou DataJud/CNJ). Essa decisão precisa estar tomada até o
> fim da Semana 3, não depois.

**E2 — Segmentador estrutural (`segmenter/`)**
Regras sobre marcadores tipográficos: `EMENTA`, `RELATÓRIO`, `VOTO`,
`ACÓRDÃO`, `É o relatório`, `Ante o exposto`, `Isto posto`, numeração romana.
Saída: lista de spans rotulados. Fallback quando nenhuma marca é encontrada:
documento inteiro rotulado como `indefinido` — e você **reporta a taxa de
fallback**, que é um resultado em si.

**E3 — Chunkers (`chunkers/`)**
Três estratégias, mesma interface:
- `fixed`: janela deslizante. Use 512 tokens/stride 256 **e** 1024/512, para
  comparar com o BR-TaxQA-R, que usou 2048/1024.
- `recursive`: `RecursiveCharacterTextSplitter` com separadores jurídicos.
- `structural`: nunca cruza fronteira de macro-seção; se uma seção exceder o
  limite máximo, subdivide internamente e propaga o rótulo.

**E4 — Indexação e recuperação (`indexing/`, `retrieval.py`)**
Dois retrievers: BM25 (léxico) e denso. Para 16k documentos, FAISS `IndexFlatIP`
resolve — não precisa de ANN aproximado.

Agregação chunk→documento: **max-pooling** como padrão.
```python
doc_score = max(chunk_scores_of_doc)
```
Implemente também `sum-top-k` (k=3) como análise de sensibilidade. Se as duas
concordarem, você reporta uma linha dizendo isso e blinda a metodologia.

**E5 — Avaliação e análise (`evaluate.py`, `analysis.py`)**
Métricas via `ranx`, que já traz teste pareado com correção para comparações
múltiplas. Recortes obrigatórios: por tipo de consulta, por tamanho de documento
(tercis), por retriever.

---

## 3. Stack

| Função | Escolha | Nota |
|---|---|---|
| Dataset | `datasets` (HuggingFace) | JurisTCU está em `LeandroRibeiro/JurisTCU` |
| Tokenização | `tiktoken` ou tokenizer do próprio modelo | seja consistente e declare qual |
| Chunking baseline | `langchain-text-splitters` | só o splitter, não o framework inteiro |
| BM25 | `bm25s` (rápido) ou `rank_bm25` | `bm25s` é ordens de magnitude mais rápido |
| Denso | `sentence-transformers` | GPU com `torch+cu130`; fp16 dá ~3x sobre fp32 e ~60x sobre CPU |
| Índice vetorial | `faiss-cpu` | brute force basta nesta escala; o custo está no encode, não na busca |
| Métricas | `ranx` | nDCG/MRR/MAP + significância pareada |
| Estatística | `scipy`, bootstrap manual | |
| Gráficos | `matplotlib` | |

**Modelos de embedding a testar** (2 ou 3, não mais):
- Um modelo compacto adaptado ao português — o MTEB-BR aponta que modelos abertos
  e auto-hospedáveis alcançam o topo, sem precisar de API comercial.
- Um multilíngue forte de referência.
- Opcionalmente `RoBERTaLexPT` (jurídico PT) — mas atenção: é um encoder MLM, não
  um bi-encoder treinado para recuperação. Só use se for fazer fine-tune, senão
  o desempenho será enganosamente ruim e alguém na banca vai apontar isso.

> **Decidido por medição (06/09):** o critério que acabou dominando a escolha
> **não** foi a posição no ranking, e sim a **janela de contexto**. Um encoder
> de 512 tokens trunca 83% dos nossos chunks e descarta 37% do conteúdo — e,
> pior, atinge as estratégias de forma desigual: só a `fixed_512_256` caberia
> inteira, o que lhe daria vantagem artificial e invalidaria a comparação.
>
> | Modelo | Janela | Situação |
> |---|---|---|
> | **`BAAI/bge-m3`** | 1024 (nativa 8192) | **Adotado como default.** Truncamento zero, Apache-2.0, sem gate |
> | `google/embeddinggemma-300m` | 2048 | Melhor no MTEB-BR (13º de 93, 308M), mas **gated**: exige `hf auth login` |
> | `intfloat/multilingual-e5-base` | 512 | Rebaixado a análise de sensibilidade — a janela pequena enviesa a comparação |
> | `Alibaba-NLP/gte-multilingual-base` | 8192 | Descartado: o código remoto quebra com assert de CUDA no stack atual |
>
> Detalhes e medições em
> `docs/docsleo/branches/leo-f4-indexacao-e-docs/05-modelos-embedding.md`.

Não use API paga. Custo, reprodutibilidade e o fato de que a nota não sobe por isso.

---

## 4. Cronograma (16 semanas, a partir de 17/08)

| Sem. | Período | Entrega | Risco |
|---|---|---|---|
| 1 | 17–23/08 | **Documento de planejamento entregue.** Repo criado, ambiente Python. | — |
| 2 | 24–30/08 | Leitura do bloco A (ver §5). Corpus baixado. | Acesso ao dataset |
| 3 | 31/08–06/09 | **EDA concluída. Gate de viabilidade decidido.** | **Alto — decisão de corpus** |
| 4 | 07–13/09 | Segmentador v1 (regras). Amostra de 80 docs anotada. | Ambiguidade das marcas |
| 5 | 14–20/09 | Validação do segmentador. Acurácia reportada. | Acurácia baixa → iterar regras |
| 6 | 21–27/09 | Três chunkers implementados e testados. | Baixo |
| 7 | 28/09–04/10 | Pipeline BM25 ponta a ponta. **Primeiro número na tabela.** | Agregação chunk→doc |
| 8 | 05–11/10 | **Poster + apresentação.** Pipeline denso implementado. | Conflito de agenda |
| 9 | 12–18/10 | Rodadas completas: 3 chunkers × 2 retrievers. | Tempo de indexação |
| 10 | 19–25/10 | Análise por recorte (tipo de consulta, tamanho, retriever). | — |
| 11 | 26/10–01/11 | Bootstrap e significância. Tabela final fechada. | Resultados nulos |
| 12 | 02–08/11 | Redação: Metodologia + Resultados. | — |
| 13 | 09–15/11 | Redação: Introdução + Trabalhos Relacionados. | — |
| 14 | 16–22/11 | Redação: Discussão + Conclusão. Revisão do orientador. | Prazo do orientador |
| 15 | 23–29/11 | Ajustes. Repositório limpo e documentado. | — |
| 16 | 30/11–06/12 | **Entrega final.** Ensaio da defesa. | — |

**Marcos duros:** Semana 3 (viabilidade), Semana 7 (primeiro número), Semana 11
(tabela fechada). Se algum atrasar mais de uma semana, corte escopo — comece pelo
segundo modelo de embedding, que é o mais dispensável.

> **Situação real em 07/09:** os marcos vieram **muito adiantados**.
> Viabilidade decidida em 18/08 (Semana 1), F0–F3 fechadas em 24/08, o
> **primeiro número em 06/09** (marco da Semana 7) e a **tabela fechada nos dois
> retrievers em 07/09** (marco da Semana 11). O gargalo deixou de ser código ou
> compute: é a **decisão do corpus oficial**, que é da equipe, e a redação.

**Fora de escopo, explicitamente:** ColBERT / late interaction, fine-tuning de
retriever, avaliação de geração (RAGAS), rotulagem retórica em nível de sentença.
Declare isso no documento como trabalho futuro — protege vocês de escopo
crescente e mostra maturidade.

---

## 5. Roteiro de leitura

### Bloco A — Fundação (ler nas semanas 1–2, obrigatório)

1. **de Martim, H. (2026).** *Beyond Probabilistic Similarity: Structural,
   Temporal, and Causal Limitations of RAG in the Legal Domain.* arXiv:2606.09724.
   → Define cegueira mereológica, cegueira diacrônica e opacidade causal. É o
   vocabulário que a banca vai cobrar. **Leia primeiro.**

2. **de Martim, H. (2025).** *An Ontology-Driven Graph RAG for Legal Norms.*
   arXiv:2505.00039 (também em IOS Press, FAIA251598).
   → O trabalho estrutural sobre normas brasileiras. É o que vocês NÃO estão
   refazendo — precisam saber explicar a diferença.

3. **Domingos Júnior, J. et al. (2025).** *BR-TaxQA-R.* arXiv:2505.15916.
   → Comparou estratégias de segmentação em direito tributário BR com RAGAS.
   Contém a evidência contrária à hipótese de vocês. Leiam com atenção à seção
   de segmentação.

4. **JurisTCU.** arXiv:2503.08379.
   → 16.045 documentos, 150 consultas com julgamentos de relevância. Provável
   corpus principal.

### Bloco B — Metodologia e baselines (semanas 3–5)

5. **JUÁ: A Benchmark for IR in Brazilian Legal Text Collections.** arXiv:2604.06098.
   → Protocolo unificado; consolida JurisTCU, NormasTCU, Ulysses-RFCorpus,
   BR-TaxQA. Alternativa ou complemento ao JurisTCU.

6. **MTEB-BR.** arXiv:2607.04581.
   → Justifica a escolha do embedder com dado nativo em português. Usem para
   fundamentar a seleção de modelos — é um argumento forte na banca.

7. **Garcia, E. et al. (2024).** *RoBERTaLexPT.* PROPOR 2024.
   → Modelo jurídico em português, introduz o benchmark PortuLex.

8. **Lewis, P. et al. (2020).** *Retrieval-Augmented Generation.* NeurIPS.
   → Citação canônica de RAG. Leitura rápida, citação obrigatória.

9. **Karpukhin, V. et al. (2020).** *Dense Passage Retrieval.* EMNLP.
   → Fundamento do retriever denso.

### Bloco C — Contexto e trabalho futuro (leitura leve)

10. **Legal RAG Bench.** arXiv:2603.01710.
    → Achado relevante: a recuperação é o principal determinante do desempenho,
    e muitos erros atribuídos a alucinação são na verdade falhas de recuperação.
    **Isso justifica por que vocês avaliam só recuperação e não geração.** Use
    esse argumento se alguém perguntar.

11. **LegalBench-BR.** arXiv:2604.18878.
    → Contexto de NLP jurídico brasileiro (classificação, não recuperação).

12. **Khattab & Zaharia (2020).** *ColBERT.* SIGIR.
    → Só para a seção de trabalhos futuros.

### A verificar antes de citar

- O trabalho sobre o BGB alemão (chunking estrutural em Civil Law).
- A dissertação da UFMS sobre segmentação de acórdãos com supervisão fraca.
- Literatura de *rhetorical role labeling* em decisões judiciais (há trabalhos
  em inglês e hindi; o SemEval-2023 Task 6 / LegalEval é a pista mais provável).

**Nenhum destes entra na bibliografia sem que alguém tenha o PDF na mão.**
Citação fantasma em TCC é o tipo de erro que a banca encontra e não perdoa.

---

## 6. Divisão de trabalho (se for dupla)

| Pessoa A | Pessoa B |
|---|---|
| Segmentador + validação da amostra | Chunkers + indexação |
| Análise por recorte | Pipeline de avaliação e estatística |
| Trabalhos Relacionados + Introdução | Metodologia + Resultados |

Ambos: EDA na semana 3, e ambos precisam saber explicar a tabela final.

---

## 6-bis. O estágio que não estava no plano: seleção de conteúdo (F6)

O pipeline original tem cinco estágios: ingestão → segmentação → chunking →
indexação → avaliação. A F6 acrescenta um **sexto**, que roda entre a
segmentação e a indexação:

```
segmentação → [SELEÇÃO DE CONTEÚDO] → chunking → indexação
                      │
                      ├─ recorte binário   (--secoes): só indexa as seções pedidas
                      ├─ ponderação        (--pesos):  desconta o score por seção
                      └─ controle pareado  (--amostra-igual-a): mesmo tamanho, sorteado
```

E um estágio opcional depois da recuperação:

```
indexação → busca → [FUSÃO DE RANKINGS] → agregação chunk→documento → avaliação
                            │
                            ├─ RRF (posição) e soma normalizada (magnitude)
                            └─ peso por validação cruzada, ou peso igual (sem parâmetro)
```

Por que não estava no plano: ele nasceu de uma **medição** da F5 — a
fundamentação ocupa 22,8% do texto e concentra 72,0% da relevância, mas os
retrievers recuperam 65–74% pelo relatório. O plano original supunha que a
variável interessante era *o tamanho do chunk*; a medição mostrou que é *que
parte do documento entra no índice*.

**Contrato do novo estágio.** A seção de um chunk é resolvida pelo rótulo
quando ele existe (estratégias estruturais) e pelo **offset** contra os spans
do documento quando não existe (estratégias fixa e recursiva). É isso que faz
a seleção de conteúdo valer para as cinco estratégias, e não só para as duas
que conhecem a estrutura — e é uma extensão natural do contrato `Chunk` da
§1, que já previa o offset para exatamente este tipo de análise.

---

## 7. Critérios de sucesso

O TCC é bem-sucedido se, ao final, existir:

1. Um segmentador de acórdãos com acurácia medida e reportada.
2. Uma tabela comparando 3 estratégias × 2 retrievers em nDCG@10, MRR@10, MAP@10.
3. Testes de significância pareados — não só médias.
4. Três recortes analíticos respondendo "sob quais condições".
5. Repositório reprodutível.

> **Situação em 07/09 — os cinco critérios estão atendidos:**
> 1. ✅ Segmentador com **92,2%** de acurácia por caractere e **0%** de fallback,
>    validado contra os spans ouro de todo o corpus.
> 2. ✅ Tabela com **5** estratégias × 2 retrievers (o plano pedia 3) e quatro
>    métricas.
> 3. ✅ Significância pareada com correção para comparações múltiplas —
>    **mais** análise de poder estatístico, que não estava previsto.
> 4. ✅ **Quatro** recortes: tipo de consulta, tamanho de documento, retriever e
>    seção do acórdão (este último não estava previsto).
> 5. ✅ Cada rodada gera manifesto com commit, hardware, versões e tempos; o
>    BM25 foi reproduzido idêntico em duas execuções independentes.
>
> A hipótese não se confirmou, o que o §7 já previa: *"Nada disso exige que a
> hipótese se confirme."*
>
> **Atualização de 28/09 (F6).** Os cinco critérios continuam atendidos, e
> três foram superados:
> - critério 2: a tabela principal passou a ter **oito condições**
>   experimentais, não só estratégia × retriever;
> - critério 3: além da significância pareada com correção e da análise de
>   poder, a F6 acrescentou **um controle pareado** (índice do mesmo tamanho,
>   sorteado) e **validação cruzada por consulta** para escolher configuração
>   sem usar o conjunto de avaliação;
> - critério 5: a suíte foi de 115 para **182 testes**, e a avaliação é
>   byte-idêntica ao ser reexecutada.
>
> E o trabalho deixou de depender de um resultado nulo: **a segunda pergunta,
> derivada da primeira, tem resposta positiva e significativa** (+29,3% de
> nDCG@10).

**Nada disso exige que a hipótese se confirme.** Um resultado nulo bem medido,
com recortes que mostram onde cada estratégia ganha, é um TCC completo. O que
a F6 mostrou é que um resultado nulo bem medido também **rende uma pergunta
melhor**: foi medindo *por que* o chunking não importava que descobrimos o que
importa.
