# Setup do ambiente (máquina do Leo) e passos manuais

**Data:** 2026-09-05 · **Autor:** Leonardo Marques · **Status:** ✅ concluído

## Resposta curta: qual é o passo manual obrigatório?

**Só um, e só se usarmos o `embeddinggemma`:** aceitar a licença Gemma no
Hugging Face e rodar `hf auth login`. Ver
[05-modelos-embedding.md](05-modelos-embedding.md).

Tudo o mais é automatizado:
- os dois datasets são públicos e baixam por script, **sem credencial**;
- as dependências instalam por `pip install -r requirements.txt`;
- a montagem do corpus é um comando (`python -m src.ingest`).

## O que foi feito nesta máquina

### 1. Repositório e pastas grandes fora da nuvem

O repo vive dentro de `Documents\GoogleDrive\...`, e o `scripts/README.md`
avisa para não deixar `data/` nem `.venv/` numa pasta sincronizada (o cliente
trava com os ~6 GB do corpus). Como o **Developer Mode do Windows está
desligado**, `mklink /D` (symlink) exigiria administrador — usei **junction**
(`mklink /J`), que não exige:

```powershell
mkdir C:\data\tcc-segundo-semestre
cmd /c mklink /J "<repo>\data" "C:\data\tcc-segundo-semestre"
cmd /c mklink /J "<repo>\juris-chunking\.venv" "C:\venvs\tcc-juris"
```

⚠️ Detalhe que quase quebrou o git: `data/README.md` **é versionado**. Antes de
trocar a pasta pelo junction, copiei o README para dentro do destino real
(`C:\data\tcc-segundo-semestre\README.md`). Com isso o git continua enxergando
`data/README.md` normalmente e o `git status` fica limpo. Se alguém repetir o
setup e pular esse passo, o git vai acusar o README como deletado.

| O quê | Onde fica de verdade | Como o repo enxerga |
|---|---|---|
| Datasets (~6 GB) | `C:\data\tcc-segundo-semestre` | `data/` (junction) |
| Ambiente virtual (~1,8 GB) | `C:\venvs\tcc-juris` | `juris-chunking/.venv` (junction) |

### 2. Dependências — o risco do plano não se materializou

O `plano_implementacao.md` §F0 registra como maior risco: *"`ranx` (numba) no
Python 3.13 — testar primeiro; fallback: venv com Python 3.11/3.12"*, e o
artigo afirma que o pipeline roda em **Python 3.11**.

**Resultado: tudo instala e importa em Python 3.13.7.** Não precisamos do
fallback. `numba` 0.67 já suporta 3.13.

```
Python 3.13.7          faiss-cpu 1.15.0       torch 2.14.0+cpu
numba 0.67.0           ranx 0.3.21            sentence-transformers 6.0.1
numpy 2.5.2            pandas 3.0.5           bm25s 0.3.11
tiktoken 0.14.0        langchain-text-splitters 1.1.2
```

Aceite da F0 (do plano) — passou:
```bash
python -c "import faiss, bm25s, tiktoken, ranx, sentence_transformers"
# OK - todos importam
```

> 📝 **Para o artigo:** a Seção "Infrastructure and feasibility" diz "Python
> 3.11". Ou corrigimos para 3.13, ou dizemos "Python ≥ 3.11" — o que for
> verdade para a máquina que gerar os resultados finais. Não deixar 3.11 escrito
> se rodarmos em 3.13.

### 3. Testes

```bash
cd juris-chunking && pytest -q
# 39 passed in 8.26s
```

### 4. Download dos datasets

```bash
python scripts/download_datasets.py juristcu      # 90 MB — segundos
python scripts/download_datasets.py tcu_acordaos  # ~6 GB — horas, retomável
```

O download do TCU é feito por blocos com `Range` e é seguro interromper: os
arquivos completos são pulados e os `.part` retomam de onde pararam.

## Reproduzir isto em outra máquina

```bash
git clone https://github.com/igormamus1703/tcc-segundo-semestre.git
cd tcc-segundo-semestre
# (opcional, se o repo estiver em pasta de nuvem) junctions para data/ e .venv
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r juris-chunking/requirements.txt
python scripts/download_datasets.py juristcu tcu_acordaos
cd juris-chunking && python -m src.ingest && pytest -q
```
