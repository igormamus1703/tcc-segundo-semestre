# Para retomar o projeto numa nova sessão

**Cole este arquivo inteiro no início da próxima conversa.** Ele carrega o
contexto necessário para continuar sem redescobrir nada.

**Escrito em:** 07/09/2026 · **Prazo da entrega final:** ~2 meses

---

## 1. Contexto em 30 segundos

TCC de RI jurídica (PUCPR, 4 alunos). Pergunta: *chunking que respeita as
macro-seções do acórdão melhora a recuperação, comparado a chunking fixo e
recursivo?*

Corpus: **12.880 acórdãos íntegros do TCU** (2003–2023), com as 150 consultas e
2.219 qrels do **JurisTCU**. Dois retrievers: **BM25** (`bm25s`) e **denso**
(`BAAI/bge-m3` em GPU). Cinco estratégias de chunking. Métricas: nDCG@10,
MRR@10, MAP@10, Recall@100, com significância pareada e IC 95%.

**Tudo do plano original está feito.** F0–F5 concluídas, 115 testes,
experimento rodado nos dois retrievers, documentação e figuras.

Leia, nesta ordem: **`PLANO.md`** (estado e próximos passos) →
`docs/docsleo/branches/leo-f4-indexacao-e-docs/` (achados detalhados).

---

## 2. O resultado, sem enfeite

| Estratégia | BM25 | Denso |
|---|---:|---:|
| structural_pred | **0,2526** | 0,1912 |
| structural_gold | 0,2521 | 0,1847 |
| fixed_1024_512 | 0,2510 | **0,2019** |
| fixed_512_256 | 0,2486 | *(ver `results/`)* |
| recursive_default | 0,2412 | 0,1967 |

**A hipótese não se confirmou.** Zero de 16 pares de estratégias com p < 0,05,
nos dois retrievers. A ordem ainda se inverte entre eles (estruturais lideram
no BM25, ficam por último no denso), o que é evidência **contra** um efeito
estável do chunking.

**O único resultado significativo:** o BM25 supera o denso com p < 0,001 nas
quatro estratégias comparadas.

---

## 3. Por que isto NÃO é "o mesmo resultado que já existe"

Essa foi a leitura inicial e ela **subestima o que foi medido**. O que já
existia era o BR-TaxQA-R mostrando que uma janela deslizante grande vence um
splitter recursivo pequeno, **avaliando geração**. Nada além disso.

O que este trabalho tem **e não existe na literatura**:

1. **A ablação `gold` × `pred`.** Comparamos o chunking feito com a estrutura
   *ouro* (as colunas do CSV do TCU) contra o feito por um segmentador de
   regras com 92,2% de acurácia. Resultado: **p = 0,827 no BM25, com 97 empates
   em 150 consultas**, e o *predito* ligeiramente à frente. Ou seja: **não é
   preciso ter a estrutura ouro** — o que importa para qualquer um que queira
   aplicar isso num acervo real, onde não existe coluna `VOTO` pronta. Nenhum
   trabalho fez essa ablação.

2. **Onde mora a relevância num acórdão.** Localizamos os excertos julgados
   relevantes dentro dos documentos: a **fundamentação (o voto) ocupa 22,8% do
   texto e concentra 72,0% da relevância** (3,2x), enquanto o relatório tem
   69,9% do texto e só 25,7% da relevância. A posição mediana do trecho
   relevante é a **79% do documento**. Isso é medição original sobre o domínio.

3. **O descompasso** — e este é o achado mais forte. **Os dois retrievers
   recuperam predominantemente pelo relatório (65–74% dos chunks vencedores),
   que é justamente a parte com menos relevância.** Eles acham o termo onde há
   *mais texto*, não onde há *mais informação*. Ver §4: isso aponta para uma
   solução.

4. **BM25 > denso com significância em documentos longos.** O JurisTCU mostrou
   embeddings da OpenAI vencendo o BM25 em documentos curtos. Nós mostramos o
   oposto em acórdãos íntegros, com p < 0,001. É contraintuitivo e mensurado.

