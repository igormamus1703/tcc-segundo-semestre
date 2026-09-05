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

**4. `domingos2025brtaxqar` — atenção, nossa afirmação é forte demais.** O
artigo diz que o BR-TaxQA-R traz *"mixed evidence regarding the benefit of
structure-aware strategies"*, e o `plano_tecnico.md` chega a dizer que ele
"contém a evidência contrária à hipótese de vocês". Ao verificar o abstract, o
foco declarado do paper é a comparação entre o pipeline RAG próprio e
ferramentas comerciais (ChatGPT, Perplexity) em relevância e correção factual;
as conclusões específicas sobre qual estratégia de segmentação venceu **não
aparecem no resumo**.

> ⚠️ **Ação:** alguém precisa ler a seção de segmentação do PDF do BR-TaxQA-R e
> confirmar o que exatamente foi medido, antes de mantermos a frase "evidência
> contrária" / "mixed evidence". Se a comparação de chunking lá for
> secundária ou não conclusiva, nossa motivação fica **mais forte**, não mais
> fraca — mas precisamos descrever o achado deles com precisão. É a citação
> mais provável de virar pergunta de banca, porque é a que sustenta o "gap"
> que justifica nosso trabalho.

## Fontes

- [JurisTCU — arXiv:2503.08379](https://arxiv.org/abs/2503.08379)
- [BR-TaxQA-R — arXiv:2505.15916](https://arxiv.org/abs/2505.15916)
- [Beyond Probabilistic Similarity — arXiv:2606.09724](https://arxiv.org/abs/2606.09724)
- [Ontology-Driven Graph RAG — arXiv:2505.00039](https://arxiv.org/abs/2505.00039)
- [JUÁ — arXiv:2604.06098](https://arxiv.org/abs/2604.06098)
- [MTEB-BR — arXiv:2607.04581](https://arxiv.org/abs/2607.04581)
- [Legal RAG Bench — arXiv:2603.01710](https://arxiv.org/abs/2603.01710)
- [LegalBench-BR — arXiv:2604.18878](https://arxiv.org/abs/2604.18878)
