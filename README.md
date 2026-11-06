# Segmentação estrutural de acórdãos do TCU para recuperação de informação

**Trabalho de Conclusão de Curso** · Ciência da Computação · PUCPR · 2026
**Equipe:** Felipe Ribas, Igor Mamus, João Vitor Manfrim e Leonardo Marques
**Orientador:** Prof. Marco Antonio Simões Teixeira

Acórdãos do Tribunal de Contas da União (TCU) são documentos longos, com
mediana de 11.426 tokens. Para entrar num sistema de busca, eles precisam ser
cortados em pedaços (*chunks*). Este projeto investiga duas perguntas:

1. **Como cortar?** Cortar respeitando as macro-seções do acórdão (ementa,
   relatório, fundamentação e dispositivo) melhora a recuperação, comparado a
   cortes de tamanho fixo e recursivos?
2. **O que indexar?** Qual parte do acórdão deve entrar no índice?

Os experimentos usam **12.880 acórdãos íntegros**, dois retrievers (**BM25** e
um denso, **BAAI/bge-m3**) e duas coleções de consultas (**JurisTCU** e
**JUÁ-Juris**), com teste de significância, controles e validação externa.

> **Status: concluído (06/11/2026).** Fases F0 a F7 implementadas e
> integradas; **206 testes** passando. Para ver os resultados com gráficos,
> abra no navegador [`docs/apresentacao/index.html`](docs/apresentacao/index.html)
> (F6) e [`docs/apresentacao/f7.html`](docs/apresentacao/f7.html) (F7).

---

## Principais resultados

1. **Como cortar.** Com as 150 consultas do JurisTCU, as cinco estratégias não
   se distinguem: das 20 comparações entre estratégias, só uma tem p < 0,05, e
   a favor do corte fixo. Com as **7.567 consultas do JUÁ-Juris**, o corte
   **estrutural vence** o fixo e o recursivo (+1% a +12% de nDCG@10), porque
   isola a ementa num chunk próprio. O segmentador por regras é
   **equivalente** à estrutura oficial (teste de equivalência TOST).
2. **O que indexar.** A fundamentação concentra **72% do conteúdo julgado
   relevante** em 23% do texto, mas os retrievers acham os documentos sobretudo
   pelo relatório. **Tirar do índice os trechos inteiramente de relatório**
   (critério `toca`) melhora o nDCG@10 em +15,6% no JurisTCU e +9,7% nas
   consultas naturais do JUÁ, sem piorar em nenhuma amostra.
3. **Melhor configuração:** recorte por seção combinado com a fusão de BM25 e
   denso. **nDCG@10 = 0,3215 contra 0,2486** do baseline no JurisTCU (+29,3%,
   p < 0,00001), com as quatro métricas subindo e sem hiperparâmetro.
4. **Por que acreditamos.** Descartar o **mesmo número** de chunks ao acaso
   **piora** o resultado (controle pareado). O achado foi auditado contra dez
   ameaças de validade e replicado numa segunda coleção, com as hipóteses
   registradas antes de rodar.
5. **O BM25 supera o retriever denso** em todas as estratégias (p < 0,01 nas
   cinco), mas o denso é complementar: a fusão dos dois é a melhor configuração.

### Pergunta 1: estratégias de chunking

nDCG@10 no JurisTCU, índice completo (rodadas `20260906-0515_bm25` e
`20260907-0125_dense_bge_m3`):

| Estratégia | Como corta | BM25 | Denso (bge-m3) |
|---|---|---:|---:|
| `structural_pred` | nas fronteiras de seção previstas pelo segmentador | **0,2526** | 0,1912 |
| `structural_gold` | nas fronteiras de seção oficiais (colunas do TCU) | 0,2521 | 0,1847 |
| `fixed_1024_512` | janela de 1024 tokens, passo de 512 | 0,2510 | 0,2019 |
| `fixed_512_256` | janela de 512 tokens, passo de 256 | 0,2486 | **0,2055** |
| `recursive_default` | separadores de texto, até 1024 tokens | 0,2412 | 0,1967 |

