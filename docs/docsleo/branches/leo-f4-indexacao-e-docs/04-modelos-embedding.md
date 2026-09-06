# Escolha do embedder (resolve o `PREENCHER` do `models.yaml`)

**Data:** 2026-09-05 · **Autor:** Leonardo Marques · **Status:** proposta, aguarda aval da equipe

## O problema

`juris-chunking/configs/models.yaml` estava assim, bloqueando a F4:

```yaml
embedders:
  - name: pt_compact
    hf_id: "PREENCHER"  # escolher a partir do MTEB-BR, arXiv:2607.04581
  - name: multilingual_ref
    hf_id: "intfloat/multilingual-e5-large"
```

Havia ainda uma divergência entre os documentos: o `plano_implementacao.md` §F4
manda usar `intfloat/multilingual-e5-base` como *default executável*, enquanto o
`models.yaml` traz `e5-large`.

## O que o MTEB-BR mostra

Fui ao paper do MTEB-BR (arXiv:2607.04581), que é a referência que o próprio
plano manda usar. Dados relevantes:

- 22 tarefas nativas de português brasileiro, 93 modelos avaliados (23M a 27B
  parâmetros; 73 open-weight, 20 APIs comerciais).
- **Recuperação é a categoria que mais separa os modelos** — "retrieval
  spreading models most widely". Ou seja, a escolha do embedder importa mais
  para o nosso caso do que importaria para classificação.
- Os líderes em retrieval são **grandes**: Qwen3-Embedding-8B (7,6B),
  KaLM-Embedding-Gemma3-12B (11,8B), Octen-Embedding-8B (7,6B). **Inviáveis**
  para nós: seriam ~1,4M de chunks para embedar em CPU.
- **O achado que resolve nosso problema:** `embeddinggemma-300m` (308M
  parâmetros) fica em **13º de 93**, a apenas **0,033** do líder. É o menor
  modelo competitivo do benchmark.
- Rank global multilíngue prevê mal o rank em português (Spearman ρ = 0,75) —
  ou seja, **não dá para escolher pelo MTEB genérico**, e é por isso que citar
  o MTEB-BR aqui é um argumento forte na banca.

⚠️ **Cuidado que evitei:** o BERTimbau-large aparece em 3º de 93 no ranking
*geral*, e seria tentador escolhê-lo por ser "o modelo brasileiro". Mas
BERTimbau é um encoder MLM, **não um bi-encoder treinado para recuperação** —
exatamente a armadilha que o `plano_tecnico.md` §3 já alerta a respeito do
RoBERTaLexPT ("o desempenho será enganosamente ruim e alguém na banca vai
apontar isso"). Não usar sem fine-tune.

## Decisão proposta

| Slot | Modelo | Params | Licença | Gated? | Papel |
|---|---|---|---|---|---|
| `pt_compact` | `google/embeddinggemma-300m` | 308M | Gemma | **sim** ⚠️ | Melhor custo/benefício no MTEB-BR; é o número "bom" do artigo |
| `multilingual_ref` | `intfloat/multilingual-e5-base` | 278M | MIT | não | Baseline multilíngue de referência; **roda sem nenhum passo manual** |

Troquei `e5-large` (560M) por `e5-base` (278M) para seguir o
`plano_implementacao.md` §F4 e porque o custo de encode dobra com o large sem
ganho claro para o papel de *baseline de referência*. Se sobrar tempo/GPU, o
large entra como sensibilidade.

### Prefixos — atenção, não é opcional

Os dois modelos exigem prefixos diferentes, e usar errado degrada o resultado
silenciosamente (o modelo não reclama, só recupera pior):

- **e5:** `"query: {texto}"` para consultas, `"passage: {texto}"` para chunks.
- **embeddinggemma:** `"task: search result | query: {texto}"` para consultas,
  `"title: none | text: {texto}"` para chunks.

Isso está implementado em `src/indexing/dense.py` como configuração por modelo
(`query_prefix` / `passage_prefix` no `models.yaml`), não hard-coded.

## ⚠️ O único passo manual obrigatório do projeto inteiro

`google/embeddinggemma-300m` é **gated** no Hugging Face: exige conta, aceitar
a licença Gemma e autenticar localmente.

```bash
# 1. Ter conta no huggingface.co e aceitar os termos em:
#    https://huggingface.co/google/embeddinggemma-300m
# 2. Autenticar na máquina (uma vez só):
hf auth login          # versões novas do huggingface-hub
# ou: huggingface-cli login
```

**Tudo o mais no projeto é automatizado** — os dois datasets (JurisTCU e
acórdãos do TCU) são públicos e baixam sem credencial pelo
`scripts/download_datasets.py`.

Se ninguém quiser criar conta no HF, o pipeline **roda inteiro** só com o
`multilingual_ref` (e5-base, MIT, sem gate) — perdemos o modelo melhor, não o
experimento. Por isso o `run_experiments.py` aceita `--embedder` e o default é
o modelo sem gate.

## O que isso significa para o artigo

A frase atual — *"a compact Portuguese model selected based on MTEB-BR"* — fica
sustentada, mas dá para deixar bem mais forte, porque agora temos o dado:
escolhemos um modelo de 308M que fica a 0,033 do líder de um benchmark de 93
modelos, sendo que os líderes têm 8–12B. Isso é um argumento de
**custo-benefício mensurado**, não de conveniência.

## Fontes

- [MTEB-BR — arXiv:2607.04581](https://arxiv.org/abs/2607.04581)
- [google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m)
- [intfloat/multilingual-e5-base](https://huggingface.co/intfloat/multilingual-e5-base)
