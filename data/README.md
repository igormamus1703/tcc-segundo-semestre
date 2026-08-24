# data/

Esta pasta guarda os datasets baixados e é **ignorada pelo Git** (só este
README é versionado). Ela é recriada localmente por cada integrante do TCC —
ver `scripts/README.md` para o passo a passo de download e a recomendação
de manter `data/` fora de pastas sincronizadas por nuvem (OneDrive/Drive/
Dropbox), que trava com os ~6 GB do `tcu_acordaos`.

Depois do download, o conteúdo esperado é:

```
data/
├── juristcu/
│   ├── doc.csv
│   ├── qrel.csv
│   └── query.csv
└── tcu_acordaos/
    └── acordao-completo-{2003..2023}.csv
```

Os artefatos derivados desses arquivos brutos (`corpus_docs.jsonl`,
`queries.jsonl`, `qrels.trec`, gerados por `juris-chunking/src/ingest.py`)
ficam em `juris-chunking/data/interim/`, também fora do Git pelo mesmo
motivo de tamanho.
