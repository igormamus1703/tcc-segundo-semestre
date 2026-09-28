# PLANO — estado do projeto e o que fazer a seguir

**Documento vivo.** Comece por aqui se você vai pegar o projeto para rodar,
codar ou escrever. Atualize **acrescentando**, não apagando: a seção
[Histórico](#histórico-o-que-já-foi-feito) é o registro do que já foi decidido,
e apagá-la faz alguém redescobrir o mesmo problema daqui a um mês.

**Última atualização:** 28/09/2026 · por Leonardo Marques

---

## 1. Em uma página: onde o projeto está

| | |
|---|---|
| **Pergunta 1 (original)** | Chunking que respeita as macro-seções do acórdão melhora a recuperação, comparado a chunking fixo/recursivo? |
| **Pergunta 2 (derivada, 28/09)** | Se *como* cortar não importa, **qual parte** do documento indexar? |
| **Corpus** | 12.880 acórdãos íntegros do TCU (2003–2023), 150 consultas e 2.219 qrels do JurisTCU |
| **Fases** | F0–F6 concluídas e mergeadas na `main` |
| **Testes** | 191 passando · resultado auditado contra 10 ameaças de validade |
| **Resposta à pergunta 1** | **Não melhora.** Nenhuma diferença entre estratégias é significativa — e isso agora vale em **dois** pontos de operação diferentes |
| **Resposta à pergunta 2** | **A fundamentação. O relatório atrapalha.** Descartá-lo do índice melhora o nDCG@10 em 11–17% no BM25 e 12–28% no denso, nas cinco estratégias |
| **Melhor configuração** | recorte + fusão BM25/denso: **nDCG@10 = 0,3215**, contra 0,2486 do baseline — **+29,3%**, p < 0,00001, e **sem hiperparâmetro** |
| **Bloqueio nº 1** | 🔴 A equipe precisa decidir o corpus oficial: o artigo diz 113.827 documentos, o código produz 12.880 |

### A tabela principal (nDCG@10), índice completo — F5

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

### A tabela nova (nDCG@10), sem o relatório no índice — F6, 28/09

| Estratégia | BM25 | Δ | Denso | Δ | **controle: −67% aleatório** |
|---|---:|---:|---:|---:|---:|
| **fixed_512_256** | **0,2904** | +16,8% | **0,2627** | +27,8% | 0,2260 (−9,1%) |
| structural_gold | 0,2835 | +12,4% | 0,2167 | +17,3% | 0,2177 (−13,6%) |
| structural_pred | 0,2835 | +12,3% | 0,2147 | +12,3% | 0,2210 (−12,5%) |
| fixed_1024_512 | 0,2790 | +11,2% | 0,2292 | +13,5% | 0,2305 (−8,2%) |
| recursive_default | 0,2764 | +14,6% | 0,2351 | +19,5% | 0,2006 (−16,8%) |

As cinco melhoram, todas significativas no BM25 (p = 0,00025 a 0,003). **A
coluna do controle é o que sustenta o achado:** um índice do mesmo tamanho,
sorteado ao acaso, **piora** — então o ganho vem da estrutura do acórdão, não
de ter um índice menor.

### A configuração recomendada

Três pontos na curva de custo × qualidade, e o artigo deve apresentar os três:

| Configuração | nDCG@10 | MRR@10 | MAP@10 | R@100 | custo |
|---|---:|---:|---:|---:|---|
| BM25, índice completo (baseline F5) | 0,2486 | 0,5186 | 0,0963 | 0,4709 | — |
| BM25 **sem o relatório** | 0,2904 | 0,5889 | 0,1190 | 0,4993 | **um** índice, 1/3 do tamanho |
| sem o relatório **+ fusão (CV)** | 0,3160 | **0,6058** | 0,1330 | 0,5259 | dois índices de 1/3 |
| **fusão das 4 condições, peso igual** | **0,3215** | 0,6000 | **0,1402** | **0,5479** | quatro buscas por consulta |
| | **+29,3%** | +15,7% | **+45,6%** | **+16,4%** | |

`fixed_512_256`, p < 0,00001 com Bonferroni sobre 28 pares. **Nenhuma métrica
piora.** A melhor configuração funde quatro rankings com **peso igual** — ou
seja, **não tem hiperparâmetro para ajustar**, e por isso dispensa a validação
cruzada que a versão ponderada exige. As duas empatam (p = 0,338). Detalhe em
[docs/docsleo/branches/leo-f6-secoes-e-fusao/](docs/docsleo/branches/leo-f6-secoes-e-fusao/)
e resumo para apresentação em [RESULTADOS-F6.md](RESULTADOS-F6.md).

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

**Atualização de 28/09:** a decisão ficou mais fácil. Com a F6, o trabalho tem
um resultado nulo bem medido **e** uma intervenção que melhora o nDCG@10 em
27%. A sugestão é enquadrar assim: a pergunta sobre *granularidade* do chunk
tem resposta nula e bem medida; a pergunta sobre *seleção de conteúdo* — que
nasceu da primeira — tem resposta positiva e significativa. O trabalho não
"deu errado e a gente achou outra coisa": a segunda pergunta só existe porque
a primeira foi respondida com cuidado.

### 🟠 DECISÃO 4 — Revisar a F6, já mergeada (nova)

A branch `leo/f6-secoes-e-fusao` foi **mergeada em 28/09** com 191 testes
verdes, todos os artefatos e uma auditoria de validade. O merge seguiu o
mesmo critério da branch anterior: ela só **acrescenta** módulos e rodadas,
sem tocar em `ingest.py`, `segmenter/` ou `chunkers/`.

**O que ainda precisa da equipe é a revisão do conteúdo**, não do código: a
F6 muda a tese do artigo. Checklist e pontos de atenção no
[README da branch](docs/docsleo/branches/leo-f6-secoes-e-fusao/README.md);
resumo para a orientação em [RESULTADOS-F6.md](RESULTADOS-F6.md).

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
- [x] Análise de sensibilidade da agregação: `sum_top_k` vs `max_pooling` —
      *Leo, 28/09*. O `max_pooling` ganha em 4 de 5; o default fica, agora com
      evidência. Rodada `20260928-1707_bm25_sec_sumtopk`
- [ ] Opcional: rodar com o `embeddinggemma-300m` (exige `hf auth login`) para
      ter um segundo modelo denso

### 3.1b ✅ A frente mais promissora, agora fechada: filtragem por seção

**Concluída em 28/09** na branch `leo/f6-secoes-e-fusao`. O que era um script
exploratório virou opção de pipeline, rodou nos dois retrievers e nas cinco
estratégias, e passou por um controle.

- [x] Reimplementar no pipeline como opção de indexação (`--secoes ...`), com
      testes — *Leo, 28/09*. Reproduz o exploratório: 95.300 chunks, idêntico
- [x] Rodar no **BM25** — *Leo, 28/09*. **+11,2% a +16,8%, as cinco
      significativas** (p = 0,00025 a 0,003)
- [x] Rodar nas **cinco** estratégias, não só nas estruturais — *Leo, 28/09*.
      Nas fixas/recursiva a seção vem do offset do chunk
- [x] Testar a variante **ponderada** — *Leo, 28/09*. **Negativa:** satura no
      corte binário e não preserva o recall. Descartada, com o motivo medido
- [x] Efeito por tipo de consulta — *Leo, 28/09*. **+24,1% nas consultas reais
      de log**, +25,7% e +30,1% nas sintéticas: o ganho não vem das fáceis
- [x] Bootstrap de IC 95% e análise de poder — *Leo, 28/09*
- [x] 🆕 **Controle pareado por amostra aleatória** — *Leo, 28/09*. Não estava
      previsto e é o item mais importante da lista: descartar 2/3 do índice ao
      acaso **piora** o nDCG@10; escolhendo o relatório, melhora. Mesmo tamanho
      de índice, efeitos opostos
- [x] 🆕 **Fusão híbrida BM25 + denso**, com peso por validação cruzada —
      *Leo, 28/09*. +4,4% a +8,7%, e **soma com o recorte**: 0,3160 na melhor
      configuração

> A pergunta do trabalho deixa de ser só *"como cortar o documento?"*
> (resposta medida: tanto faz) e ganha uma segunda metade com resposta:
> **"qual parte do documento indexar?"** — a fundamentação; o relatório
> atrapalha. Mecanismo medido antes da intervenção, ganho significativo, e
> controle que descarta a explicação trivial.

### 3.1c O que ficou aberto depois da F6

- [ ] **Chunk com contexto de seção**: prefixar cada chunk com o nome da sua
      seção antes de encodar (`"[voto] …"`). Exige reencode, ~10 h de GPU
- [ ] **Reranking com cross-encoder** no top-100. Caro, mas é o que mais rende
      em RI
- [ ] **Expansão de consulta** (docT5query). O JurisTCU mediu +47%. Fora do
      escopo declarado; é o item mais forte de trabalhos futuros
- [ ] **Critério de densidade informativa** independente da estrutura (tamanho
      de sentença, densidade de termos jurídicos). A auditoria mostrou que o
      efeito acompanha a **densidade de relevância**, e não o relatório em si;
      falta a versão que não precisa segmentar o documento. Seria a
      contribuição mais geral do trabalho
- [ ] **Consultas dirigidas a fatos do caso concreto**, para testar se o
      recorte inverte de sinal nelas. É a limitação do §4 da auditoria, e não
      dá para testar com o JurisTCU como ele é
- [ ] Explicar por que o recorte **sobe** o Recall@100 no BM25 e **desce** no
      denso. Há hipótese registrada, não há medição

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

Sete resultados sustentados por evidência. Os quatro primeiros são da F5; os
três últimos, da F6 (28/09).

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

**5. 🆕 Descartar o relatório do índice melhora a recuperação, nas cinco
estratégias e nos dois retrievers.**
BM25: +11,2% a +16,8% de nDCG@10, todas com p entre 0,00025 e 0,003. Denso:
+12,3% a +27,8%. O índice fica com 28–34% do tamanho. No BM25 o Recall@100
**também sobe** (+1,8% a +6,0%); no denso cai (−4,1% a −10,5%), e essa
diferença é limitação do denso, não do método. O ganho vale igual com os spans
**preditos** pelo segmentador (`gold` × `pred`: p = 0,9886, 75 empates em 150).

**6. 🆕 E não é por o índice ficar menor — é por *qual* parte sai.**
Controle pareado: descartando o **mesmo número** de chunks, sorteados ao acaso,
o nDCG@10 **cai** 8,2% a 16,8%. Mesmo tamanho de índice, efeitos de sinal
oposto. É este controle que transforma a observação numa afirmação causal
sobre a estrutura do acórdão.

**7. 🆕 O retriever denso não é dispensável: é complementar.**
Fundido ao BM25 com peso escolhido por **validação cruzada por consulta**
(5 dobras), acrescenta 4,4% a 8,6% de nDCG@10 sobre o BM25 sozinho, em 6 de 10
configurações com p < 0,05. Melhor ainda: fundir as **quatro** condições
(BM25 e denso, cada um com e sem o relatório) com **peso igual** chega a
**0,3215 — +29,3% sobre o baseline**, e o ganho vai de +19,5% a +29,3% nas
cinco estratégias, com todas as métricas subindo e **sem nenhum
hiperparâmetro**. Mantém-se nos três tipos de consulta, inclusive nas reais de
log (+18,2%).

**8. 🆕 O efeito segue a concentração de relevância, e a decisão generaliza.**
Dez recortes de seção testados: remover seções pobres **e pequenas** não faz
nada (ementa −0,1%, dispositivo +0,2%); remover a fundamentação custa −17,5%;
e indexar **só** o relatório — 72% do texto — é 21,5% **pior** que indexar
tudo. A formulação correta do achado é *"indexe a parte do documento onde a
relevância se concentra"*, não *"o relatório é ruim"*.

E a decisão de qual seção indexar, que foi tomada olhando os rótulos de
relevância, foi validada por **validação cruzada por consulta** sobre 10
candidatos: as cinco dobras escolheram a mesma configuração, e o ganho medido
**fora** da escolha é **+16,2%** (p = 0,000275) contra +16,8% medido dentro.

> **O que muda na tese.** O trabalho passa a ter duas perguntas, e as duas com
> resposta: *como cortar o documento?* (tanto faz, e agora sabemos que o
> empate vale em dois pontos de operação) e *qual parte indexar?* (a
> fundamentação; o relatório atrapalha). A segunda nasceu da primeira.

> ⚠️ **Limitação a declarar no artigo.** O JurisTCU julga relevância sobre
> excertos de jurisprudência, que representam teses jurídicas e saem do voto
> por construção do gênero. A conclusão vale para a tarefa *"encontrar o
> acórdão que firma determinada tese"*; **não** se pode afirmar que o
> relatório seja inútil para quem busca fatos do caso concreto. Detalhe em
> [f6/04-auditoria-de-validade](docs/docsleo/branches/leo-f6-secoes-e-fusao/04-auditoria-de-validade.md) §10.

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

# 6. F6 — a configuracao recomendada (28/09)
python -m src.run_experiments --strategy all --retriever bm25  --secoes sem:relatorio
python -m src.run_experiments --strategy all --retriever dense --secoes sem:relatorio
python -m src.tuning --bm25 <rodada-bm25-recortada> --denso <rodada-densa-recortada>
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
├── PLANO.md                    ← você está aqui (documento vivo)
├── RESULTADOS-F6.md            resumo dos resultados novos, para apresentar
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
| 28/09 | **F6:** recorte por seção vira pipeline e roda no BM25 — **+11% a +17%, as cinco significativas** | [f6/resultados/01](docs/docsleo/branches/leo-f6-secoes-e-fusao/resultados/01-recorte-por-secao.md) |
| 28/09 | **Controle:** −67% aleatório **piora**; −67% escolhendo o relatório melhora | [f6/resultados/02](docs/docsleo/branches/leo-f6-secoes-e-fusao/resultados/02-controle-aleatorio.md) |
| 28/09 | **Fusão BM25 + denso** com peso por validação cruzada: +4,4% a +8,7% | [f6/resultados/03](docs/docsleo/branches/leo-f6-secoes-e-fusao/resultados/03-fusao-hibrida.md) |
| 28/09 | **Configuração final: nDCG@10 = 0,3215 (+29,3%)**, todas as métricas sobem, sem hiperparâmetro | [f6/resultados/04](docs/docsleo/branches/leo-f6-secoes-e-fusao/resultados/04-tabela-principal.md) |
| 28/09 | ⚠️ **Bug dos empates:** o mesmo arquivo TREC dava dois números no mesmo recorte. Corrigido, tabelas da F6 regeradas | [f6/03-empate-de-score](docs/docsleo/branches/leo-f6-secoes-e-fusao/03-empate-de-score.md) |
| 28/09 | **Auditoria de validade:** 10 ameaças testadas — dose-resposta, nDCG reimplementado do zero, controle em 3 sementes, escolha da seção por CV | [f6/04-auditoria-de-validade](docs/docsleo/branches/leo-f6-secoes-e-fusao/04-auditoria-de-validade.md) |
| 28/09 | Branch `leo/f6-secoes-e-fusao` mergeada na `main` | [README da branch](docs/docsleo/branches/leo-f6-secoes-e-fusao/README.md) |

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
| **Ponderar a seção** em vez de cortar (F6) | Satura no corte binário e **não** preserva o recall: o peso é aplicado depois do corte em `--top-chunks`, então o chunk descontado já ocupou vaga |
| **RRF sem peso** para fundir BM25 + denso (F6) | p entre 0,206 e 0,906. Peso igual a um retriever 20% pior puxa a fusão para baixo tanto quanto o outro puxa para cima |
| **`sum_top_k`** como agregação (F6) | Perde do `max_pooling` em 4 de 5 estratégias. Era análise de sensibilidade: cumpriu o papel de justificar o default |
