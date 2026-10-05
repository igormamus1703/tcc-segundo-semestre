# Referências do TCC

**Criado em:** 05/10/2026 (branch `leo/f7-evolucao`) · **Mantido por:** Leonardo Marques

Base bibliográfica do artigo final e do pôster. Reúne o que o projeto já cita
(artigo, `plano_tecnico.md`, docs da F4–F6) e o que foi pesquisado para a F7.

**Regra do projeto** (`plano_tecnico.md` §5): *nenhuma referência entra no
texto final sem alguém ter aberto o PDF*. Por isso cada entrada traz o nível
de verificação:

| Selo | Significa |
|---|---|
| 📄 **lida** | texto completo lido; os números citados aqui foram conferidos no PDF |
| 🔎 **conferida** | título, autores, ano e venue conferidos na página oficial (arXiv/ACM/DOI); o conteúdo vem do resumo |
| 📚 **canônica** | clássico da área, amplamente citado; **conferir o PDF antes de citar um número** |

---

## 1. Dados e benchmarks — de onde vêm o corpus, as consultas e os qrels

| Chave | Referência | Selo | Papel no TCC |
|---|---|---|---|
| `fernandes2025juristcu` | Fernandes, L. C.; Ribeiro, L. S.; de Castro, M. V. B.; Pacheco, L. A. S.; Sandes, E. F. O. **JurisTCU: A Brazilian Portuguese Information Retrieval Dataset with Query Relevance Judgments.** arXiv:2503.08379, 2025. Publicado em *Language Resources and Evaluation* 60(1):23, 2026. | 📄 | **Benchmark principal**: as 150 consultas e os 2.250 qrels |
| `pereira2026jua` | Pereira, J.; Fernandes, L.; de Brito, E.; Lotufo, R.; Bonifacio, L. **JUÁ — A Benchmark for Information Retrieval in Brazilian Legal Text Collections.** arXiv:2604.06098, 2026. | 🔎 | Contexto do corpus e, na F7, **segunda coleção de teste** (JUÁ-Juris) |
| `tcu_dados_abertos` | Tribunal de Contas da União. **Acórdãos — Dados Abertos** (CSV anual, 2003–2023). Portal de Dados Abertos do TCU. | — | Texto íntegro dos 12.880 acórdãos e as colunas que dão a estrutura ouro |
| `domingos2025brtaxqar` | Domingos Júnior, J.; Faria, A.; Seiti de Oliveira, E.; de Brito, E.; Teotonio, M.; Assumpção, A.; Carmo, D.; Lotufo, R.; Pereira, J. **BR-TaxQA-R: A Dataset for Question Answering with References for Brazilian Personal Income Tax Law.** arXiv:2505.15916, 2025. Também em *Intelligent Systems* (BRACIS), Springer, 2026, pp. 208–222. | 📄 | Trabalho relacionado mais próximo em chunking jurídico BR (ver §3) |
| `stekel2026mtebbr` | Stekel, T. R. C. **MTEB-BR: A Text Embedding Benchmark for Brazilian Portuguese.** arXiv:2607.04581, 2026. | 🔎 | Escolha do modelo de embedding |
| `carvalho2026legalbenchbr` | Carvalho Neto, P. B. **LegalBench-BR: A Benchmark for Evaluating LLMs on Brazilian Legal Decision Classification.** arXiv:2604.18878, 2026. | 🔎 | Panorama de benchmarks jurídicos BR |
| `butler2026legalragbench` | Butler, A.-R.; Butler, U. **Legal RAG Bench: an end-to-end benchmark for legal RAG.** arXiv:2603.01710, 2026. | 🔎 | **Justifica avaliar recuperação, não geração**: a recuperação é o principal determinante do desempenho de RAG jurídico |
| `thakur2021beir` | Thakur, N.; Reimers, N.; Rücklé, A.; Srivastava, A.; Gurevych, I. **BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models.** NeurIPS Datasets and Benchmarks, 2021. | 📚 | Avaliação heterogênea; BM25 como baseline forte |

