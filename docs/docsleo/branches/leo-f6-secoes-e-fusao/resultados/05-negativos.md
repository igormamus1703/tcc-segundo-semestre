# O que foi testado e NÃO funcionou

**Data:** 28/09/2026 · **Autor:** Leonardo Marques

Três coisas foram implementadas, medidas e descartadas nesta branch. Ficam
registradas para ninguém repetir, e porque duas delas explicam *por que* a
versão que ficou é a certa.

---

## 1. Ponderação por seção (`--pesos`) — descartada

**A ideia.** Em vez de cortar o relatório fora do índice, deixá-lo dentro com
um peso menor: o score do chunk é multiplicado pelo peso da sua seção antes da
agregação chunk → documento. A promessa era **preservar o Recall@100**, que o
corte binário sacrificava no denso.

**O que aconteceu.** Ela satura no corte binário e perde recall.

| Configuração (denso, `fixed_512_256`) | nDCG@10 | Recall@100 |
|---|---:|---:|
| índice completo | 0,2055 | 0,4759 |
| peso do relatório = 0,5 | 0,2627 | 0,4558 |
| peso do relatório = 0,2 | 0,2627 | 0,4558 |
| corte binário (sem relatório) | 0,2627 | 0,4564 |

Os três primeiros dígitos idênticos entre 0,2 e 0,5 levantaram a suspeita de
que o peso não estava sendo aplicado. Teste de sanidade com peso 0,98
(`structural_gold`, denso): **0,1990 contra 0,1847 do baseline**. O peso é
aplicado, sim — e um desconto de 2% já rende +7,7%.

**Duas conclusões, uma delas interessante.**

*A prática:* qualquer peso moderado empurra todo chunk de relatório para baixo
do melhor chunk não-relatório do mesmo documento, e o resultado da agregação
passa a ser idêntico ao do corte. A ponderação acrescenta um hiperparâmetro e
não entrega nada que o corte já não dê. **Descartada.**

*A que vale reportar no artigo:* **um desconto de 2% no score do relatório já
captura metade do ganho**. Isso quer dizer que, dentro de um mesmo documento, o
chunk do relatório vence o da fundamentação **por muito pouco** — não é um
casamento muito melhor, é um casamento marginalmente melhor que acontece mais
vezes porque há mais texto de relatório. É a evidência mais direta do mecanismo
"eles acham o termo onde há mais texto, não onde há mais informação".

**Por que o recall não é preservado, ao contrário do esperado.** O peso é
aplicado *depois* do corte em `--top-chunks` (2.000 por consulta). Os chunks de
relatório entram no top-2.000 por score bruto, ocupam vaga, e só então são
descontados — enquanto no corte binário eles nunca disputam, e as 2.000 vagas
vão para chunks úteis. O número de linhas do run cai de ~146 mil para ~108 mil,
o que é exatamente esse efeito. Está documentado no código, em
`run_experiments.run_one`.

## 2. RRF sem peso — descartado

Fundir BM25 e denso com peso igual não muda nada: p entre 0,206 e 0,906 nas
cinco estratégias. Detalhe em [03-fusao-hibrida.md](03-fusao-hibrida.md).
Mantido no registro porque é o default de quase toda implementação de RRF, e
alguém vai tentar de novo se não estiver escrito que não funciona **aqui** —
com um retriever 20% mais fraco que o outro, a fusão democrática é puxada para
baixo tanto quanto para cima.

A rodada é a `20260928-1635_fusao_rrf-k60`.

## 3. Agregação `sum_top_k` — não melhora (análise de sensibilidade)

Item aberto desde a F5, agora fechado. Sob o recorte por seção, no BM25:

| Estratégia | max_pooling | sum_top_k (k=3) |
|---|---:|---:|
| fixed_512_256 | **0,2904** | 0,2875 |
| structural_gold | **0,2835** | 0,2725 |
| structural_pred | **0,2835** | 0,2651 |
| fixed_1024_512 | **0,2790** | 0,2835 |
| recursive_default | **0,2764** | 0,2656 |

O `max_pooling` ganha em 4 de 5. Isto **não** é um resultado negativo no mau
sentido: era uma análise de sensibilidade, e ela cumpriu o papel de mostrar que
a conclusão não depende da escolha de agregação. O default continua
`max_pooling`, agora com evidência em vez de convenção.

Rodada: `20260928-1707_bm25_sec_sumtopk`.

---

## Coisas que NÃO foram testadas nesta branch

Registradas para o planejamento, não como falha:

| Ideia | Por que ficou de fora |
|---|---|
| Chunk com prefixo de seção (`"[voto] …"`) | Exige reencode de tudo, ~10 h de GPU |
| Reranking com cross-encoder no top-100 | Caro, e muda a natureza do pipeline |
| Expansão de consulta (docT5query) | Fora do escopo declarado; o JurisTCU mediu +47% com isso, é o item mais forte de trabalhos futuros |
| Critério de densidade informativa independente da estrutura | É a hipótese alternativa que o controle aleatório não descarta — ver [02-controle-aleatorio.md](02-controle-aleatorio.md) |
| Segundo modelo denso (`embeddinggemma-300m`) | Exige `hf auth login`, e não muda nenhuma conclusão desta branch |
