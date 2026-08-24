# Datasets

Este projeto usa dados públicos de duas fontes. Os arquivos **não** são
versionados no repositório (são grandes demais); em vez disso, use o script
de download para reconstruir esta pasta localmente.

## Antes de baixar: tire `data/` de pastas sincronizadas na nuvem

Se o repositório estiver dentro de uma pasta do OneDrive/Google
Drive/Dropbox (como este está), **não baixe os datasets ali dentro** — os
CSVs do TCU somam ~6 GB e o cliente de sincronização trava/(re)envia
arquivos grandes sem parar, deixando os downloads inconsistentes.

Solução usada neste projeto: `data/` é um link simbólico para uma pasta
fora da sincronização.

```powershell
# Windows (PowerShell, como administrador) — ajuste o caminho de destino
mkdir C:\data\tcc-segundo-semestre
cmd /c mklink /D "data" "C:\data\tcc-segundo-semestre"
```

```bash
# Linux/Mac
mkdir -p ~/data/tcc-segundo-semestre
ln -s ~/data/tcc-segundo-semestre data
```

Rode isso a partir da raiz do repositório **antes** do primeiro download.
O `.gitignore` já ignora `data/*`, então o link (ou uma pasta normal, se
preferir não usar link) não afeta o Git de nenhuma forma.

## Como baixar

Os dois datasets usados pelo pipeline atual (ver `plano_implementacao.md`,
seção 0):

```bash
python scripts/download_datasets.py juristcu        # ~91 MB — rápido
python scripts/download_datasets.py tcu_acordaos     # ~6 GB — demora, retomável
```

`tcu_acordaos` baixa 21 arquivos (um por ano, 2003–2023) e é o mais pesado:
espere de dezenas de minutos a algumas horas dependendo da conexão. O
download é feito em blocos (`Range`) e é seguro interromper e rodar de novo
— arquivos já completos são pulados e arquivos parciais (`.part`) retomam
do ponto onde pararam.

Para forçar o re-download de arquivos já existentes, adicione `--force`.

Rodar sem argumentos baixa **todos** os datasets cadastrados, incluindo dois
que foram avaliados e descartados como alternativa de corpus (ver seção 0.5
do `plano_implementacao.md` — mantidos no script só de referência, não são
necessários para rodar o pipeline):

```bash
python scripts/download_datasets.py                 # baixa os 4 (não recomendado)
python scripts/download_datasets.py jurisprudencias_stj
python scripts/download_datasets.py brazilian_court_decisions
```

O script usa apenas a biblioteca padrão do Python (3.x), sem dependências
externas — pode rodar antes mesmo de criar o venv do `juris-chunking`.

## Depois de baixar: montar o corpus

Baixar os CSVs não é o passo final — `juristcu/` e `tcu_acordaos/` são
insumos brutos. O corpus que o resto do pipeline usa (`corpus_docs.jsonl`,
`queries.jsonl`, `qrels.trec`) é construído a partir deles por
`juris-chunking/src/ingest.py`. Ver `juris-chunking/README.md` para o passo
a passo completo (venv, dependências, `python -m src.ingest`).

## Estrutura

```
data/
├── juristcu/
│   ├── doc.csv             # 16.045 documentos (enunciado + excerto)
│   ├── qrel.csv             # 2.250 julgamentos de relevância
│   └── query.csv             # 150 consultas
└── tcu_acordaos/
    ├── acordao-completo-2003.csv
    ├── acordao-completo-2004.csv
    ├── ...
    └── acordao-completo-2023.csv   # 21 arquivos, ~6 GB no total
```

## Datasets

### JurisTCU

Dataset de recuperação de informação jurídica em português, com jurisprudência
do Tribunal de Contas da União (TCU) e julgamentos de relevância (qrels) para
avaliação de sistemas de busca jurídica. Fornece as **queries e os qrels**
usados na avaliação; os documentos crus (enunciado + excerto) não são usados
diretamente — foram substituídos pelos acórdãos íntegros do TCU (ver abaixo)
porque não têm texto suficiente para diferenciar estratégias de chunking
(ver seção 0 do `plano_implementacao.md`).

- **Link:** https://huggingface.co/datasets/LeandroRibeiro/JurisTCU
- **Arquivos:**
  - `doc.csv` — 16.045 documentos (acórdãos/enunciados) do TCU
  - `query.csv` — 150 consultas de busca
  - `qrel.csv` — 2.250 julgamentos de relevância consulta↔documento

### Acórdãos completos do TCU (dados abertos)

Acórdãos **íntegros** do TCU, um CSV por ano (2003–2023), com cada seção do
acórdão em uma coluna separada (`SUMARIO`, `RELATORIO`, `VOTO`, `ACORDAO`,
etc.) — é o corpus principal do projeto. Ligado ao JurisTCU por join em
(`NUMACORDAO`, `ANOACORDAO`, `COLEGIADO`); ver seção 0 do
`plano_implementacao.md` para a decisão completa.

- **Link:** https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/
- **Arquivos:** `acordao-completo-{2003..2023}.csv`, separador `|`, ~6 GB total

### Datasets descartados (mantidos no script só de referência)

Avaliados como alternativa de corpus e descartados — **não precisam ser
baixados** para rodar o pipeline atual:

- **Jurisprudências STJ** — [`celsowm/jurisprudencias_stj`](https://huggingface.co/datasets/celsowm/jurisprudencias_stj) — sem qrels.
- **Brazilian Court Decisions** — [`joelniklaus/brazilian_court_decisions`](https://huggingface.co/datasets/joelniklaus/brazilian_court_decisions) — só ementas, sem qrels.