**Fatos do JurisTCU que o artigo precisa citar** (📄, conferidos no texto completo):
- As consultas sintéticas (G2, G3) foram **geradas a partir do ENUNCIADO** dos 50 documentos mais acessados: GPT-4 gerou 5 perguntas por enunciado, refinadas à mão em uma.
- **Pool de julgamento:** top-300 do BM25 + top-300 do Legal-BERTimbau, reordenados pelo `mt5-3B-mmarco-en-pt`; anotados os 10 melhores + 5 aleatórios do top-1000 do BM25. Escala 0–3, GPT-4 + revisão de especialista.
- **Limitação declarada pelos autores:** o pool pré-selecionado por BM25 e BERT pode enviesar a avaliação a favor desses dois modelos.
- BM25 deles (sobre excertos, não acórdãos íntegros): nDCG@10 de 27,5 / 51,1 / 53,3 em G1 / G2 / G3; BM25 + doc2query + sinônimos: G1 = 40,4.

**Fatos do JUÁ-Juris** (🔎, card do dataset no Hugging Face `ufca-llms/jua`):
- 17.147 pares (enunciado, excerto) da jurisprudência selecionada do TCU; teste = 1.714 (10%, estratificado por dificuldade no BM25), treino = 15.433.
- Consulta = enunciado; relevante = o excerto correspondente (binário, `query-id == corpus-id`).
- O id `JURISPRUDENCIA-SELECIONADA-<N>` usa o mesmo `KEY` do `doc.csv` do JurisTCU, e é isso que permite levar cada consulta ao acórdão íntegro (F7, `src/jua.py`).

---

## 2. Trabalhos diretamente concorrentes — recuperação em acórdãos longos do TCU

| Chave | Referência | Selo | Papel no TCC |
|---|---|---|---|
| `pereira2026nuggets` | Pereira, L.; Brito, E.; Lotufo, R.; Pereira, J. **Legal Nugget Extraction for Granular Retrieval over Long Jurisprudential Texts.** arXiv:2607.22479, jul. 2026. | 📄 | **O trabalho mais próximo do nosso.** Mesmo problema (tese diluída num documento longo), solução por LLM |
| `pereira2026domainadaptive` | Pereira, J.; Lotufo, R.; Bonifacio, L. **Domain-Adaptive Dense Retrieval for Brazilian Legal Search.** arXiv:2605.04005, 2026. | 🔎 | Retrievers adaptados ao domínio (Qwen3-Embedding-4B); teto atual do JUÁ |
| `ma2023structural` | Ma, Y.; Wu, Y.; Ai, Q.; Liu, Y.; Shao, Y.; Zhang, M.; Ma, S. **Incorporating Structural Information into Legal Case Retrieval.** *ACM TOIS* 42(2), art. 40, 2023. DOI 10.1145/3609796. | 🔎 | Precedente internacional: estrutura do documento jurídico na recuperação |

**O que o `pereira2026nuggets` mostra** (📄):
- Extrai "nuggets" (teses jurídicas atômicas) com `gpt-5.4-nano`, indexa os nuggets e agrega ao documento por max.
- JurisTCU: nDCG@10 de 0,209 → **0,327** com `text-embedding-3-small`; JUÁ-Juris: 0,103 → 0,205.
- **Não generaliza:** piora em NormasTCU e BR-TaxQA, e perde para retrievers adaptados ao domínio (jua-4B: 0,375 no JurisTCU, documento inteiro).
- Conclusão dos autores: o ganho depende do alinhamento entre consulta-tese e representação-tese.

> 💡 **Posicionamento para a banca.** O nosso recorte por seção ataca o mesmo
> problema **sem LLM, sem custo de geração e sem perder rastreabilidade**: a
> fundamentação já é, por construção do gênero, a seção que carrega a tese. As
> diferenças precisam ficar explícitas: (1) eles indexam o *excerto* do
> JurisTCU, nós o *acórdão íntegro*; (2) a nossa unidade é a seção oficial,
> não um texto gerado; (3) os números não são diretamente comparáveis. A
> pergunta que liga os dois trabalhos: *quanto do ganho dos nuggets uma
> heurística estrutural gratuita já captura?*

---

## 3. Chunking e granularidade — a pergunta original do TCC

