# Achado crítico: o corpus do código (12.881) ≠ o corpus do artigo (113.827)

**Data:** 2026-09-05 · **Autor:** Leonardo Marques · **Status:** ⚠️ decisão pendente da equipe

## Resumo em uma frase

O artigo e o pôster afirmam **113.827 documentos indexáveis**; o `ingest.py`
como está hoje no `main` produz **no máximo 12.881**. Não é bug, não é
regressão: é uma mudança de escopo do corpus que não foi propagada para os
artefatos nem para o texto.

## Como isso apareceu

Fui conferir os JSONs versionados em `results/tables/` contra o código antes de
começar a F4, e os números não fechavam.

```bash
# results/tables/eda_stats.json
"n_docs": 113827
# results/tables/segmenter_validation.json
"n_docs": 113827
```

Mas o `ingest.py` filtra o corpus pelas chaves referenciadas pelo JurisTCU:

```python
# juris-chunking/src/ingest.py, load_tcu_acordaos()
if key is None or key in by_key or key not in wanted_keys:
    continue
```

## A evidência

**1. Quantas chaves de join o JurisTCU realmente tem?** Medido diretamente
sobre o `doc.csv` baixado, replicando a função `_join_key` do próprio repo:

```
docs JurisTCU      : 16045
sem chave de join  : 207
CHAVES UNICAS      : 12881
```

12.881 bate exatamente com o número do `plano_implementacao.md`. Logo
`wanted_keys` tem 12.881 entradas, e o corpus filtrado **não pode** passar
disso — muito menos chegar a 113.827.

**2. O que aconteceu, na palavra do próprio autor.** A mensagem do commit
`92828d4` (Igor Mamus, 24/08/2026) diz, textualmente:

> "validated against the gold spans on the **full 113k-doc corpus**, 92.7% char
> accuracy, 1.6% fallback rate"

Ou seja: a validação **foi mesmo rodada** com 113k documentos. O que ocorreu foi
a ordem dos fatos:

1. rodou o `ingest` **sem** o filtro → corpus = todos os acórdãos dos CSVs do TCU (113.827);
2. gerou `eda_stats.json` e `segmenter_validation.json` a partir dessa rodada;
3. **depois** adicionou o filtro `wanted_keys`, descrito no docstring como
   otimização ("evita normalizar os outros ~101k à toa") — mas que também
   **muda o corpus final**, não só o custo de CPU;
4. commitou as duas coisas juntas, sem regenerar os JSONs.

`git log` confirma que filtro e tabelas entraram no mesmo commit:

```bash
git log --oneline -S "key not in wanted_keys" -- juris-chunking/src/ingest.py
# 92828d4 Add corpus ingestion (F1) and structural segmenter (F2)
git log --oneline -- results/tables/
# 92828d4 Add corpus ingestion (F1) and structural segmenter (F2)
```

**Conclusão:** o Igor está certo quando diz que "está funcionando" — o código
roda e os 39 testes passam. As duas coisas são verdade ao mesmo tempo. O
problema não é o código, é que **o número publicado no artigo veio de uma
versão anterior dele**.

## Por que isso é urgente (e não um detalhe de bookkeeping)

Estes números, hoje no artigo e no pôster, **todos** vêm da rodada de 113k:

| Número | Onde aparece | Corpus que o gerou |
|---|---|---|
| 113.827 documentos indexáveis | artigo §Materials, Tabela I, pôster | 113k (obsoleto) |
| mediana 7.347 tokens/doc (p90 24.163, p99 71.480) | artigo §Materials, Fig. 2, pôster | 113k (obsoleto) |
| relatório = 72,5% dos caracteres, ementa = 1,0% | artigo §Materials, Fig. 2 | 113k (obsoleto) |
| 92,7% de acurácia do segmentador, 1,6% fallback | artigo §F2, pôster | 113k (obsoleto) |

