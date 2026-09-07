# PLANO — estado do projeto e o que fazer a seguir

**Documento vivo.** Comece por aqui se você vai pegar o projeto para rodar,
codar ou escrever. Atualize **acrescentando**, não apagando: a seção
[Histórico](#histórico-o-que-já-foi-feito) é o registro do que já foi decidido,
e apagá-la faz alguém redescobrir o mesmo problema daqui a um mês.

**Última atualização:** 07/09/2026 · por Leonardo Marques

---

## 1. Em uma página: onde o projeto está

| | |
|---|---|
| **Pergunta** | Chunking que respeita as macro-seções do acórdão melhora a recuperação, comparado a chunking fixo/recursivo? Sob quais condições? |
| **Corpus** | 12.880 acórdãos íntegros do TCU (2003–2023), 150 consultas e 2.219 qrels do JurisTCU |
| **Fases** | F0–F5 concluídas; **experimento 5 × 2 completo** |
| **Testes** | 115 passando |
| **Resposta curta à pergunta** | **Não melhora.** Nenhuma diferença entre estratégias é significativa, em nenhum dos dois retrievers |
| **Resultados significativos** | **1.** BM25 supera o retriever denso (p < 0,001). **2.** Descartar o relatório do índice melhora o nDCG@10 em **16,9%** (p = 0,001) |
| **Bloqueio nº 1** | 🔴 A equipe precisa decidir o corpus oficial: o artigo diz 113.827 documentos, o código produz 12.880 |

### A tabela principal (nDCG@10)

| Estratégia | BM25 | Denso (bge-m3) |
|---|---:|---:|
| structural_pred | **0,2526** | 0,1912 |
| structural_gold | 0,2521 | 0,1847 |
| fixed_1024_512 | 0,2510 | 0,2019 |
| fixed_512_256 | 0,2486 | **0,2055** |
| recursive_default | 0,2412 | 0,1967 |

**A ordem se inverte entre os retrievers**: as estruturais lideram no BM25 e
ficam por último no denso. Nenhuma dessas diferenças é significativa — mas a
inversão é consistente, e é evidência **contra** um efeito estável do chunking
estrutural.

---

## 2. O que a equipe precisa decidir (não dá para decidir sozinho)

### 🔴 DECISÃO 1 — Qual é o corpus oficial?

O artigo e o pôster dizem **113.827** documentos. O `ingest.py` produz
**12.880**. Não é bug: é uma mudança de escopo de agosto que não foi propagada
para os artefatos nem para o texto. Análise completa em
[docs/docsleo/branches/leo-f4-indexacao-e-docs/02-achado-corpus.md](docs/docsleo/branches/leo-f4-indexacao-e-docs/02-achado-corpus.md).

**Por que é urgente:** o trabalho agora tem um resultado **significativo**
(BM25 > denso). Um número significativo medido no corpus errado vai para o
artigo como afirmação forte — é o tipo de coisa que a banca cobra.

**Recomendação:** ficar com 12.880 e corrigir o artigo. O JurisTCU avalia sobre
16.045 documentos; 12.880 acórdãos íntegros é o análogo direto, mudando **uma
variável só** (o documento passa a ser o acórdão inteiro). Ir para 113.827
mudaria tamanho de documento *e* de coleção ao mesmo tempo, e custaria ~9 dias
de GPU.

**Responsável sugerido:** Igor (autor da F1/F2) + todos.

### 🟠 DECISÃO 2 — Quem corrige o artigo e o pôster?

Onze números do artigo mudam. Lista completa com "de → para" em
[07-numeros-para-o-artigo.md](docs/docsleo/branches/leo-f4-indexacao-e-docs/07-numeros-para-o-artigo.md).
Os principais: 113.827 → 12.880 documentos; mediana 7.347 → 11.426 tokens;
segmentador 92,7% → 92,2%; fallback 1,6% → 0,0%; Python 3.11 → 3.13.7.

Também é preciso **refazer a Figura 2** e **remover a afirmação** de que ~100k
documentos são "compatible with personal hardware and Google Colab" — não são
(9 dias de CPU nessa escala).

### 🟡 DECISÃO 3 — O que fazer com o resultado da hipótese?

A hipótese não se confirmou. Isso **não** é um problema para o TCC — o
`plano_tecnico.md` §7 já dizia que "um resultado nulo bem medido é um TCC
completo". Mas a equipe precisa decidir como a Introdução e a Conclusão vão
tratar isso. Sugestão em [§4](#4-o-que-o-artigo-pode-afirmar).

---

## 3. Próximos passos, por frente

Marque `[x]` quando concluir e **assine com seu nome**. Acrescente itens novos
no fim de cada lista.

### 3.1 Execução (precisa de máquina com GPU)

- [x] Ambiente, download dos datasets (6 GB), corpus montado — *Leo, 05/09*
- [x] Chunking: 2.200.767 chunks nas 5 estratégias — *Leo, 05/09*
- [x] BM25 nas 5 estratégias, reproduzido idêntico em duas rodadas — *Leo, 06/09*
- [x] Denso nas 4 primeiras estratégias — *Leo, 06/09*
- [x] Denso na `fixed_512_256` — *Leo, 07/09*. **Experimento completo: 5 × 2**
- [ ] Análise de sensibilidade da agregação: `sum_top_k` vs `max_pooling`
      (`python -m src.run_experiments --aggregation sum_top_k`) — barato, o
      cache já existe; **bom primeiro item para quem for pegar o projeto**
- [ ] Opcional: rodar com o `embeddinggemma-300m` (exige `hf auth login`) para
      ter um segundo modelo denso

### 3.1b 🏆 A frente mais promissora: filtragem por seção

Testado em 07/09 e **funcionou**: descartar os chunks do relatório melhora o
nDCG@10 em **16,9%** (p = 0,001) usando um terço do índice, e o ganho se mantém
com os spans **preditos** pelo segmentador (p = 0,017), não só com a estrutura
ouro. Detalhe em
[resultados/05-filtragem-por-secao.md](docs/docsleo/branches/leo-f4-indexacao-e-docs/resultados/05-filtragem-por-secao.md).

Foi exploratório, fora do `src/`. Para virar resultado do artigo:

- [ ] Reimplementar no pipeline como opção de indexação (`--secoes ...`), com testes
- [ ] Rodar no **BM25** — só testamos no denso
- [ ] Testar a variante **ponderada** (peso por seção em vez de corte binário),
      que talvez preserve o Recall@100, hoje 7% menor
- [ ] Efeito por tipo de consulta, sobretudo nas consultas reais de log
- [ ] Bootstrap de IC 95% e análise de poder

> Isto reformula a pergunta do trabalho de *"como cortar o documento?"*
> (resposta: tanto faz) para **"qual parte do documento indexar?"** — que tem
> resposta, com mecanismo medido antes da intervenção.

### 3.2 Análise e escrita

- [ ] Notebooks 01–03, consumindo só `results/` (sem cálculo pesado)
- [ ] Reescrever §Resultados do artigo com a tabela 5 × 2
- [ ] Acrescentar a Discussão sobre por que o BM25 vence (vocabulário jurídico
      técnico e recorrente favorece casamento lexical; o embedding de um chunk
      de ~770 tokens dilui o termo específico)
- [ ] Acrescentar as duas limitações novas: viés de coleção (só acórdãos que
      viraram jurisprudência) e viés de pool nos qrels do JurisTCU
- [ ] Ler o PDF do BR-TaxQA-R e confirmar a descrição que fazemos dele

### 3.3 Código (melhorias que dependem de aval)

- [ ] `ingest.py` gravar `n_tokens` no `corpus_docs.jsonl`, como manda o
      contrato do `plano_implementacao.md` §2 (hoje o `corpus_stats()` calcula
      e descarta). Contornado com cache, mas o certo é na fonte — *precisa do
      aval do Igor*
- [ ] `ingest.py` importar de `src/tokenization.py` em vez de chamar `tiktoken`
      direto — o plano pede tokenizer único centralizado

---

## 4. O que o artigo pode afirmar

Três resultados sustentados por evidência, e um achado de domínio.

**1. O BM25 supera o retriever denso, com significância forte.**

| Comparação (mesma estratégia) | p | BM25 vence / empata / perde |
|---|---:|---|
| structural_gold | **0,000005** | 83 / 25 / 42 |
| structural_pred | **0,000010** | 83 / 21 / 46 |
| fixed_1024_512 | **0,000793** | 81 / 22 / 47 |
| recursive_default | **0,002189** | 80 / 23 / 47 |

Coerente com `pereira2026jua` (baselines lexicais competitivas em RI jurídica
em português) e com o JurisTCU, onde os BERT-based foram os piores.

**2. A estratégia de chunking não altera a recuperação — em nenhum retriever.**
BM25: 10 pares, **0 significativos** (menor p = 0,097). Denso: 6 pares,
**0 significativos** (menor p = 0,084). Com análise de poder declarada: 150
consultas detectam a partir de ~0,017–0,028 em nDCG@10, e as diferenças
observadas vão de 0,001 a 0,017.

**3. O erro do segmentador não custa desempenho.**
`structural_gold` × `structural_pred`: p = 0,827 (BM25) e 0,283 (denso), com o
**predito** à frente no BM25. 97 empates em 150 consultas. Um segmentador por
regras com 92,2% de acurácia entrega o mesmo que a estrutura ouro — a conclusão
prática mais útil, e a ablação que o BR-TaxQA-R não tem.

**4. Achado de domínio: a relevância mora na fundamentação.**
O voto ocupa 22,8% dos caracteres do acórdão e concentra **72,0%** do conteúdo
julgado relevante (3,2x); o relatório tem 69,9% do texto e só 25,7% da
relevância. A posição mediana do trecho relevante é a **79%** do documento.
Mas **ambos os retrievers recuperam predominantemente pelo relatório** (65–74%)
— acham o termo onde há mais texto, não onde há mais relevância.

---

## 5. Como rodar o projeto (do zero)

```bash
git clone https://github.com/igormamus1703/tcc-segundo-semestre.git
cd tcc-segundo-semestre

# 1. ambiente (fora de pasta sincronizada, se o repo estiver numa)
python -m venv .venv && .venv\Scripts\activate
pip install -r juris-chunking/requirements.txt

# 2. dados (~6 GB, retomável)
python scripts/download_datasets.py juristcu tcu_acordaos

# 3. corpus e validação
cd juris-chunking
python -m src.ingest                 # ~30 min, lê 6 GB de CSV
python -m src.segmenter.validate
pytest -q                            # 115 passando

# 4. chunking (~50 min, gera 6 GB)
python -m src.chunkers.run --strategy all

# 5. experimento
python -m src.run_experiments --strategy all --retriever bm25    # ~25 min
python -m src.run_experiments --strategy all --retriever dense   # ~10 h de GPU
python -m src.evaluate                                           # tabelas
python -m src.plots                                              # figuras
```

Ou tudo de uma vez, com orçamento de tempo e log datado:

```powershell
.\scripts\rodada_completa.ps1 -MaxHoras 5
```

**Requisitos reais:** GPU obrigatória para o denso (em CPU são 127 h contra
~10 h numa RTX 5060), ~15 GB de disco livre, Python ≥ 3.13.

**O único passo manual do projeto:** usar o `embeddinggemma-300m` exige conta no
Hugging Face e `hf auth login`. O default (`bge-m3`) não exige nada.

---

## 6. Onde as coisas ficam

```
├── PLANO.md                    ← você está aqui
├── README.md                   fluxo de trabalho obrigatório da equipe
├── plano_tecnico.md            arquitetura, stack, cronograma (referência)
├── plano_implementacao.md      status fase a fase — "o que fazer agora"
├── juris-chunking/             todo o código
├── results/
│   ├── corpus/                 caracterização do corpus (muda com o corpus)
│   └── experiments/            uma pasta datada por rodada, com manifesto
└── docs/
    ├── docsleo/                caderno de bordo do Leo
    ├── docsigor/               (a criar)
    ├── docsjoao/               (a criar)
    └── docsfelipe/             (a criar)
```

**Cada integrante mantém sua pasta em `docs/`** e anota lá o que fez, decidiu e
mediu. O padrão está no [README.md](README.md#fluxo-de-trabalho-obrigatório):
branch → testar → anotar → merge.

---

## 7. Histórico: o que já foi feito

Resumo do que está decidido, para ninguém refazer. O detalhe está em
[docs/docsleo/](docs/docsleo/).

| Quando | O quê | Onde está documentado |
|---|---|---|
| 18/08 | Decisão de corpus: acórdãos íntegros do TCU + qrels do JurisTCU | `plano_implementacao.md` §0 |
| 24/08 | F1 (ingestão) e F2 (segmentador) — Igor | `plano_implementacao.md` |
| 24/08 | F3 (5 chunkers), com bug de offset do LangChain corrigido | docstring de `chunkers/recursive.py` |
| 05/09 | Ambiente em Python 3.13 (o risco do `ranx`/numba não se materializou) | [01-ambiente-setup](docs/docsleo/branches/leo-f4-indexacao-e-docs/01-ambiente-setup.md) |
| 05/09 | **Achado:** corpus do código (12.880) ≠ do artigo (113.827) | [02-achado-corpus](docs/docsleo/branches/leo-f4-indexacao-e-docs/02-achado-corpus.md) |
| 05/09 | F4 e F5 implementadas (BM25, denso, avaliação, recortes) | [06-implementacao-f4](docs/docsleo/branches/leo-f4-indexacao-e-docs/06-implementacao-f4.md) |
| 06/09 | As 8 citações do artigo verificadas no arXiv — nenhuma fantasma | [04-referencias-verificadas](docs/docsleo/branches/leo-f4-indexacao-e-docs/04-referencias-verificadas.md) |
| 06/09 | Embedder escolhido pela **janela de contexto**, não pelo ranking | [05-modelos-embedding](docs/docsleo/branches/leo-f4-indexacao-e-docs/05-modelos-embedding.md) |
| 06/09 | **Achado:** 72% da relevância está na fundamentação (22,8% do texto) | [03-analise-do-dominio](docs/docsleo/branches/leo-f4-indexacao-e-docs/03-analise-do-dominio.md) |
| 06/09 | BM25 nas 5 estratégias — primeiro número | [resultados/01-bm25](docs/docsleo/branches/leo-f4-indexacao-e-docs/resultados/01-bm25.md) |
| 06/09 | Denso, 3 de 5: a ordem inverte, e o BM25 vence com significância | [resultados/04-denso-parcial](docs/docsleo/branches/leo-f4-indexacao-e-docs/resultados/04-denso-parcial.md) |
| 07/09 | **Achado:** descartar o relatório do índice dá +16,9% de nDCG@10 (p = 0,001) | [resultados/05-filtragem-por-secao](docs/docsleo/branches/leo-f4-indexacao-e-docs/resultados/05-filtragem-por-secao.md) |
| 07/09 | **Experimento fechado:** 5 estratégias × 2 retrievers, com a inversão completa | [resultados/06-final-5x2](docs/docsleo/branches/leo-f4-indexacao-e-docs/resultados/06-final-5x2.md) |
| 07/09 | Branch `leo/f4-indexacao-e-docs` mergeada na `main` | [README da branch](docs/docsleo/branches/leo-f4-indexacao-e-docs/README.md) |

### Coisas que já foram tentadas e NÃO funcionaram

Para ninguém repetir:

| Tentativa | Resultado |
|---|---|
| `gte-multilingual-base` como embedder | Quebra com `device-side assert` do CUDA, em fp16 e fp32 |
| ONNX Runtime para acelerar o encode | `optimum` rebaixa o `transformers` e quebra o `sentence-transformers` |
| `torch.compile` + TF32 | 0,99x — sem ganho (já estamos em fp16) |
| Deduplicar chunks entre estratégias | 0,4% de redundância — não compensa |
| Encode denso em CPU | 4,8 chunks/s → 127 h. Inviável |
| `multilingual-e5-base` (janela 512) | Truncaria 83% dos chunks e enviesaria a comparação |