5. **Controle de granularidade.** O BR-TaxQA-R comparou 2.048 *tokens* contra
   1.000 *caracteres* — 8x de diferença. Não estavam testando estrutura,
   estavam testando tamanho. Nós comparamos chunks do mesmo tamanho.

6. **Quantificação do custo de documento longo.** Nosso BM25 fica em 0,51–0,60
   do nDCG@10 do JurisTCU, **de forma estável nos três grupos de consulta**.
   Razão constante = diferença de dificuldade da tarefa, não defeito de
   pipeline. Poucos trabalhos medem isso.

**Um resultado nulo com quatro achados originais em volta é um TCC completo.**
O `plano_tecnico.md` §7 já dizia isso. Mas dá para ir além — é o §4.

---

## 4. ✅ JÁ TESTADO, E FUNCIONOU — é por aqui que o TCC fica forte

A pergunta era: *se 72% da relevância está na fundamentação e os retrievers
recuperam 70% pelo relatório, o que acontece se indexarmos só a parte que
importa?*

**Testado em 07/09, com o cache existente. Funciona, e é significativo:**

| Configuração | Chunks | nDCG@10 | vs baseline | p |
|---|---:|---:|---:|---:|
| completo (baseline) | 286.689 | 0,1853 | — | — |
| **tudo menos o relatório** | **95.300** | **0,2167** | **+16,9%** | **0,00098** ✅ |
| só fundamentação | 64.629 | 0,2104 | +13,5% | 0,0128 ✅ |
| sem relatório, com spans **preditos** | 95.300 | 0,2147 | +12,3% | 0,0165 ✅ |

**E não depende da estrutura ouro:** ouro × predito dá p = 0,722, com 47
empates em 150 consultas. O segmentador de 92,2% entrega o mesmo ganho — é isso
que torna o achado aplicável fora do TCU.

**Trade-off a declarar:** o Recall@100 cai de 0,4224 para 0,3928 (−7%). Ganha-se
precisão no topo, perde-se cobertura na cauda.

Detalhe completo em
`docs/docsleo/branches/leo-f4-indexacao-e-docs/resultados/05-filtragem-por-secao.md`.

> **O que isso faz pelo TCC:** reformula a pergunta de *"como cortar o
> documento?"* (resposta medida: tanto faz) para **"qual parte do documento
> indexar?"** — que tem resposta, com mecanismo medido *antes* da intervenção e
> ganho estatisticamente significativo. Deixa de ser um trabalho com resultado
> nulo e passa a ser um trabalho com um resultado nulo **e** uma descoberta.

### O que falta para virar resultado do artigo

Foi um teste exploratório, num script fora do `src/`. Antes de publicar:

1. **Reimplementar no pipeline** como opção de indexação
   (`--secoes fundamentacao,ementa,dispositivo`), com testes
2. **Rodar no BM25** — só testamos no denso, e o BM25 é o retriever mais forte
   do trabalho
3. Testar a variante **ponderada** (peso por seção em vez de corte binário),
   que talvez preserve o recall
4. Verificar o efeito **por tipo de consulta**, sobretudo nas consultas reais
5. Bootstrap de IC 95% e análise de poder, como nos demais resultados

### A pergunta original, que agora tem resposta parcial

Isso muda a pergunta do trabalho de *"como cortar o documento?"* (respondida:
tanto faz) para **"qual parte do documento indexar?"** — que é uma pergunta
melhor, com um mecanismo já medido por nós para justificá-la.

**Variantes ainda não testadas, da mais barata para a mais cara:**

1. ~~Filtrar por seção~~ — **feito, funciona** (acima)
2. **Ponderar por seção**: multiplicar o score do chunk por um peso conforme a
   seção, em vez do corte binário. Reusa o cache; pode preservar o recall.
3. **Chunk com contexto de seção**: prefixar cada chunk com o nome da sua
   seção antes de encodar (ex.: `"[voto] ..."`). Exige reencode (~10 h).

Outras ideias, se sobrar tempo, em ordem de custo/benefício:

4. **Fusão híbrida BM25 + denso** (Reciprocal Rank Fusion). Barata — só combina
   os runs que já existem. A literatura mostra ganho consistente, e nós temos os
   dois retrievers medidos.
5. **Reranking com cross-encoder** no top-100. Caro, mas é o que mais costuma
   render em RI.