Se rodarmos o pipeline hoje e publicarmos os resultados, **nenhuma dessas
estatísticas vai reproduzir**. Uma banca que peça "rode aí" encontra a
divergência na hora.

## O trade-off real (com números)

Estimativa de custo de embedding denso, usando a média de 11.651 tokens/doc
medida no EDA e as 5 estratégias de chunking do `chunkers.yaml`:

| | **A — corpus filtrado** (código atual) | **B — corpus completo** (artigo) |
|---|---|---|
| Documentos | 12.881 | 113.827 |
| Tokens totais | ~150 M | ~1,33 B |
| Chunks (5 estratégias) | ~1,38 M | ~12,2 M |
| Encode denso em **CPU** (~25 chunks/s) | **15,3 h** (roda de madrugada) | **135,5 h ≈ 5,6 dias** ❌ |
| Encode denso em **GPU T4** (Colab) | **1,3 h** | 11,3 h (várias sessões, com risco de desconexão) |

O artigo afirma que o cenário de ~100k documentos é *"compatible with personal
hardware and Google Colab"*. **Isso não se sustenta para o retriever denso**:
são 5,6 dias de CPU contínua, ou ~11 h de GPU num Colab gratuito que
desconecta. Essa frase precisa mudar independentemente de qual corpus a gente
escolher.

## Minha recomendação: ficar com A (12.881) e corrigir o artigo

Não é só pelo custo — tem um argumento **metodológico** que acho mais forte:

1. **Paridade com o benchmark de referência.** O JurisTCU (arXiv:2503.08379),
   que é de onde vêm nossas 150 queries e 2.250 qrels, avalia sobre
   **16.045 documentos**. Um corpus de 12.881 acórdãos íntegros é o análogo
   direto — mesma ordem de grandeza, mesma densidade de relevância — mudando
   **uma variável só**: o documento passa a ser o acórdão íntegro em vez do
   enunciado+excerto. Essa é exatamente a contribuição que o trabalho quer
   isolar.
2. **Ir para 113.827 mexe em duas variáveis ao mesmo tempo** (tamanho do
   documento *e* tamanho da coleção). Aí fica impossível dizer se uma diferença
   de nDCG@10 veio do chunking estrutural ou de ter 9x mais distratores.
3. O custo cabe no cronograma; o do cenário B não cabe.

**Contra-argumento honesto, que a banca pode levantar:** um corpus formado
*apenas* por acórdãos que originaram algum enunciado do JurisTCU é uma coleção
enviesada — todo documento nela já foi, em algum momento, considerado
jurisprudencialmente relevante. Isso torna a tarefa de recuperação mais fácil
(e menos realista) do que buscar num acervo completo. **Isso precisa estar
declarado como limitação no artigo**, junto com a limitação já reconhecida de
que a relevância foi julgada sobre o excerto e transferida ao acórdão inteiro.

**Alternativa intermediária, se quisermos responder a esse contra-argumento:**
12.881 referenciados + uma amostra aleatória de ~40k acórdãos não referenciados
como distratores (~53k docs, custo ~4x o de A, ~5 h de CPU). Fica mais
realista sem estourar o cronograma. Só vale se sobrar tempo depois da F5.

## O que precisa ser decidido (não é decisão minha sozinho)

- [ ] **Qual corpus é o oficial?** A (12.881), B (113.827) ou C (~53k com distratores)?
- [ ] Regenerar `eda_stats.json` e `segmenter_validation.json` no corpus escolhido.
- [ ] Corrigir no artigo: contagem de documentos, Figura 2, estatísticas de seção,
      acurácia do segmentador e a frase sobre viabilidade em Colab.
- [ ] Adicionar a limitação de viés de coleção (se ficarmos com A).

**Enquanto isso não for decidido, nenhum desses números deve ir para a versão
final do artigo.** Falar com o Igor — ele é o autor da F1/F2 e pode ter tido uma
razão para o filtro que não está escrita em lugar nenhum.