Com poder estatístico (F7; BM25, índice completo): estrutural predito contra
cada alternativa, em nDCG@10:

| | JurisTCU (150) | JUÁ natural (6.000) | JUÁ difícil (1.567) |
|---|---:|---:|---:|
| × fixo 512/256 | +1,4% (n.s.) | **+1,2%** (p = 0,005) | **+7,3%** (p = 0,0001) |
| × recursivo | +4,8% (n.s.) | **+2,4%** (p < 10⁻⁸) | **+9,9%** (p < 10⁻⁵) |
| × estrutural ouro | equivalentes (TOST, ±0,01) | equivalentes | equivalentes |

### Pergunta 2: o que indexar

Estratégia `fixed_512_256`, JurisTCU (rodada `20260928-1822_f6_tabela_principal`):

| Configuração | nDCG@10 | MRR@10 | MAP@10 | R@100 |
|---|---:|---:|---:|---:|
| BM25, índice completo (baseline) | 0,2486 | 0,5186 | 0,0963 | 0,4709 |
| BM25, mesmo nº de chunks descartados **ao acaso** (controle) | 0,2260 | 0,4725 | 0,0867 | 0,4310 |
| BM25, **sem o relatório** | 0,2904 | 0,5889 | 0,1190 | 0,4993 |
| sem o relatório + fusão com o denso (peso por validação cruzada) | 0,3160 | **0,6058** | 0,1330 | 0,5259 |
| **fusão das 4 condições, peso igual** | **0,3215** | 0,6000 | **0,1402** | **0,5479** |

### Validação externa (F7): o critério `toca`

BM25, `fixed_512_256`, nDCG@10 (rodada `20261005-2216_f7_replicacao_final`):

| Coleção | Consultas | Índice completo | Sem relatório, pela maioria (F6) | Sem relatório, `toca` (F7) |
|---|---:|---:|---:|---:|
| JurisTCU | 150 | 0,2490 | 0,2893 (+16,2%) | 0,2878 (+15,6%) |
| JUÁ natural | 6.000 | 0,6549 | 0,7078 (+8,1%) | 0,7182 (+9,7%) |
| JUÁ difícil | 1.567 | 0,2497 | 0,2182 (**−12,6%**) | 0,2634 (+5,5%) |

O recorte da F6 falha nas consultas difíceis: nos cortes fixos, o primeiro
chunk junta a ementa com o início do relatório e é descartado com ele. O
critério `toca`, que descarta só os chunks inteiramente de relatório, corrige
isso. Os ganhos no JurisTCU e no JUÁ natural são significativos após a
correção de Bonferroni; o +5,5% no JUÁ difícil, não (p = 0,012 sem correção).

> O índice completo dá 0,2490 nesta tabela e 0,2486 na anterior para o mesmo
> run: a replicação desempata scores iguais pelo identificador do documento
> antes de medir. Detalhe em
> [`03-empate-de-score.md`](docs/documentos/branches/f6-secoes-e-fusao/03-empate-de-score.md).

### O que foi tentado e ficou de fora

A exploração completa da F7 está guardada na branch **`f7-evolucao`**,
sem merge. Os resultados existem, mas não compensaram a complexidade
acrescentada:

| Tentativa | Resultado (JurisTCU) | Por que ficou de fora |
|---|---|---|
| Ranker aprendido (LambdaRank com sinais por seção, treinado no JUÁ) | +18,6% sobre o BM25 | Empata com a fusão das 4 condições, que não precisa de modelo treinado |
| Reranker com cross-encoder (`bge-reranker-v2-m3`) | −15,9% contra a fusão das 4 | Não supera o primeiro estágio |
| Ajuste fino LoRA do reranker | −60% (v1) e −28% (v2) contra o reranker sem ajuste | Com negativos só do BM25, o modelo aprendeu um atalho que penaliza o casamento literal; negativos mistos (v2) atenuaram, sem resolver |

