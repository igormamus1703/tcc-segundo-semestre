# Para retomar o projeto numa nova sessão

**Cole este arquivo inteiro no início da próxima conversa.** Ele carrega o
contexto necessário para continuar sem redescobrir nada.

**Escrito em:** 07/09/2026 · **Atualizado em:** 28/09/2026
**Prazo da entrega final:** ~5 semanas

---

## 1. Contexto em 30 segundos

TCC de RI jurídica (PUCPR, 4 alunos). Pergunta original: *chunking que respeita
as macro-seções do acórdão melhora a recuperação, comparado a chunking fixo e
recursivo?*

Corpus: **12.880 acórdãos íntegros do TCU** (2003–2023), com as 150 consultas e
2.219 qrels do **JurisTCU**. Dois retrievers: **BM25** (`bm25s`) e **denso**
(`BAAI/bge-m3` em GPU). Cinco estratégias de chunking. Métricas: nDCG@10,
MRR@10, MAP@10, Recall@100, com significância pareada e IC 95%.

**F0–F5 concluídas e mergeadas.** **F6 concluída e NÃO mergeada**, na branch
`leo/f6-secoes-e-fusao` — é onde está tudo o que é novo.

Leia, nesta ordem: **`PLANO.md`** (estado e próximos passos) →
**`RESULTADOS-F6.md`** (o que mudou em 28/09, escrito para apresentar) →
`docs/docsleo/branches/leo-f6-secoes-e-fusao/` (o detalhe com os artefatos).

---

## 2. O resultado, sem enfeite

### A pergunta original: resposta nula, e ela se sustentou

| Estratégia | BM25 | Denso |
|---|---:|---:|
| structural_pred | **0,2526** | 0,1912 |
| structural_gold | 0,2521 | 0,1847 |
| fixed_1024_512 | 0,2510 | 0,2019 |
| fixed_512_256 | 0,2486 | **0,2055** |
| recursive_default | 0,2412 | 0,1967 |

**A hipótese não se confirmou.** Um de 20 pares com p < 0,05, e ele aponta
*contra*. A ordem se inverte entre os retrievers. **E em 28/09 o empate foi
confirmado num segundo ponto de operação** (com recorte por seção, 16% acima):
10 pares, menor p = 0,056. Um empate que sobrevive a uma mudança grande no
desempenho absoluto é evidência bem mais forte que um empate medido uma vez.

### A pergunta derivada: resposta positiva e significativa

| Configuração (`fixed_512_256`) | nDCG@10 | MRR@10 | MAP@10 | R@100 |
|---|---:|---:|---:|---:|
| BM25, índice completo (baseline) | 0,2486 | 0,5186 | 0,0963 | 0,4709 |
| BM25, −67% **aleatório** (controle) | 0,2260 | 0,4725 | 0,0867 | 0,4310 |
| BM25, **sem o relatório** | 0,2904 | 0,5889 | 0,1190 | 0,4993 |
| sem o relatório **+ fusão (peso por CV)** | 0,3160 | **0,6058** | 0,1330 | 0,5259 |
| **fusão das 4 condições, peso igual** | **0,3215** | 0,6000 | **0,1402** | **0,5479** |

**+29,3% de nDCG@10, p < 0,00001**, com Bonferroni sobre 28 pares. As quatro
métricas sobem. A melhor configuração funde quatro rankings com **peso
igual** — não tem hiperparâmetro, logo não há como ajustar no conjunto de
teste. A versão ponderada (0,3160) usa peso escolhido por validação cruzada e
empata com ela (p = 0,338); a vantagem dela é precisar só dos índices
recortados, com um terço do tamanho.

---

## 3. O que a F6 acrescentou, e por que cada peça importa

1. **Recorte por seção virou pipeline** (`--secoes sem:relatorio`). Roda nos
   dois retrievers e nas **cinco** estratégias — nas fixas e na recursiva a
   seção do chunk vem do *offset*, não de rótulo. **+11% a +17% no BM25**
   (todas significativas), **+12% a +28% no denso**.

2. **O controle pareado** (`--amostra-igual-a sem:relatorio`) é a peça que
   torna isso uma afirmação causal. Descartar o **mesmo número** de chunks,
   sorteados, **piora** o nDCG@10 (−8% a −17%). Mesmo tamanho de índice,
   efeitos opostos: o ganho é da estrutura do acórdão.

3. **Fusão BM25 + denso** (`src/fusion.py`, `src/tuning.py`). O denso não era
   inútil, era complementar: +4,4% a +8,6% sobre o BM25, e **soma com o
   recorte**. O peso sai de validação cruzada por consulta, com um teste que
   espiona a seleção e proíbe a dobra de teste de participar dela. E a melhor
   variante — fundir as **quatro** condições com peso igual — chega a +19,5% a
   +29,3% nas cinco estratégias **sem hiperparâmetro nenhum**.

