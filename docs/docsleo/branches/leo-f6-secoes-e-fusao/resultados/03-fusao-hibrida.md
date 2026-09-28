# Fusão híbrida: o retriever denso não era inútil, era complementar

**Data:** 28/09/2026 · **Autor:** Leonardo Marques
**Status:** ✅ com peso escolhido por validação cruzada

---

## A pergunta

A F5 mediu que o BM25 vence o denso nas cinco estratégias, com p entre
0,000005 e 0,002. A leitura fácil é "o denso não serve para acórdãos". A
leitura correta é mais interessante: **o denso erra em lugares diferentes**. Se
os dois errassem nos mesmos documentos, combiná-los não poderia ajudar.

Custo de descobrir: segundos de CPU. Nenhum reencode, nenhuma reindexação — só
os arquivos TREC que já estavam em `results/experiments/`.

## Dois métodos, e por quê

- **RRF** (Reciprocal Rank Fusion): usa só a *posição* no ranking. É o padrão
  da área porque BM25 e cosseno vivem em escalas incomparáveis — um score 18,4
  do BM25 e um 0,73 do cosseno não têm relação, e somá-los é erro de categoria.
- **Soma normalizada**: min-max *por consulta* e soma ponderada. Usa a
  *magnitude*, que o RRF joga fora. Faz sentido testar porque a distância entre
  o 1º e o 2º colocado diz algo, e porque com um retriever claramente mais
  forte que o outro, dar peso a ele pode superar a fusão democrática do RRF.

## Primeiro resultado: RRF sem peso não serve

```bash
python -m src.fusion --experimentos ../results/experiments/20260906-0515_bm25 \
    ../results/experiments/20260907-0125_dense_bge_m3 --metodo rrf --k 60
```

| Estratégia | BM25 | RRF 1:1 | p |
|---|---:|---:|---:|
| structural_pred | 0,2526 | 0,2555 | 0,778 |
| structural_gold | 0,2521 | 0,2534 | 0,906 |
| fixed_1024_512 | 0,2510 | 0,2534 | 0,794 |
| fixed_512_256 | 0,2486 | 0,2521 | 0,714 |
| recursive_default | 0,2412 | 0,2535 | 0,206 |

Nenhuma diferença. Faz sentido: dar peso igual a um retriever 20% pior puxa a
fusão para baixo tanto quanto o outro a puxa para cima. **Resultado negativo,
mantido no registro** — a rodada é a `20260928-1635_fusao_rrf-k60`.

## Segundo resultado: com peso, funciona

Varrendo pesos e `k` (`rrf` com peso do BM25 em 1–5, `soma_norm` com peso
0,5–0,9), o melhor de cada estratégia sobe **6,6% a 9,7%** sobre o BM25, com
p entre 0,0007 e 0,015, **e o Recall@100 também sobe**.

⚠️ **Mas esse número está contaminado**: o peso foi escolhido olhando o
conjunto de avaliação. Com 150 consultas e ~24 configurações, alguma pareceria
boa por acaso. Reportar assim é ajustar no teste. A correção está em
[../02-metodologia-cv.md](../02-metodologia-cv.md).

## O número honesto: peso escolhido por validação cruzada

```bash
python -m src.tuning --bm25 ../results/experiments/20260906-0515_bm25 \
    --denso ../results/experiments/20260907-0125_dense_bge_m3
```

Cinco dobras de consultas. Em cada uma, o peso é escolhido nas outras quatro e
aplicado na dobra que não participou da escolha.

| Estratégia | método | BM25 | fusão (CV) | Δ | p | pesos escolhidos |
|---|---|---:|---:|---:|---:|---|
| recursive_default | soma_norm | 0,2412 | **0,2623** | +8,7% | **0,0132** | 0,6 · 0,7 · 0,6 · 0,7 · 0,6 |
| structural_pred | rrf | 0,2526 | **0,2708** | +7,2% | **0,0030** | 5 · 5 · 5 · 5 · 3 |
| structural_gold | soma_norm | 0,2521 | **0,2686** | +6,6% | **0,0251** | 0,7 · 0,7 · 0,6 · 0,7 · 0,7 |
| fixed_512_256 | rrf | 0,2486 | **0,2622** | +5,5% | **0,0228** | 5 · 3 · 3 · 3 · 3 |
| fixed_1024_512 | soma_norm | 0,2510 | **0,2640** | +5,2% | **0,0245** | 0,8 · 0,8 · 0,7 · 0,7 · 0,7 |

**7 das 10 configurações (5 estratégias × 2 métodos) dão p < 0,05 após a CV.**
O ganho aparente da varredura (6,6–9,7%) cai para 4,4–8,7% depois da correção —
a diferença entre os dois é a medida do quanto vinha do ajuste, e vale reportar
no artigo.

Os pesos escolhidos ficam entre 0,6 e 0,8 para o BM25 na soma normalizada. Não
são idênticos entre as dobras, então **o que se pode afirmar é que alguma fusão
com o BM25 dominante ajuda — não que 0,7 seja "o" número certo.** A faixa
estreita, porém, mostra que o efeito não é frágil.

## O que isto muda na narrativa do trabalho

Antes: *"o BM25 vence o denso; o denso não compensa o custo de GPU."*

Depois: *"o BM25 vence o denso isoladamente, mas os dois erram de formas
diferentes, e o sinal do denso vale 5–9% de nDCG@10 quando entra com peso
menor. O custo de GPU se paga."*

A segunda afirmação é mais forte, mais útil para quem for aplicar isso, e
continua compatível com o resultado significativo da F5.

## O melhor de tudo: fusão + recorte se somam

Rodando a mesma CV sobre os runs **já recortados**:

| Estratégia | BM25 sem relatório | + fusão (CV) | Δ | p |
|---|---:|---:|---:|---:|
| **fixed_512_256** | 0,2904 | **0,3160** | **+8,8%** | **0,0002** |
| recursive_default | 0,2764 | 0,3006 | +8,7% | **0,0004** |
| structural_gold | 0,2835 | 0,3025 | +6,7% | **0,0002** |
| fixed_1024_512 | 0,2790 | 0,2970 | +6,4% | **0,0007** |
| structural_pred | 0,2835 | 0,2902 | +2,3% | 0,228 |

As duas intervenções são independentes e os ganhos se acumulam: o recorte muda
*o que está no índice*, a fusão muda *como dois rankings se combinam*.

O detalhe da configuração final está em
[04-tabela-principal.md](04-tabela-principal.md).
