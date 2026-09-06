# Diário de execução

Ordem cronológica do que foi rodado, com os comandos exatos e o que saiu. Serve
para reproduzir e para escrever a seção de Metodologia sem depender de memória.

---

## 2026-09-05 — Sessão 1 (Leo)

### Ambiente

```bash
git clone https://github.com/igormamus1703/tcc-segundo-semestre.git
# junctions (Developer Mode desligado -> mklink /J, que não exige admin)
mklink /J "<repo>\data" "C:\data\tcc-segundo-semestre"
mklink /J "<repo>\juris-chunking\.venv" "C:\venvs\tcc-juris"
python -m venv C:\venvs\tcc-juris
pip install -r juris-chunking/requirements.txt   # 183 pacotes, ~1,8 GB
```

**Resultado:** tudo instalou em **Python 3.13.7**. O risco "ranx/numba não roda
em 3.13", registrado no plano como o maior risco da F0, **não se materializou**
— não precisamos do fallback para 3.11/3.12.

```bash
python -c "import faiss, bm25s, tiktoken, ranx, sentence_transformers"   # OK
pytest -q                                                               # 39 passed
```

### Datasets

```bash
python scripts/download_datasets.py juristcu       # 90 MB, segundos
python scripts/download_datasets.py tcu_acordaos   # 6,0 GB, ~2 h, exit 0
```

21 arquivos anuais (2003–2023). O download é retomável por blocos `Range`:
interrompi e retomei sem problema durante a sessão.

### Verificação do corpus — o achado do dia

```
docs JurisTCU: 16045 | sem chave de join: 207 | CHAVES ÚNICAS: 12881
```

12.881 ≠ 113.827 (o número dos JSONs versionados e do artigo). Investigação
completa em [02-achado-corpus.md](02-achado-corpus.md).

**Conclusão: o código está certo; os artefatos e o artigo é que estão
defasados.** O Igor tem razão quando diz que "está funcionando".

### Verificação das referências

Todas as 8 citações do artigo conferidas contra o arXiv — **nenhuma citação
fantasma**. Duas correções a fazer, em
[03-referencias-verificadas.md](03-referencias-verificadas.md).

### Implementação da F4/F5

Detalhes e decisões em [06-implementacao-f4.md](06-implementacao-f4.md).

```bash
pytest -q   # 81 passed (39 anteriores + 42 novos)
```

### Em aberto ao fim da sessão

- Decisão do corpus oficial (bloqueia todos os números finais).
- Rodar `src.ingest` e os chunkers sobre o corpus completo.
- Confirmar o que o BR-TaxQA-R realmente concluiu sobre chunking.
