# Recorte por seção, agora no pipeline: as cinco estratégias, os dois retrievers

**Data:** 28/09/2026 · **Autor:** Leonardo Marques
**Status:** ✅ resultado de pipeline, com testes — substitui o exploratório de 07/09
**Corpus:** 12.880 acórdãos · 150 consultas · 2.219 qrels

---

## O que estava em aberto

O teste de 07/09
([05-filtragem-por-secao](../leo-f4-indexacao-e-docs/resultados/05-filtragem-por-secao.md))
mostrou +16,9% de nDCG@10 ao descartar o relatório do índice, mas com quatro
buracos declarados: era um script fora do `src/`, só no **denso**, só nas
estratégias **estruturais**, e sem controle. Esta rodada fecha os quatro.

## Comandos

```bash
cd juris-chunking
python -m src.run_experiments --strategy all --retriever bm25  --secoes sem:relatorio \
    --label bm25_sec_sem_relatorio
python -m src.run_experiments --strategy all --retriever dense --secoes sem:relatorio \
    --label dense_sec_sem_relatorio

python -m src.evaluate --experiment ../results/experiments/20260928-1638_bm25_sec_sem_relatorio \
    --incluir ../results/experiments/20260906-0515_bm25
python -m src.evaluate --experiment ../results/experiments/20260928-1650_dense_sec_sem_relatorio \
    --incluir ../results/experiments/20260907-0125_dense_bge_m3
```

> `sem:relatorio` e `--secoes=-relatorio` são a mesma coisa. A segunda forma
> precisa do `=` colado: solta, o argparse lê `-relatorio` como uma opção e
> aborta com "expected one argument".

**Primeira validação:** o recorte produz **95.300 chunks** na
`structural_gold`, exatamente o número do teste exploratório de 07/09. A
reimplementação reproduz o experimento anterior, não é um caminho novo.

## nDCG@10

| Estratégia | BM25 completo | BM25 sem relatório | Δ | denso completo | denso sem relatório | Δ |
|---|---:|---:|---:|---:|---:|---:|
| structural_gold | 0,2521 | **0,2835** | +12,4% | 0,1847 | **0,2167** | +17,3% |
| structural_pred | 0,2526 | **0,2835** | +12,3% | 0,1912 | **0,2147** | +12,3% |
| recursive_default | 0,2412 | **0,2764** | +14,6% | 0,1967 | **0,2351** | +19,5% |
| fixed_1024_512 | 0,2510 | **0,2790** | +11,2% | 0,2019 | **0,2292** | +13,5% |
| fixed_512_256 | 0,2486 | **0,2904** | +16,8% | 0,2055 | **0,2627** | +27,8% |

**As dez comparações melhoram.** No BM25, todas as cinco são significativas:

| Estratégia (BM25, recorte × completo) | p | vitórias / empates / derrotas |
|---|---:|---|
| fixed_512_256 | **0,000249** | 84 / 26 / 40 |
| recursive_default | **0,000550** | 75 / 21 / 54 |
| structural_pred | **0,001046** | 79 / 30 / 41 |
| structural_gold | **0,002341** | 75 / 34 / 41 |
| fixed_1024_512 | **0,002986** | 81 / 25 / 44 |

Isso fecha o buraco maior do achado exploratório: **o efeito vale no BM25**,
que é o retriever mais forte do trabalho, e vale nas estratégias **fixas e
recursiva**, que não carregam rótulo de seção — nelas a seção é resolvida pelo
*offset* do chunk contra os spans do documento, o mesmo mecanismo do recorte
analítico da F5.

## O trade-off de recall existe no denso, e NÃO no BM25

Esta é uma correção ao que o achado exploratório declarava.

| Estratégia | Recall@100 BM25 | sem relatório | Δ | Recall@100 denso | sem relatório | Δ |
|---|---:|---:|---:|---:|---:|---:|
| structural_gold | 0,4849 | 0,5045 | **+4,0%** | 0,4220 | 0,3928 | −6,9% |
| structural_pred | 0,4863 | 0,4952 | **+1,8%** | 0,4241 | 0,3795 | −10,5% |
| recursive_default | 0,4731 | 0,4967 | **+5,0%** | 0,4283 | 0,3932 | −8,2% |
| fixed_1024_512 | 0,4861 | 0,5077 | **+4,4%** | 0,4507 | 0,4189 | −7,1% |
| fixed_512_256 | 0,4709 | 0,4993 | **+6,0%** | 0,4759 | 0,4564 | −4,1% |

O teste de 07/09 rodou só no denso, viu o recall cair 7% e registrou isso como
limitação do método. **É limitação do denso.** No BM25 ganha-se precisão no
topo *e* cobertura na cauda.

Uma explicação plausível, que o trabalho ainda não testou: o BM25 recupera um
documento por casamento de termo, e o relatório é uma massa de texto que casa
termos por volume — ele ocupava vagas no top-k sem trazer o documento certo.
Retirá-lo libera vaga. Já o denso recupera por semelhança semântica global, e
alguns documentos só tinham um "gancho" semântico no relatório; sem ele, somem.
**Isto é hipótese, não medição** — registrada aqui para não virar afirmação no
artigo sem teste.

## A ablação ouro × predito continua valendo — e mais forte

`structural_gold` × `structural_pred`, ambas com recorte, no BM25:
**p = 0,9886, com 75 empates em 150 consultas** (contra 97 empates e p = 0,827
no índice completo).

É o resultado que torna tudo isto aplicável fora do TCU: **não é preciso ter o
acórdão publicado em colunas**. O segmentador por regras, com 92,2% de
acurácia, entrega o mesmo ganho que a estrutura ouro.

## A pergunta original do TCC continua com a mesma resposta

Sob o recorte, as cinco estratégias **continuam sem se separar**:

| Par (BM25, ambas com recorte) | p |
|---|---:|
| fixed_512_256 × recursive_default | 0,0558 |
| fixed_1024_512 × fixed_512_256 | 0,1334 |
| (os outros oito pares) | 0,41 – 0,99 |

Nenhum p < 0,05 em 10 pares. O resultado nulo da F5 **não foi derrubado: foi
reforçado**, porque agora se sabe que ele vale em dois pontos de operação
separados por 16% de nDCG@10. Um empate que sobrevive a uma mudança grande no
desempenho absoluto é evidência mais forte do que um empate medido uma vez só.

**Vale registrar a inversão:** no índice completo, `fixed_512_256` era a 4ª no
BM25; sem o relatório, é a 1ª nos dois retrievers. A diferença não é
significativa, e a leitura honesta é "continua empatado" — mas a inversão
merece uma frase na Discussão, porque é consistente com o mecanismo: com o
relatório fora, o que sobra é texto denso em conteúdo julgado, e chunks menores
localizam melhor dentro dele.

## Custo

O índice fica com **28% a 34%** do tamanho. No BM25 a construção cai de ~85 s
para ~45 s por estratégia; no denso, com o cache recortado, a rodada inteira
das cinco estratégias levou **4 minutos**, contra as ~10 h que um reencode
custaria.

## O que este documento NÃO afirma

- Que o relatório é inútil para o usuário. Ele é descartado **do índice**; o
  documento recuperado continua inteiro. A afirmação é sobre onde buscar, não
  sobre o que mostrar.
- Que o mecanismo está provado. A concentração de relevância na fundamentação
  foi medida *antes* (F5), o que torna a explicação plausível e pré-registrada
  — mas a diferença BM25 × denso no recall ainda não tem explicação medida.
- Que 2/3 de índice a menos é sempre bom. O contrário: ver
  [02-controle-aleatorio.md](02-controle-aleatorio.md).