| Chave | Referência | Selo | Papel no TCC |
|---|---|---|---|
| `qu2025semanticchunking` | Qu, R.; Tu, R.; Bao, F. **Is Semantic Chunking Worth the Computational Cost?** Findings of NAACL 2025. arXiv:2410.13070. | 🔎 | **Converge com o nosso resultado nulo:** chunking "inteligente" não dá ganho consistente que pague o custo |
| `shaukat2026systematic` | Shaukat, M. A.; Adnan, M.; Kuhn, C. C. N. **A Systematic Investigation of Document Chunking Strategies and Embedding Sensitivity.** arXiv:2603.06976, 2026. | 🔎 | **Contraponto:** chunking por conteúdo (grupos de parágrafos) vence o fixo por caracteres. Atenção: o baseline deles é fixo *por caracteres*, não por tokens com overlap, como o nosso |
| `smigielski2026chunking` | Śmigielski, M. et al. **Chunking Methods on Retrieval-Augmented Generation — Effectiveness Evaluation Against Computational Cost and Limitations.** arXiv:2606.00881, 2026. | 🔎 | Avaliação ampla; chunking traz problemas frequentemente ignorados |
| `jimenoyepes2024financial` | Jimeno Yepes, A.; You, Y.; Milczek, J.; Laverde, S.; Li, L. **Financial Report Chunking for Effective Retrieval Augmented Generation.** arXiv:2402.05131, 2024. | 🔎 | Chunking por elemento estrutural ajuda em relatórios financeiros — hipótese análoga em outro gênero |
| `gunther2024latechunking` | Günther, M.; Mohr, I.; Williams, D. J.; Wang, B.; Xiao, H. **Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models.** arXiv:2409.04701, 2024. | 🔎 | Alternativa moderna: cortar *depois* do encoder. Trabalho futuro |
| `anthropic2024contextual` | Anthropic. **Introducing Contextual Retrieval.** Blog técnico, set. 2024. | 🔎 | Contexto do documento prefixado ao chunk; relacionado ao "prefixo de seção" que ficou como trabalho futuro |
| `domingos2025brtaxqar` | (ver §1) | 📄 | Janela 2.048 tokens > splitter recursivo de 1.000 caracteres. **Confunde estrutura com tamanho** — é o espaço que o TCC ocupa |

**O que já está escrito sobre o BR-TaxQA-R** (`docs/docsleo/branches/leo-f4-indexacao-e-docs/04-referencias-verificadas.md`):
sliding-window de 2.048/1.024 tokens: Response Relevancy 0,819 e Factual
Correctness 0,313; recursivo de 1.000 caracteres: 0,791 e 0,286. A comparação
mistura granularidade (~8×) com estrutura e mede geração (RAGAS), não
recuperação.

---

## 4. Modelos de recuperação

| Chave | Referência | Selo | Papel no TCC |
|---|---|---|---|
| `robertson2009prf` | Robertson, S.; Zaragoza, H. **The Probabilistic Relevance Framework: BM25 and Beyond.** *Foundations and Trends in IR* 3(4), 2009. | 📚 | Fundamento do BM25 |
| `robertson2004bm25f` | Robertson, S.; Zaragoza, H.; Taylor, M. **Simple BM25 Extension to Multiple Weighted Fields.** CIKM 2004. | 🔎 | **Explica o negativo da F6:** somar scores por campo quebra a saturação do BM25; o certo é ponderar a *frequência do termo antes* da saturação (BM25F). É exatamente por isso que a nossa ponderação de score por seção saturou no corte binário |
| `lu2024bm25s` | Lù, X. H. **BM25S: Orders of magnitude faster lexical search via eager sparse scoring.** arXiv:2407.03618, 2024. | 🔎 | Implementação de BM25 usada (`bm25s`) |
| `karpukhin2020dpr` | Karpukhin, V. et al. **Dense Passage Retrieval for Open-Domain Question Answering.** EMNLP 2020. | 📚 | Recuperação densa (bi-encoder) |
| `chen2024bgem3` | Chen, J.; Xiao, S.; Zhang, P.; Luo, K.; Lian, D.; Liu, Z. **M3-Embedding (BGE M3): Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation.** arXiv:2402.03216, 2024 (Findings of ACL 2024). | 🔎 | **Modelo denso usado** (`BAAI/bge-m3`, janela de 8.192 tokens) |
| `zhang2025qwen3embedding` | Zhang, Y. et al. **Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models.** arXiv:2506.05176, 2025. | 🔎 | Família de embedding e reranker do estado da arte; base dos modelos JUÁ |
| `khattab2020colbert` | Khattab, O.; Zaharia, M. **ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT.** SIGIR 2020. | 📚 | Interação tardia; granularidade dentro do modelo |
| `garcia2024robertalexpt` | Garcia, E. et al. **RoBERTaLexPT: A Legal RoBERTa Model Pretrained with Deduplication for Portuguese.** PROPOR 2024. | 📚 | Descartado como retriever: encoder MLM sem fine-tune de recuperação |
| `chalkidis2020legalbert` | Chalkidis, I.; Fergadiotis, M.; Malakasiotis, P.; Aletras, N.; Androutsopoulos, I. **LEGAL-BERT: The Muppets straight out of Law School.** Findings of EMNLP 2020. | 📚 | Necessidade de representações adaptadas ao domínio jurídico |
| `reimers2019sbert` | Reimers, N.; Gurevych, I. **Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.** EMNLP 2019. | 📚 | Biblioteca `sentence-transformers` |
| `johnson2019faiss` | Johnson, J.; Douze, M.; Jégou, H. **Billion-scale similarity search with GPUs.** *IEEE Transactions on Big Data*, 2019. arXiv:1702.08734. | 📚 | Índice vetorial (`faiss.IndexFlatIP`) |

