# Datasets

Este projeto usa três datasets públicos do Hugging Face Hub. Os arquivos **não**
são versionados no repositório (são grandes demais); em vez disso, use o script
de download para reconstruir esta pasta localmente.

## Como baixar

```bash
python scripts/download_datasets.py
```

Isso cria a estrutura abaixo dentro de `data/`. Para baixar só um dataset
específico:

```bash
python scripts/download_datasets.py juristcu
python scripts/download_datasets.py jurisprudencias_stj
python scripts/download_datasets.py brazilian_court_decisions
```

Para forçar o re-download de arquivos já existentes, adicione `--force`.

O script usa apenas a biblioteca padrão do Python (3.x), sem dependências
externas.

## Estrutura

```
data/
├── juristcu/
│   ├── doc.csv
│   ├── qrel.csv
│   └── query.csv
├── jurisprudencias_stj/
│   └── jurisprudencias_stj.parquet
└── brazilian_court_decisions/
    ├── train.jsonl
    ├── test.jsonl
    └── validation.jsonl
```

## Datasets

### JurisTCU

Dataset de recuperação de informação jurídica em português, com jurisprudência
do Tribunal de Contas da União (TCU) e julgamentos de relevância (qrels) para
avaliação de sistemas de busca jurídica.

- **Link:** https://huggingface.co/datasets/LeandroRibeiro/JurisTCU
- **Arquivos:**
  - `doc.csv` — 16.045 documentos (acórdãos/enunciados) do TCU
  - `query.csv` — 150 consultas de busca
  - `qrel.csv` — 2.250 julgamentos de relevância consulta↔documento

### Jurisprudências STJ

Jurisprudência do Superior Tribunal de Justiça (STJ), extraída do portal
[SCON](https://scon.stj.jus.br/SCON/), com teses geradas por LLM.

- **Link:** https://huggingface.co/datasets/celsowm/jurisprudencias_stj
- **Arquivo:** `jurisprudencias_stj.parquet` (~1,2 GB)

### Brazilian Court Decisions

Coleção de 4.043 ementas de decisões judiciais do Tribunal de Justiça de
Alagoas (TJAL), rotuladas em 7 categorias e por unanimidade da decisão.
Suporta a tarefa de Legal Judgment Prediction.

- **Link:** https://huggingface.co/datasets/joelniklaus/brazilian_court_decisions
- **Arquivos:** `train.jsonl` (3.234 registros), `test.jsonl` (404),
  `validation.jsonl` (404)