4. **O ganho não vem das consultas fáceis.** Nas consultas reais de log (as
   mais difíceis, nDCG de 0,13): **+18,2%**. Nas sintéticas: +29,6% e +33,6%.

5. **Três coisas foram testadas e descartadas**, com o motivo medido:
   ponderação por seção, RRF sem peso e `sum_top_k`. Estão em
   `docs/docsleo/branches/leo-f6-secoes-e-fusao/resultados/05-negativos.md` —
   leia antes de tentar de novo.

6. **O resultado foi auditado contra 10 ameaças de validade**
   (`04-auditoria-de-validade.md`). As três que mais importam:
   - **dose-resposta**: o efeito acompanha a concentração de relevância da
     seção. Remover a ementa (0,4% da relevância) não faz nada; remover a
     fundamentação (72%) custa −17,5%; indexar **só** o relatório — 72% do
     texto — é 21,5% pior que indexar tudo;
   - **circularidade**: a decisão de cortar o relatório veio dos próprios
     rótulos de relevância. Testada por CV sobre 10 candidatos: as 5 dobras
     escolhem a mesma configuração e o ganho **fora** da escolha é +16,2%
     (p = 0,000275);
   - ⚠️ **a limitação que fica**: o JurisTCU julga excertos de jurisprudência,
     que saem do voto por construção. A conclusão vale para "achar o acórdão
     que firma uma tese"; para quem busca fatos do caso concreto, pode
     inverter. **Isso precisa estar no artigo.**

7. **182 testes** (eram 115). Três bugs reais foram achados em execução, e os
   três produziam resultado plausível e errado: uma colisão de nome de run que
   apagava uma linha da tabela; um colapso de condições que fazia a figura
   mostrar menos barras do que condições; e — o mais sério — **empate de score
   na fronteira da métrica**, que fazia o mesmo arquivo TREC dar dois valores
   diferentes no mesmo recorte. Ver
   `docs/docsleo/branches/leo-f6-secoes-e-fusao/03-empate-de-score.md`.

   ⚠️ **O terceiro afeta a F5 também.** Os recortes, IC 95% e análise de poder
   das rodadas antigas foram calculados com o bug. O efeito é de terceira casa
   e nenhuma conclusão muda, mas **quem for citar um número de recorte da F5
   no artigo deve regerar a tabela antes** (`python -m src.evaluate
   --experiment <rodada>`).

---

## 4. O que fazer agora — em ordem de valor

### 🔴 1. Passar a branch para a equipe e decidir o merge

`leo/f6-secoes-e-fusao` está pronta e verde, mas **não foi mergeada**, porque
muda a tese do artigo. Checklist e pontos de atenção no
`docs/docsleo/branches/leo-f6-secoes-e-fusao/README.md`.

### 🔴 2. A decisão de corpus continua aberta

Artigo diz 113.827, código produz 12.880. Todos os números da F5 **e da F6**
são do corpus de 12.880. Detalhe em
`docs/docsleo/branches/leo-f4-indexacao-e-docs/02-achado-corpus.md`.
Ficou **mais** urgente: agora há um resultado forte a publicar.

### 🟠 3. Reescrever o artigo com as duas perguntas

A Introdução, os Resultados e a Conclusão mudam. A estrutura sugerida:
a pergunta sobre *granularidade* tem resposta nula e bem medida; a pergunta
sobre *seleção de conteúdo*, que nasceu dela, tem resposta positiva. Os onze
números a corrigir continuam listados em
`docs/docsleo/branches/leo-f4-indexacao-e-docs/07-numeros-para-o-artigo.md`.

### 🟡 4. O que sobrou de experimento, em ordem de custo/benefício

| Ideia | Custo | Por que vale |
|---|---|---|
| **Densidade informativa** sem usar a estrutura (tamanho de sentença, densidade de termos jurídicos) | médio | A auditoria mostrou que o efeito acompanha a densidade de relevância, não o relatório em si; falta a versão que dispensa segmentar. É a contribuição mais geral possível |
| **Consultas dirigidas a fatos do caso concreto** | alto | Testaria se o recorte inverte de sinal. É a limitação do §10 da auditoria, e não dá para testar com o JurisTCU como ele é |
| Explicar o recall subir no BM25 e cair no denso | baixo | Hipótese registrada, medição não feita. É uma pergunta que a banca vai fazer |
| **Chunk com prefixo de seção** (`"[voto] …"`) | ~10 h GPU | Exige reencode |
| **Reranking com cross-encoder** no top-100 | alto | O que mais rende em RI |
| **Expansão de consulta** (docT5query) | alto | O JurisTCU mediu +47%. Fora do escopo; é o item mais forte de trabalhos futuros |

---