---

## 5. Documentos longos: agregação de passagens e reranking

| Chave | Referência | Selo | Papel no TCC |
|---|---|---|---|
| `dai2019deeper` | Dai, Z.; Callan, J. **Deeper Text Understanding for IR with Contextual Neural Language Modeling.** SIGIR 2019. | 🔎 | **MaxP/FirstP**: o documento vale a melhor passagem — é a nossa agregação `max_pooling` |
| `zhang2021aggregation` | Zhang, X.; Yates, A.; Lin, J. **Comparing Score Aggregation Approaches for Document Retrieval with Pretrained Transformers.** ECIR 2021. | 🔎 | Sustenta a escolha de max-pooling contra `sum_top_k` (confirmado na F6) |
| `li2020parade` | Li, C.; Yates, A.; MacAvaney, S.; He, B.; Sun, Y. **PARADE: Passage Representation Aggregation for Document Reranking.** arXiv:2008.09093 (ACM TOIS 2023). | 🔎 | Agregação aprendida de passagens |
| `nogueira2019monobert` | Nogueira, R.; Cho, K. **Passage Re-ranking with BERT.** arXiv:1901.04085, 2019. | 📚 | Reranking com cross-encoder (F7) |
| `lin2021pretrained` | Lin, J.; Nogueira, R.; Yates, A. **Pretrained Transformers for Text Ranking: BERT and Beyond.** Morgan & Claypool, 2021. arXiv:2010.06467. | 🔎 | Referência-livro para reranking e documentos longos |
| `bge_reranker_v2_m3` | BAAI. **bge-reranker-v2-m3** (model card, Hugging Face), 2024. Cross-encoder multilíngue sobre o bge-m3. | 🔎 | Reranker da F7. Card: fine-tune com até 1.024 tokens |

---

## 6. Fusão de rankings

| Chave | Referência | Selo | Papel no TCC |
|---|---|---|---|
| `cormack2009rrf` | Cormack, G. V.; Clarke, C. L. A.; Büttcher, S. **Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods.** SIGIR 2009. | 📚 | RRF (`src/fusion.py`), k = 60 |
| `fox1994combsum` | Fox, E. A.; Shaw, J. A. **Combination of Multiple Searches.** TREC-2, 1994. | 📚 | CombSUM — a soma normalizada da F6 é um CombSUM com min-max |

---

## 7. Avaliação e estatística