6. **Expansão de consulta** (docT5query / sinônimos). O JurisTCU mediu **+47%**
   com isso. Está fora do escopo declarado, mas é o item mais forte da seção de
   trabalhos futuros.

> ⚠️ **Cuidado metodológico:** os itens 1 e 2 usam os `gold_spans`, que só
> existem porque o TCU publica o acórdão em colunas. Para a conclusão ser
> aplicável a um acervo real, teste também com os spans **preditos** pelo
> segmentador — que é exatamente a ablação `gold`/`pred` que já temos montada.

---

## 5. O que está bloqueado esperando a equipe

### 🔴 A decisão do corpus (bloqueia tudo o que for para o artigo)

O artigo e o pôster dizem **113.827 documentos**; o código produz **12.880**.
Não é bug — é mudança de escopo de agosto que não foi propagada. Detalhe em
`docs/docsleo/branches/leo-f4-indexacao-e-docs/02-achado-corpus.md`.

**Ficou mais urgente** depois que o trabalho passou a ter um resultado
significativo: um número significativo medido no corpus errado vira afirmação
forte e errada no artigo.

### 🟠 Onze números do artigo mudam

Lista com "de → para" em
`docs/docsleo/branches/leo-f4-indexacao-e-docs/07-numeros-para-o-artigo.md`.
Inclui refazer a Figura 2 e remover a afirmação de que ~100k documentos rodam
em "personal hardware and Google Colab" — não rodam.

---

## 6. Estado técnico (para não redescobrir)

| | |
|---|---|
| Ambiente | Python 3.13.7, venv em `C:\venvs\tcc-juris`, `torch 2.14.0+cu130` |
| GPU | RTX 5060 (8 GB) — encode a ~48 chunks/s com bge-m3 fp16 |
| Dados | `C:\data\tcc-segundo-semestre` (junction), 6 GB |
| Cache de embeddings | `juris-chunking/data/processed/<estrategia>/emb_*.npy` — **não apagar**, custou ~10 h de GPU |
| Branch | `leo/f4-indexacao-e-docs` |

**Comandos que importam:**

```bash
cd juris-chunking
pytest -q                                              # 115 testes
python -m src.run_experiments --strategy all --retriever bm25
python -m src.run_experiments --strategy all --retriever dense   # usa o cache
python -m src.evaluate                                 # tabelas da rodada mais recente
python -m src.evaluate --incluir <outra-rodada>        # cruza BM25 e denso
python -m src.plots                                    # figuras com rodapé de contexto
```

### Já tentado e que NÃO funciona (não repetir)

| Tentativa | O que aconteceu |
|---|---|
| `gte-multilingual-base` | `device-side assert` do CUDA, em fp16 e fp32 |
| ONNX Runtime | `optimum` rebaixa o `transformers` e quebra o `sentence-transformers` |
| `torch.compile` + TF32 | 0,99x, sem ganho |
| Deduplicar chunks entre estratégias | 0,4% de redundância |
| Encode em CPU | 4,8 chunks/s → 127 h |
| `multilingual-e5-base` | Janela de 512 truncaria 83% dos chunks e enviesaria a comparação |

---

## 7. Como abrir a próxima conversa

Cole este arquivo e diga algo como:

> "Retomando o TCC. Li o CONTINUAR-AQUI.md. Quero atacar a ideia do §4 —
> filtrar/ponderar por seção — para ver se conseguimos um resultado positivo
> antes da entrega. Comece pela variante mais barata, usando o cache que já
> existe, e me diga o que os números mostram antes de irmos adiante."

Ou, se a prioridade for fechar o texto:

> "Retomando o TCC. Li o CONTINUAR-AQUI.md. A equipe decidiu o corpus: [X].
> Preciso corrigir os números do artigo e do pôster conforme o
> 07-numeros-para-o-artigo.md, e revisar a Discussão com os resultados atuais."

**Regras do projeto que valem em qualquer sessão** (estão no `README.md`):
branch → testar → anotar em `docs/docs<seu-nome>/` → merge. Commits sem
co-autoria de ferramenta. Nenhum número vai para o artigo sem o artefato que o
comprova.
