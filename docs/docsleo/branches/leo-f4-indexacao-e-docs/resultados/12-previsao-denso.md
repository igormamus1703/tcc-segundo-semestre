# Previsão sobre o retriever denso — registrada e testada

**Data:** 2026-09-06 · **Autor:** Leonardo Marques
**Status:** sinal exploratório, não conclusivo (subcorpus pequeno)

## A previsão, registrada ANTES de rodar

Em [11-analise-do-dominio.md](../11-analise-do-dominio.md) registrei, antes de
ver qualquer número denso:

> "a diferença entre estrutural e fixo deve ser maior no denso do que no BM25",
> porque no denso o embedding é uma média semântica do trecho, e um chunk que
> atravessa a fronteira relatório→voto mistura conteúdo de alta densidade de
> sinal (72% da relevância) com conteúdo de baixa (25,7%).

Registrar antes evita a tentação de explicar qualquer resultado depois do fato.

## O teste

Subcorpus de **451 documentos** (331 relevantes + 120 distratores), **25
consultas**, 375 qrels. Comparação escolhida de propósito entre
`structural_gold` e `fixed_1024_512`, que produzem chunks do **mesmo tamanho**
(~840 tokens de subword): a única variável que muda é respeitar ou não a
fronteira de seção.

| Estratégia | BM25 | Denso (bge-m3) |
|---|---:|---:|
| fixed_1024_512 | **0,6387** | **0,5934** |
| structural_gold | 0,6316 | 0,5713 |
| **diferença (estrutural − fixo)** | **−0,0071** | **−0,0221** |

## Veredito: metade certa, metade errada

**✅ A magnitude se confirmou.** A diferença entre as duas estratégias é **3,1x
maior no denso** (0,0221 contra 0,0071). A fronteira de seção realmente importa
mais para o retriever denso — o mecanismo previsto existe.

**❌ A direção não se confirmou.** Eu previa que o estrutural *ganharia* no
denso. Ele **perde**, e perde **mais** justamente no denso.

Ou seja: respeitar as fronteiras de seção **piora** a recuperação densa, e o
mecanismo que eu imaginei operar a favor da hipótese opera contra ela.

## Hipótese para o porquê (a testar na rodada completa)

O chunking estrutural produz chunks de tamanho **irregular por construção**: a
ementa tem 1,3% dos caracteres do corpus e o dispositivo 6,0%, então essas
seções geram chunks curtos. Um chunk curto tem um embedding menos informativo —
menos contexto para o modelo situar o trecho.

A janela fixa, ao contrário, entrega sempre ~840 tokens de contexto, e o
"defeito" de atravessar a fronteira pode estar funcionando como **vantagem**:
o chunk que pega o fim do relatório e o começo do voto carrega o problema *e* a
resposta juntos, que é exatamente o par que uma consulta jurídica procura.

Se isso se confirmar no corpus completo, é um achado bom para o artigo — e
converge com o BR-TaxQA-R, que também viu a janela deslizante simples ganhar.
A diferença é que aqui saberemos **por quê**, com a análise de seções e com a
granularidade controlada (o que eles não fizeram).

## Ressalvas — por que isso NÃO é o resultado do trabalho

1. **451 documentos contra 12.880.** O subcorpus tem densidade de relevantes
   muito maior (73%), o que torna a tarefa mais fácil e comprime as diferenças.
2. **25 consultas.** A análise de poder mostra que com esse tamanho só efeitos
   grandes são detectáveis; nenhuma dessas diferenças tem significância.
3. **Uma estratégia estrutural só.** Falta o `structural_pred`, que é o cenário
   realista, e as demais baselines.

**A rodada completa (150 consultas, 12.880 documentos, 5 estratégias) é que
decide.** Este documento existe para que amanhã se saiba o que era esperado
antes de olhar o resultado.

## Também medido: denso × BM25 em nível absoluto

O BM25 fica acima do denso nos dois subcorpora testados (0,4928 × 0,4032 no de
1.899 docs; 0,6387 × 0,5934 aqui). Verifiquei que **não é erro de
configuração**: pooling CLS (correto para o bge-m3), camada de normalização
ativa, prefixo vazio (o bge-m3 dispensa) e zero truncamento com janela 1024.

É coerente com a literatura que o próprio artigo cita — `pereira2026jua`
observa que baselines lexicais seguem competitivas em RI jurídica em português,
e o JurisTCU mostrou modelos BERT-based indo mal, com só os embeddings da
OpenAI superando o BM25.