## 5. Estado técnico (para não redescobrir)

| | |
|---|---|
| Ambiente | Python 3.13.7, venv em `C:\venvs\tcc-juris`, `torch 2.14.0+cu130` |
| GPU | RTX 5060 (8 GB) — encode a ~48 chunks/s com bge-m3 fp16 |
| Dados | `C:\data\tcc-segundo-semestre` (junction), 6 GB |
| Cache de embeddings | `juris-chunking/data/processed/<estrategia>/emb_*.npy` — **não apagar**, custou ~10 h de GPU |
| Branch atual | `leo/f6-secoes-e-fusao` (não mergeada) |

**O cache agora serve subconjuntos.** É o que faz o recorte por seção no denso
custar **4 minutos** em vez de 10 h: `DenseIndex._load_cache` seleciona as
linhas por `chunk_id` quando os chunks pedidos são um subconjunto dos
cacheados. Com recorte ativo o cache é **somente leitura**, para um encode
parcial nunca substituir o completo.

### Comandos que importam

```bash
cd juris-chunking
pytest -q                                              # 182 testes

# F4/F5 — as rodadas base
python -m src.run_experiments --strategy all --retriever bm25
python -m src.run_experiments --strategy all --retriever dense   # usa o cache
python -m src.evaluate                                 # tabelas da rodada mais recente
python -m src.evaluate --incluir <outra-rodada>        # cruza BM25 e denso

# F6 — recorte, controle, fusão
python -m src.run_experiments --strategy all --retriever bm25 --secoes sem:relatorio
python -m src.run_experiments --strategy all --retriever bm25 --amostra-igual-a sem:relatorio
python -m src.fusion --experimentos <bm25> <denso> --metodo rrf

# a MELHOR configuracao: funde as 4 condicoes com peso igual, sem parametro
python -m src.fusion --metodo soma_norm --label fusao4_peso_igual \
    --experimentos <bm25> <bm25-sem-rel> <denso> <denso-sem-rel>
python -m src.tuning  --bm25 <bm25> --denso <denso>    # peso por validacao cruzada

# tabela do artigo, a partir de runs avulsos, e figuras
python -m src.evaluate --label comparacao --runs a.trec b.trec ...
python -m src.plots --experiment <rodada> --referencia <run-baseline>
```

> `--secoes sem:relatorio` e `--secoes=-relatorio` são a mesma coisa. A segunda
> **só** funciona colada: solta, o argparse lê `-relatorio` como opção e aborta.

### Já tentado e que NÃO funciona (não repetir)

| Tentativa | O que aconteceu |
|---|---|
| `gte-multilingual-base` | `device-side assert` do CUDA, em fp16 e fp32 |
| ONNX Runtime | `optimum` rebaixa o `transformers` e quebra o `sentence-transformers` |
| `torch.compile` + TF32 | 0,99x, sem ganho |
| Deduplicar chunks entre estratégias | 0,4% de redundância |
| Encode em CPU | 4,8 chunks/s → 127 h |
| `multilingual-e5-base` | Janela de 512 truncaria 83% dos chunks |
| **Ponderar a seção** em vez de cortar | Satura no corte binário e não preserva o recall — o peso é aplicado depois do corte em `--top-chunks` |
| **RRF sem peso** | p entre 0,206 e 0,906: peso igual a um retriever 20% pior anula o ganho |
| **`sum_top_k`** | Perde do `max_pooling` em 4 de 5 estratégias |
| **Confiar na ordem que o ranx devolve os scores por consulta** | Empates de score na fronteira do `@k` fazem o mesmo run dar números diferentes. `per_query_scores` desempata por `doc_id` antes de avaliar |

---

## 6. Como abrir a próxima conversa

Cole este arquivo e diga o que quer atacar. Três aberturas úteis:

> "Retomando o TCC. Li o CONTINUAR-AQUI.md. A equipe aprovou a F6 — faça o
> merge de `leo/f6-secoes-e-fusao` na `main` e atualize os `.md` da raiz."

> "Retomando o TCC. Li o CONTINUAR-AQUI.md. Quero atacar o item 4 da §4: um
> critério de densidade informativa que não use a estrutura do acórdão, para
> ver se o ganho do recorte é sobre *o relatório* ou sobre *texto de baixa
> densidade* em geral."

> "Retomando o TCC. Li o CONTINUAR-AQUI.md. A equipe decidiu o corpus: [X].
> Preciso corrigir os números do artigo e do pôster conforme o
> 07-numeros-para-o-artigo.md, e reescrever os Resultados com a tabela da F6."

**Regras do projeto que valem em qualquer sessão** (estão no `README.md`):
branch → testar → anotar em `docs/docs<seu-nome>/` → merge. Commits sem
co-autoria de ferramenta. Nenhum número vai para o artigo sem o artefato que o
comprova.
