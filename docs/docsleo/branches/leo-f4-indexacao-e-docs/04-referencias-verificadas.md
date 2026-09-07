# Verificação das referências do artigo

**Data:** 2026-09-05 · **Autor:** Leonardo Marques · **Status:** ✅ concluído

O `plano_tecnico.md` §5 é explícito: *"Nenhum destes entra na bibliografia sem
que alguém tenha o PDF na mão. Citação fantasma em TCC é o tipo de erro que a
banca encontra e não perdoa."* Como o artigo já foi escrito citando 8 trabalhos
— vários deles de 2026, portanto recentes demais para estarem no meu
conhecimento prévio — verifiquei **cada um** contra a página oficial do arXiv.

## Resultado: nenhuma citação fantasma ✅

| Chave BibTeX | arXiv | Título confirmado | Autor(es) | Ano | ✓ |
|---|---|---|---|---|---|
| `fernandes2025juristcu` | 2503.08379 | JurisTCU: A Brazilian Portuguese Information Retrieval Dataset with Query Relevance Judgments | L. C. Fernandes, L. S. Ribeiro, M. V. B. de Castro, L. A. S. Pacheco, E. F. O. Sandes | 2025 | ✅ |
| `domingos2025brtaxqar` | 2505.15916 | BR-TaxQA-R: A Dataset for Question Answering with References for Brazilian Personal Income Tax Law | J. Domingos Júnior, A. Faria, E. Seiti de Oliveira, E. de Brito, M. Teotonio, A. Assumpção, D. Carmo, R. Lotufo, J. Pereira | 2025 | ✅ |
| `demartim2026beyond` | 2606.09724 | Beyond Probabilistic Similarity: Structural, Temporal, and Causal Limitations of RAG in the Legal Domain | Hudson de Martim | 2026 | ✅ |
| `demartim2025ontology` | 2505.00039 | An Ontology-Driven Graph RAG for Legal Norms: A Structural, Temporal, and Deterministic Approach | Hudson de Martim | 2025 | ✅ |
| `pereira2026jua` | 2604.06098 | JUÁ — A Benchmark for Information Retrieval in Brazilian Legal Text Collections | J. Pereira, L. Fernandes, E. de Brito, R. Lotufo, L. Bonifacio | 2026 | ✅ |
| `stekel2026mtebbr` | 2607.04581 | MTEB-BR: A Text Embedding Benchmark for Brazilian Portuguese | Tardelli Ronan Coelho Stekel | 2026 | ✅ |
| `butler2026legalragbench` | 2603.01710 | Legal RAG Bench: an end-to-end benchmark for legal RAG | Abdur-Rahman Butler, Umar Butler | 2026 | ✅ |
| `carvalho2026legalbenchbr` | 2604.18878 | LegalBench-BR: A Benchmark for Evaluating LLMs on Brazilian Legal Decision Classification | Pedro Barbosa de Carvalho Neto | 2026 | ✅ |

Canônicos não verificados individualmente por serem amplamente conhecidos e
estáveis: `lewis2020rag` (RAG, NeurIPS 2020), `karpukhin2020dpr` (DPR, EMNLP
2020), `khattab2020colbert` (ColBERT, SIGIR 2020).

## Correções e ajustes a fazer no artigo

**1. `demartim2025ontology` — atualizar o venue.** O artigo hoje cita como
arXiv + "IOS Press, FAIA251598". A versão v5 (11/09/2025) confirma que foi
**aceito no JURIX 2025** (Legal Knowledge and Information Systems, IOS Press).
Citar a publicação na conferência em vez do preprint pega melhor com a banca.

**2. `demartim2026beyond` — o vocabulário que usamos está correto.** O paper
define exatamente os três termos: *mereological blindness*, *diachronic
blindness* e *causal opacity*. Nosso artigo usa "mereological blindness" na
introdução, e está fiel à fonte.

**3. `butler2026legalragbench` — o argumento que usamos se sustenta.** O achado
central confirmado é que *"a recuperação de informações é o impulsionador
primário do desempenho legal RAG"* e que muitos erros atribuídos a alucinação
são, na verdade, falhas de recuperação. **É esta a nossa justificativa para
avaliar só recuperação e não geração** — se alguém na banca perguntar "por que
vocês não avaliam a resposta final?", a resposta é essa citação.