A branch fica como registro do que foi tentado e como base para trabalhos
futuros. Análise completa em
[`docs/documentos/branches/f7-evolucao/`](docs/documentos/branches/f7-evolucao/README.md).

### Limitações

- O JurisTCU julga excertos de jurisprudência, que tendem a sair da
  fundamentação. A conclusão vale para encontrar o acórdão que firma uma tese,
  não para buscas por fatos do caso concreto.
- O JUÁ-Juris mede outra tarefa (achar o acórdão de um enunciado); as duas
  coleções se complementam, mas não são intercambiáveis.
- As 50 consultas reais de log do JurisTCU não têm poder para detectar os
  efeitos medidos, embora todos apontem na mesma direção.

---

## Dados

| Fonte | Conteúdo | Uso no projeto |
|---|---|---|
| [Acórdãos completos do TCU](https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/) (dados abertos) | 21 CSVs (2003–2023), uma coluna por seção do acórdão | Texto dos documentos e estrutura oficial das seções |
| [JurisTCU](https://huggingface.co/datasets/LeandroRibeiro/JurisTCU) | 16.045 documentos, 150 consultas e 2.250 julgamentos de relevância | Consultas e relevância (F1–F7) |
| [JUÁ-Juris](https://huggingface.co/datasets/ufca-llms/jua) | 1.714 pares (enunciado, excerto) de teste e 15.433 de treino | Segunda coleção de consultas (F7) |

O **corpus** liga cada documento do JurisTCU ao acórdão íntegro que o contém:
12.880 acórdãos, com 98,7% dos documentos ligados e 99,69% dos julgamentos
preservados (2.219 pares consulta-acórdão). Do JUÁ-Juris entram as 1.567
consultas de teste que caem nesses acórdãos e uma amostra natural de 6.000 do
treino.

Os dados não são versionados no Git por causa do tamanho (~6 GB). O script
`scripts/download_datasets.py` baixa os três conjuntos.

> ⚠️ O TCU regerou os CSVs de acórdãos em 02/10/2026, e os de 2019, 2020, 2022
> e 2023 mudaram. Os resultados usam a versão baixada em 05/09/2026; para
> reproduzi-los exatamente, use essa cópia, entregue com o pacote de
> artefatos e com checksums SHA-256. Detalhes em
> [`scripts/README.md`](scripts/README.md).

---

## Como o pipeline funciona

```
 CSVs do TCU ─┐
              ├─► F1 ingestão ─► F2 segmentador ─► F3 chunking (5 estratégias)
 JurisTCU ────┘                                             │
                                                            ▼
 F7 validação no JUÁ-Juris ◄─ F6 seleção por seção ◄─ F5 avaliação ◄─ F4 busca
    (critério toca, TOST)        e fusão BM25+denso       (métricas e     (BM25 e
                                                           significância)   denso)
```

| Fase | Código (`juris-chunking/src/`) | O que faz |
|---|---|---|
| F1 | `ingest.py` | Liga o JurisTCU aos acórdãos íntegros, normaliza o texto e grava os spans de cada seção |
| F2 | `segmenter/` | Prevê as seções por regras: 92,2% de acurácia por caractere contra a estrutura oficial, 0% de fallback |
| F3 | `chunkers/` | Cinco estratégias (fixa 512/256 e 1024/512, recursiva, estrutural ouro e predita): 2.200.767 chunks |
| F4 | `indexing/`, `retrieval.py`, `run_experiments.py` | BM25 (`bm25s`) e denso (BAAI/bge-m3 com FAISS, busca exata); agregação chunk → documento por *max-pooling* |
| F5 | `evaluate.py`, `analysis.py`, `plots.py` | nDCG@10, MRR@10, MAP@10 e Recall@100; teste t pareado com Bonferroni, IC 95% por bootstrap, análise de poder e recortes |
| F6 | `sections.py`, `fusion.py`, `tuning.py` | Recorte do índice por seção, controle pareado, fusão RRF e soma normalizada, peso por validação cruzada |
| F7 | `jua.py`, `mecanismo.py`, `replicacao.py` | JUÁ-Juris ligado ao corpus, critério `toca`, mecanismo da ementa e replicação entre coleções com TOST |

---

## Como reproduzir

**Requisitos:** Python 3.13, cerca de 15 GB livres e GPU NVIDIA para o
retriever denso: o encode leva cerca de 10 h numa RTX 5060, contra 127 h em
CPU. Versões dos pacotes em
[`juris-chunking/requirements.txt`](juris-chunking/requirements.txt).

```bash
git clone https://github.com/igormamus1703/tcc-segundo-semestre.git
cd tcc-segundo-semestre
python -m venv .venv && .venv\Scripts\activate         # Linux/Mac: source .venv/bin/activate
pip install -r juris-chunking/requirements.txt

python scripts/download_datasets.py juristcu tcu_acordaos jua   # ~6 GB, retomável

cd juris-chunking
pytest -q                                                        # 206 testes
python -m src.ingest                                             # corpus, poucos minutos
python -m src.segmenter.validate                                 # acurácia do segmentador
python -m src.chunkers.run --strategy all                        # chunks, ~50 min
python -m src.run_experiments --strategy all --retriever bm25    # ~25 min
python -m src.run_experiments --strategy all --retriever dense   # ~10 h de GPU
python -m src.evaluate --experiment <rodada>                     # tabelas
python -m src.plots --experiment <rodada>                        # figuras
```

Os comandos da F6 (recorte, controle e fusão) e da F7 (JUÁ-Juris, critério
`toca`, mecanismo e replicação) estão em
[`juris-chunking/README.md`](juris-chunking/README.md). Para rodar F4 a F6 de
uma vez, com orçamento de tempo e log, use `.\scripts\rodada_completa.ps1`
(ver [`scripts/README.md`](scripts/README.md)).

**Rastreabilidade.** Cada execução cria `results/experiments/AAAAMMDD-HHMM_rótulo/`
com um `manifest.json` que registra o comando exato, o commit, as versões das
bibliotecas e o hardware. A pasta também guarda as tabelas e um log da
execução, e as figuras trazem no rodapé a rodada e o commit de onde vieram. O
índice de todas as rodadas está em
[`results/experiments/INDICE.md`](results/experiments/INDICE.md), e a
convenção completa em [`results/README.md`](results/README.md).

---

## Estrutura do repositório

```
├── README.md                  este arquivo
├── PLANO.md                   estado do projeto, decisões e histórico
├── plano_tecnico.md           arquitetura, stack e cronograma
├── plano_implementacao.md     plano e status fase a fase (F0–F7)
├── RESULTADOS-F6.md           resumo da F6, escrito para a orientação
├── REFERENCIAS.md             bibliografia, com BibTeX
├── juris-chunking/            código-fonte (src/), configurações, testes e notebooks
├── scripts/                   download dos dados e execução encadeada
├── data/                      dados brutos (não versionados)
├── results/
│   ├── corpus/                caracterização do corpus e do segmentador
│   └── experiments/           uma pasta por rodada: manifesto, log, tabelas e figuras
└── docs/
    ├── documentos/               caderno de bordo, uma pasta por branch de trabalho
    └── apresentacao/          páginas com gráficos da F6 e da F7
```

## Branches

| Branch | O que é |
|---|---|
| `main` | O projeto final |
| `f7-evolucao` | Arquivo da exploração completa da F7 (ranker aprendido, reranker com cross-encoder e ajuste fino), sem merge; base para trabalhos futuros |

As branches de trabalho já integradas à `main` (F4/F5, F6, F7 e encerramento)
estão documentadas em [`docs/documentos/`](docs/documentos/README.md).

## Documentação

| Para saber... | Leia |
|---|---|
| Estado do projeto, decisões tomadas e histórico | [`PLANO.md`](PLANO.md) |
| Arquitetura, stack e cronograma | [`plano_tecnico.md`](plano_tecnico.md) |
| O que cada fase entregou | [`plano_implementacao.md`](plano_implementacao.md) |
| Os resultados da F6, com a argumentação | [`RESULTADOS-F6.md`](RESULTADOS-F6.md) |
| A F7 que vai para o artigo (parágrafo e tabelas propostos) | [`docs/documentos/branches/f7-enxuta/README.md`](docs/documentos/branches/f7-enxuta/README.md) |
| A auditoria de validade da F6 | [`04-auditoria-de-validade.md`](docs/documentos/branches/f6-secoes-e-fusao/04-auditoria-de-validade.md) |
| O pré-registro das hipóteses da F7 | [`00-preregistro.md`](docs/documentos/branches/f7-evolucao/00-preregistro.md) |
| A bibliografia | [`REFERENCIAS.md`](REFERENCIAS.md) |

---

## Fluxo de trabalho da equipe

O projeto seguiu quatro passos, nesta ordem: **branch → testar → anotar →
merge**.

### 1. Trabalhe numa branch, nunca direto na `main`

```bash
git checkout -b <fase>-<assunto-curto>     # ex.: f4-indexacao-e-docs
```

A `main` só recebe código que já rodou e foi revisado. Commits pequenos, com
mensagem simples e direta dizendo **o que foi feito e por quê**.

### 2. Teste antes de pedir merge

```bash
cd juris-chunking && pytest -q     # tem que estar verde
```

Mudou comportamento? **Escreva o teste junto.** Dê preferência a testar o que
falha em silêncio: encoding, alinhamento de índices, cache inválido,
normalização divergente entre indexação e busca, empate de scores. Erro que
estoura exceção você descobre sozinho; o que só piora o número passa direto e
vai parar no artigo.

Antes de rodar no corpus inteiro, faça o smoke test:

```bash
python -m src.chunkers.run --strategy all --limit-docs 500
python -m src.run_experiments --strategy all --retriever bm25 --limit-queries 10
```

### 3. Anote tudo na pasta de documentação

Toda a documentação fica em `docs/documentos/`, com uma pasta por branch de
trabalho:

```
docs/
└── documentos/
    └── branches/
        └── <nome-da-branch>/
            ├── README.md        o que a branch faz + checklist de merge
            ├── NN-assunto.md    decisões, achados, execução
            └── resultados/      números medidos, com o comando que os gerou
```

O caderno de bordo das fases F4 a F7 está em [`docs/documentos/`](docs/documentos/README.md).

Toda anotação tem, no mínimo: **data e autor**, **o comando exato**
(copiável, não parafraseado), **o número que saiu** e o artefato que o
comprova, **a decisão tomada** e a alternativa descartada, e **o que ficou em
aberto**.

> **Por que isso não é burocracia:** o número **113.827 documentos** saiu no
> nosso pôster, e só descobrimos que ele não correspondia ao que o código
> produz porque alguém foi ler a mensagem de um commit de agosto. Se a decisão
> de filtrar o corpus tivesse sido anotada quando foi tomada, o número errado
> nunca teria saído. Ver
> [`02-achado-corpus.md`](docs/documentos/branches/f4-indexacao-e-docs/02-achado-corpus.md).

**Nenhum número vai para o artigo sem estar anotado com o artefato que o
comprova.** Se não dá para apontar o arquivo em `results/` que gerou aquele
valor, ele não entra. **O mesmo vale para figuras:** toda figura sai de
`python -m src.plots`, que estampa no rodapé a rodada, a data, o corpus, o
modelo e o commit, lidos do manifesto.

### 4. Só então o merge

O merge vem com o `README.md` da branch preenchido (o que mudou, testes
verdes, o que precisa de revisão) e depois da revisão de quem é dono da fase
tocada. Se a branch muda números que já estão no artigo ou no pôster, isso é
dito explicitamente.

### Regra final, que vale mais que as outras

**Reporte o que aconteceu, não o que devia ter acontecido.** Se o teste falhou,
diga que falhou e mostre a saída. Se o resultado deu nulo, escreva que deu
nulo. Um resultado nulo bem medido é um TCC completo (`plano_tecnico.md` §7);
um resultado inflado que a banca desmonta na defesa, não.