| Chave | Referência | Selo | Papel no TCC |
|---|---|---|---|
| `jarvelin2002ndcg` | Järvelin, K.; Kekäläinen, J. **Cumulated Gain-Based Evaluation of IR Techniques.** *ACM TOIS* 20(4):422–446, 2002. | 📚 | nDCG |
| `voorhees2000qa` | Voorhees, E. M.; Tice, D. M. **Building a Question Answering Test Collection.** SIGIR 2000. | 📚 | MRR |
| `bassani2022ranx` | Bassani, E. **ranx: A Blazing-Fast Python Library for Ranking Evaluation and Comparison.** ECIR 2022. | 📚 | Biblioteca de avaliação |
| `smucker2007comparison` | Smucker, M. D.; Allan, J.; Carterette, B. **A Comparison of Statistical Significance Tests for Information Retrieval Evaluation.** CIKM 2007, pp. 623–632. DOI 10.1145/1321440.1321528. | 🔎 | **Justifica o teste t pareado:** t, randomização e bootstrap concordam na prática; Wilcoxon e sinal perdem poder |
| `webber2008power` | Webber, W.; Moffat, A.; Zobel, J. **Statistical Power in Retrieval Experimentation.** CIKM 2008. DOI 10.1145/1458082.1458158. | 🔎 | **Análise de poder**; e: mais consultas rasas dão mais poder que poucas consultas profundas — o argumento da F7 para usar o JUÁ-Juris |
| `sakai2016topicsetsize` | Sakai, T. **Topic Set Size Design.** *Information Retrieval Journal* 19, 2016. DOI 10.1007/s10791-015-9273-z. | 🔎 | Quantas consultas são necessárias para um dado efeito mínimo |
| `sakai2018book` | Sakai, T. **Laboratory Experiments in Information Retrieval: Sample Sizes, Effect Sizes, and Statistical Power.** Springer, 2018. | 🔎 | Referência-livro para poder e tamanho de efeito |
| `sakai2007alternatives` | Sakai, T. **Alternatives to Bpref.** SIGIR 2007. | 🔎 | **Listas condensadas:** avaliar só sobre documentos julgados. Robustez ao pool incompleto (F7) |
| `buckley2004bpref` | Buckley, C.; Voorhees, E. M. **Retrieval Evaluation with Incomplete Information.** SIGIR 2004. | 📚 | bpref; julgamento incompleto |
| `efron1993bootstrap` | Efron, B.; Tibshirani, R. J. **An Introduction to the Bootstrap.** Chapman & Hall, 1993. | 📚 | IC 95% por bootstrap |
| `dunn1961bonferroni` | Dunn, O. J. **Multiple Comparisons Among Means.** *JASA* 56(293):52–64, 1961. | 📚 | Correção de Bonferroni |
| `kohavi1995cv` | Kohavi, R. **A Study of Cross-Validation and Bootstrap for Accuracy Estimation and Model Selection.** IJCAI 1995. | 📚 | Validação cruzada para escolher hiperparâmetro sem tocar no teste (F6) |

---

## 8. RAG jurídico e contexto do problema

| Chave | Referência | Selo | Papel no TCC |
|---|---|---|---|
| `lewis2020rag` | Lewis, P. et al. **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.** NeurIPS 2020. | 📚 | Definição de RAG |
| `demartim2026beyond` | de Martim, H. **Beyond Probabilistic Similarity: Structural, Temporal, and Causal Limitations of RAG in the Legal Domain.** arXiv:2606.09724, 2026. | 🔎 | Motivação: *mereological blindness* — o RAG ignora a estrutura do documento jurídico |
| `demartim2025ontology` | de Martim, H. **An Ontology-Driven Graph RAG for Legal Norms: A Structural, Temporal, and Deterministic Approach.** JURIX 2025 (*Legal Knowledge and Information Systems*, IOS Press). arXiv:2505.00039. | 🔎 | Estrutura como cidadã de primeira classe em RAG jurídico. **Citar o JURIX, não o preprint** |

---

## 9. Software (citar na seção de Materiais)

| Ferramenta | Versão no projeto | Referência |
|---|---|---|
| `bm25s` | 0.3.11 | `lu2024bm25s` |
| `ranx` | 0.3.21 | `bassani2022ranx` |
| `faiss-cpu` | 1.15.0 | `johnson2019faiss` |
| `sentence-transformers` | 6.0.1 | `reimers2019sbert` |
| `transformers` / `torch` | 5.16.1 / 2.14.0+cu130 | Wolf et al. (2020); Paszke et al. (2019) |
| `scipy` (teste t pareado) | — | Virtanen et al. (2020), *Nature Methods* |
| `BAAI/bge-m3` | — | `chen2024bgem3` |
| `BAAI/bge-reranker-v2-m3` | — | `bge_reranker_v2_m3` |