**4. `domingos2025brtaxqar` — RESOLVIDO, e o achado é ótimo para nós.**

Fui ao texto completo (arXiv HTML v1). O que o BR-TaxQA-R realmente comparou:

| Estratégia | Parâmetros | Response Relevancy | Factual Correctness |
|---|---|---|---|
| Sliding-window | 2.048 tokens / stride 1.024 | **0,819** | **0,313** |
| Recursive splitter | 1.000 **caracteres** / 100 de overlap, com separadores hierárquicos | 0,791 | 0,286 |

Conclusão literal deles: *"simple sliding-window segmentation achieves good
results, and that incorporating relevant jurisprudence further improves
performance"*. A abordagem simples **superou** a que tentava explorar a
estrutura hierárquica.

**Ou seja: sim, é evidência contrária à nossa hipótese. A frase do artigo está
correta e deve ficar.** Mas ao ler o detalhe aparecem três limitações
metodológicas que são exatamente o espaço que o nosso trabalho ocupa — e isso
precisa estar explícito na seção de Trabalhos Relacionados:

1. **A comparação deles confunde estrutura com tamanho de chunk.** 2.048
   *tokens* contra 1.000 *caracteres* (≈250 tokens) é uma diferença de ~8x na
   granularidade. Não dá para saber se o sliding-window ganhou por ser
   "estrutura-cego" ou simplesmente por ter 8x mais contexto por chunk. **Nós
   controlamos isso**: as cinco estratégias são medidas com o mesmo tokenizador
   (`cl100k_base`) e faixas de tamanho comparáveis (512/1024 tokens).

2. **O "recursive com separadores hierárquicos" deles não é um chunker
   estrutural.** É um splitter genérico com uma lista de separadores — não há
   segmentador que identifique as macro-seções do documento e proíba o chunk de
   cruzar fronteira. **Nós temos um segmentador de verdade, validado
   (92,2% por caractere), e ainda a ablação `gold` vs `pred`** para separar o
   efeito da estrutura do efeito do erro de segmentação. Essa ablação não
   existe no trabalho deles.

3. **Eles avaliam geração (RAGAS), nós avaliamos recuperação.** As métricas do
   BR-TaxQA-R são Response Relevancy e Factual Correctness, medidas sobre a
   resposta final — o que coloca o LLM gerador como variável de confusão entre
   o chunking e o número reportado. Nós medimos nDCG@10 / MRR@10 / MAP@10 /
   Recall@100 diretamente sobre a recuperação. E o Legal RAG Bench
   (`butler2026legalragbench`) mostra que **a recuperação é o determinante
   principal** do desempenho — logo, medi-la isoladamente é mais informativo,
   não menos.

> 💡 **Para a banca:** se perguntarem "o BR-TaxQA-R já não mostrou que chunking
> estrutural não ajuda?", a resposta é: eles mostraram que um splitter genérico
> com chunks 8x menores perde para uma janela deslizante grande, avaliando
> geração. Isso não testa a hipótese estrutural — testa tamanho de chunk. É
> justamente por isso que este trabalho existe.

O parâmetro 2.048/1.024 deles também confirma a escolha do nosso
`chunkers.yaml`: usamos 512/256 e 1024/512 para ter pontos de comparação
próximos e abaixo do deles.

## Fontes

- [JurisTCU — arXiv:2503.08379](https://arxiv.org/abs/2503.08379)
- [BR-TaxQA-R — arXiv:2505.15916](https://arxiv.org/abs/2505.15916)
- [Beyond Probabilistic Similarity — arXiv:2606.09724](https://arxiv.org/abs/2606.09724)
- [Ontology-Driven Graph RAG — arXiv:2505.00039](https://arxiv.org/abs/2505.00039)
- [JUÁ — arXiv:2604.06098](https://arxiv.org/abs/2604.06098)
- [MTEB-BR — arXiv:2607.04581](https://arxiv.org/abs/2607.04581)
- [Legal RAG Bench — arXiv:2603.01710](https://arxiv.org/abs/2603.01710)
- [LegalBench-BR — arXiv:2604.18878](https://arxiv.org/abs/2604.18878)