---

## 10. BibTeX

```bibtex
@article{fernandes2025juristcu,
  title   = {JurisTCU: A Brazilian Portuguese Information Retrieval Dataset with Query Relevance Judgments},
  author  = {Fernandes, L. C. and Ribeiro, L. d. S. and de Castro, M. V. B. and da Silva Pacheco, L. A. and de Oliveira Sandes, E. F.},
  journal = {Language Resources and Evaluation},
  volume  = {60}, number = {1}, pages = {23}, year = {2026},
  note    = {arXiv:2503.08379}
}
@misc{pereira2026jua,
  title  = {{JU\'A} -- A Benchmark for Information Retrieval in Brazilian Legal Text Collections},
  author = {Pereira, Jayr and Fernandes, Leandro and de Brito, Erick and Lotufo, Roberto and Bonifacio, Luiz},
  year   = {2026}, eprint = {2604.06098}, archivePrefix = {arXiv}
}
@misc{pereira2026nuggets,
  title  = {Legal Nugget Extraction for Granular Retrieval over Long Jurisprudential Texts},
  author = {Pereira, Lucas and Brito, Erick and Lotufo, Roberto and Pereira, Jayr},
  year   = {2026}, eprint = {2607.22479}, archivePrefix = {arXiv}
}
@misc{pereira2026domainadaptive,
  title  = {Domain-Adaptive Dense Retrieval for Brazilian Legal Search},
  author = {Pereira, Jayr and Lotufo, Roberto and Bonifacio, Luiz},
  year   = {2026}, eprint = {2605.04005}, archivePrefix = {arXiv}
}
@misc{domingos2025brtaxqar,
  title  = {{BR-TaxQA-R}: A Dataset for Question Answering with References for Brazilian Personal Income Tax Law, including case law},
  author = {Domingos J{\'u}nior, J. and Faria, A. and Seiti de Oliveira, E. and de Brito, E. and Teotonio, M. and Assump{\c{c}}{\~a}o, A. and Carmo, D. and Lotufo, R. and Pereira, J.},
  year   = {2025}, eprint = {2505.15916}, archivePrefix = {arXiv}
}
@article{ma2023structural,
  title   = {Incorporating Structural Information into Legal Case Retrieval},
  author  = {Ma, Yixiao and Wu, Yueyue and Ai, Qingyao and Liu, Yiqun and Shao, Yunqiu and Zhang, Min and Ma, Shaoping},
  journal = {ACM Transactions on Information Systems},
  volume  = {42}, number = {2}, articleno = {40}, year = {2023},
  doi     = {10.1145/3609796}
}
@inproceedings{qu2025semanticchunking,
  title     = {Is Semantic Chunking Worth the Computational Cost?},
  author    = {Qu, Renyi and Tu, Ruixuan and Bao, Forrest},
  booktitle = {Findings of the Association for Computational Linguistics: NAACL 2025},
  year      = {2025}, note = {arXiv:2410.13070}
}
@misc{shaukat2026systematic,
  title  = {A Systematic Investigation of Document Chunking Strategies and Embedding Sensitivity},
  author = {Shaukat, Muhammad Arslan and Adnan, Muntasir and Kuhn, Carlos C. N.},
  year   = {2026}, eprint = {2603.06976}, archivePrefix = {arXiv}
}
@misc{smigielski2026chunking,
  title  = {Chunking Methods on Retrieval-Augmented Generation -- Effectiveness Evaluation Against Computational Cost and Limitations},
  author = {{\'S}migielski, Mateusz and Rajkowski, Micha{\l} and Zbrocki, Mateusz and Bernacki-Janson, Micha{\l} and Kunicki, Karol and Godziszewska, Julianna and Piasecki, Maciej and Wojtasik, Konrad},
  year   = {2026}, eprint = {2606.00881}, archivePrefix = {arXiv}
}
@misc{jimenoyepes2024financial,
  title  = {Financial Report Chunking for Effective Retrieval Augmented Generation},
  author = {Jimeno Yepes, Antonio and You, Yao and Milczek, Jan and Laverde, Sebastian and Li, Leah},
  year   = {2024}, eprint = {2402.05131}, archivePrefix = {arXiv}
}
@misc{gunther2024latechunking,
  title  = {Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models},
  author = {G{\"u}nther, Michael and Mohr, Isabelle and Williams, Daniel James and Wang, Bo and Xiao, Han},
  year   = {2024}, eprint = {2409.04701}, archivePrefix = {arXiv}
}
@inproceedings{robertson2004bm25f,
  title     = {Simple {BM25} Extension to Multiple Weighted Fields},
  author    = {Robertson, Stephen and Zaragoza, Hugo and Taylor, Michael},
  booktitle = {Proceedings of the 13th ACM International Conference on Information and Knowledge Management (CIKM)},
  year      = {2004}
}
@article{robertson2009prf,
  title   = {The Probabilistic Relevance Framework: {BM25} and Beyond},
  author  = {Robertson, Stephen and Zaragoza, Hugo},
  journal = {Foundations and Trends in Information Retrieval},
  volume  = {3}, number = {4}, year = {2009}
}
@misc{lu2024bm25s,
  title  = {{BM25S}: Orders of magnitude faster lexical search via eager sparse scoring},
  author = {L{\`u}, Xing Han},
  year   = {2024}, eprint = {2407.03618}, archivePrefix = {arXiv}
}
@misc{chen2024bgem3,
  title  = {{BGE M3-Embedding}: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation},
  author = {Chen, Jianlv and Xiao, Shitao and Zhang, Peitian and Luo, Kun and Lian, Defu and Liu, Zheng},
  year   = {2024}, eprint = {2402.03216}, archivePrefix = {arXiv}
}
@misc{zhang2025qwen3embedding,
  title  = {Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models},
  author = {Zhang, Yanzhao and others},
  year   = {2025}, eprint = {2506.05176}, archivePrefix = {arXiv}
}
@inproceedings{dai2019deeper,
  title     = {Deeper Text Understanding for {IR} with Contextual Neural Language Modeling},
  author    = {Dai, Zhuyun and Callan, Jamie},
  booktitle = {Proceedings of the 42nd International ACM SIGIR Conference},
  year      = {2019}
}
@inproceedings{zhang2021aggregation,
  title     = {Comparing Score Aggregation Approaches for Document Retrieval with Pretrained Transformers},
  author    = {Zhang, Xinyu and Yates, Andrew and Lin, Jimmy},
  booktitle = {Advances in Information Retrieval (ECIR)},
  year      = {2021}
}
@misc{nogueira2019monobert,
  title  = {Passage Re-ranking with {BERT}},
  author = {Nogueira, Rodrigo and Cho, Kyunghyun},
  year   = {2019}, eprint = {1901.04085}, archivePrefix = {arXiv}
}
@book{lin2021pretrained,
  title     = {Pretrained Transformers for Text Ranking: {BERT} and Beyond},
  author    = {Lin, Jimmy and Nogueira, Rodrigo and Yates, Andrew},
  publisher = {Morgan \& Claypool}, year = {2021}
}
@inproceedings{cormack2009rrf,
  title     = {Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods},
  author    = {Cormack, Gordon V. and Clarke, Charles L. A. and B{\"u}ttcher, Stefan},
  booktitle = {Proceedings of the 32nd International ACM SIGIR Conference},
  year      = {2009}
}
@inproceedings{smucker2007comparison,
  title     = {A Comparison of Statistical Significance Tests for Information Retrieval Evaluation},
  author    = {Smucker, Mark D. and Allan, James and Carterette, Ben},
  booktitle = {Proceedings of the 16th ACM CIKM},
  pages     = {623--632}, year = {2007}, doi = {10.1145/1321440.1321528}
}
@inproceedings{webber2008power,
  title     = {Statistical Power in Retrieval Experimentation},
  author    = {Webber, William and Moffat, Alistair and Zobel, Justin},
  booktitle = {Proceedings of the 17th ACM CIKM},
  year      = {2008}, doi = {10.1145/1458082.1458158}
}
@article{sakai2016topicsetsize,
  title   = {Topic Set Size Design},
  author  = {Sakai, Tetsuya},
  journal = {Information Retrieval Journal},
  volume  = {19}, year = {2016}, doi = {10.1007/s10791-015-9273-z}
}
@inproceedings{sakai2007alternatives,
  title     = {Alternatives to Bpref},
  author    = {Sakai, Tetsuya},
  booktitle = {Proceedings of the 30th International ACM SIGIR Conference},
  year      = {2007}
}
@inproceedings{buckley2004bpref,
  title     = {Retrieval Evaluation with Incomplete Information},
  author    = {Buckley, Chris and Voorhees, Ellen M.},
  booktitle = {Proceedings of the 27th International ACM SIGIR Conference},
  year      = {2004}
}
@article{jarvelin2002ndcg,
  title   = {Cumulated Gain-Based Evaluation of {IR} Techniques},
  author  = {J{\"a}rvelin, Kalervo and Kek{\"a}l{\"a}inen, Jaana},
  journal = {ACM Transactions on Information Systems},
  volume  = {20}, number = {4}, pages = {422--446}, year = {2002}
}
@inproceedings{bassani2022ranx,
  title     = {ranx: A Blazing-Fast Python Library for Ranking Evaluation and Comparison},
  author    = {Bassani, Elias},
  booktitle = {Advances in Information Retrieval (ECIR)},
  year      = {2022}
}
@misc{butler2026legalragbench,
  title  = {Legal {RAG} Bench: an end-to-end benchmark for legal {RAG}},
  author = {Butler, Abdur-Rahman and Butler, Umar},
  year   = {2026}, eprint = {2603.01710}, archivePrefix = {arXiv}
}
@misc{demartim2026beyond,
  title  = {Beyond Probabilistic Similarity: Structural, Temporal, and Causal Limitations of {RAG} in the Legal Domain},
  author = {de Martim, Hudson},
  year   = {2026}, eprint = {2606.09724}, archivePrefix = {arXiv}
}
@inproceedings{demartim2025ontology,
  title     = {An Ontology-Driven Graph {RAG} for Legal Norms: A Structural, Temporal, and Deterministic Approach},
  author    = {de Martim, Hudson},
  booktitle = {Legal Knowledge and Information Systems (JURIX 2025)},
  publisher = {IOS Press}, year = {2025}, note = {arXiv:2505.00039}
}
@misc{stekel2026mtebbr,
  title  = {{MTEB-BR}: A Text Embedding Benchmark for Brazilian Portuguese},
  author = {Stekel, Tardelli Ronan Coelho},
  year   = {2026}, eprint = {2607.04581}, archivePrefix = {arXiv}
}
@misc{carvalho2026legalbenchbr,
  title  = {{LegalBench-BR}: A Benchmark for Evaluating Large Language Models on Brazilian Legal Decision Classification},
  author = {Carvalho Neto, Pedro Barbosa de},
  year   = {2026}, eprint = {2604.18878}, archivePrefix = {arXiv}
}
@inproceedings{lewis2020rag,
  title     = {Retrieval-Augmented Generation for Knowledge-Intensive {NLP} Tasks},
  author    = {Lewis, Patrick and others},
  booktitle = {Advances in Neural Information Processing Systems 33 (NeurIPS)},
  year      = {2020}
}
@inproceedings{karpukhin2020dpr,
  title     = {Dense Passage Retrieval for Open-Domain Question Answering},
  author    = {Karpukhin, Vladimir and others},
  booktitle = {Proceedings of EMNLP 2020},
  year      = {2020}
}
@inproceedings{khattab2020colbert,
  title     = {{ColBERT}: Efficient and Effective Passage Search via Contextualized Late Interaction over {BERT}},
  author    = {Khattab, Omar and Zaharia, Matei},
  booktitle = {Proceedings of the 43rd International ACM SIGIR Conference},
  year      = {2020}
}
```

> ⚠️ **Antes do texto final:** completar os autores marcados com `and others`
> e expandir as iniciais (JurisTCU, BR-TaxQA-R) **a partir do PDF**. Ficaram
> em iniciais de propósito: é o que as fontes oficiais consultadas mostram, e
> nome inventado em bibliografia é pior que nome abreviado.
