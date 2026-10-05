# Status do TCC — a validação externa (F7)

**5 de outubro de 2026 · Leonardo Marques**

Resumo do que a F7 mudou, escrito para ser lido antes da reunião. O detalhe
técnico, com os artefatos de cada número, está em
[`docs/docsleo/branches/leo-f7-evolucao/`](docs/docsleo/branches/leo-f7-evolucao/);
a versão visual, em [`docs/apresentacao/f7.html`](docs/apresentacao/f7.html).

> ⚠️ A branch `leo/f7-evolucao` **não foi mergeada**. Tudo aqui está validado
> localmente e espera a decisão da equipe.

---

## 1. Por que a F7 existia

A F6 terminou com +29% de nDCG@10 ao tirar o relatório do índice. Mas esse
número tinha duas fraquezas que eu mesmo apontei na revisão:

- **150 consultas.** Diferenças menores que ~0,02 eram indetectáveis, e nas 50
  consultas reais de log nem o ganho principal era significativo.
- **Circularidade.** A decisão de cortar o relatório veio de olhar os mesmos
  julgamentos de relevância usados para medir.

Nenhuma análise sobre as mesmas 150 consultas resolve isso. Era preciso uma
coleção nova.

## 2. A coleção nova, de graça

O **JUÁ-Juris** (Pereira et al., 2026) é um benchmark montado sobre a mesma
base de jurisprudência do TCU, e usa as **mesmas chaves de documento** do
JurisTCU. Com isso, levei as consultas dele direto aos nossos 12.880 acórdãos,
com os mesmos índices: **zero reencode**.

| Amostra | Consultas | O que mede |
|---|---:|---|
| JurisTCU (F4–F6) | 150 | "quais acórdãos firmam esta tese?" (graduada, ~15 relevantes) |
| JUÁ difícil (teste) | 1.567 | "qual é o acórdão deste enunciado?" (1 relevante; montado com consultas que o BM25 erra) |
| JUÁ natural (treino) | 6.000 | a mesma tarefa, na distribuição natural |

**Antes de rodar qualquer número**, as previsões foram escritas e commitadas
([pré-registro](docs/docsleo/branches/leo-f7-evolucao/00-preregistro.md)).
Foi a primeira vez no trabalho que fizemos isso, e foi o que permitiu
distinguir descoberta de pescaria.

## 3. O que aconteceu

### 3.1 O recorte da F6 quebrou no JUÁ

Nas consultas difíceis do JUÁ, tirar o relatório **piorou** 13% a 21% nas
estratégias de corte fixo e recursivo. Nas estruturais, quase não mexeu.

### 3.2 A causa: a ementa ia para o lixo junto

No corte fixo, o primeiro pedaço do acórdão junta a **ementa inteira** com o
começo do relatório. Como a maioria dos caracteres é de relatório, o pedaço é
rotulado "relatório" e sai do índice com a ementa dentro. No JUÁ, a consulta é
um enunciado, que costuma repetir a ementa quase palavra por palavra. **Em 54%
das perdas grandes, era exatamente isso.**

### 3.3 A correção, confirmada em dados que nunca tínhamos olhado

O critério novo (`toca`) só descarta pedaços **100% relatório**. Como ele foi
desenhado olhando o JUÁ difícil, registrei a previsão e testei nas 6.000
consultas naturais, nunca usadas:

| Recorte "sem relatório" (fixo 512/256, BM25) | JurisTCU | JUÁ natural | JUÁ difícil |
|---|---:|---:|---:|
| critério da F6 | +16,2% | +8,1% | **−12,6%** |
| **critério `toca`** | **+15,6%** | **+9,7%** (p < 10⁻⁹⁵) | **+5,5%** |

**O `toca` é a única versão que ganha nas três amostras.** Uma das três
previsões errou ("a F6 também piora nas naturais": na verdade melhora 8%), e
o erro mostrou que o dano da F6 vivia só nas consultas difíceis.

### 3.4 A pergunta original do TCC, finalmente com poder

Na F5, as cinco estratégias de corte empataram. Com 10× mais consultas:

| Estrutural (predito) × … | JurisTCU | JUÁ natural | JUÁ difícil |
|---|---:|---:|---:|
| fixo 512/256 | n.s. | **+1,2%** (p = 0,005) | **+7,3%** (p = 0,0001) |
| recursivo | n.s. | **+2,4%** (p < 10⁻⁸) | **+9,9%** (p < 10⁻⁵) |
| estrutural (ouro) | **equivalentes** | **equivalentes** | **equivalentes** |

**O corte que respeita as seções vence, e o nosso segmentador é
estatisticamente equivalente à estrutura oficial** (teste de equivalência,
margem ±0,01). E sabemos o porquê: tirando a ementa do índice estrutural, a
vantagem vira desvantagem (−21% contra o fixo nas difíceis). O corte
estrutural ganha porque isola a ementa. No JurisTCU, onde a ementa quase não
carrega relevância, não há efeito, e isso explica o empate da F5.

### 3.5 Um modelo que aprende o peso de cada seção

Em vez de decidir à mão o que cortar, treinei um ranqueador (LambdaRank) com
doze sinais de busca (o acórdão inteiro, sem o relatório e cada seção
isolada) em consultas do JUÁ, e o testei **no JurisTCU, que ele nunca viu**:

- com os sinais por seção: **+16,5%** sobre o mesmo modelo sem eles, e
  **+18,6%** sobre o BM25 (p < 0,0001);
- empata com a fusão da F6 no JurisTCU, onde ela foi ajustada, e ganha dela
  por 11% a 25% no JUÁ.

Abrindo o modelo (SHAP), aparece a regra da F6, **aprendida dos dados**: o
mesmo casamento de termos vale **cerca de 5× menos** quando acontece no
relatório do que na fundamentação, nas duas coleções.

### 3.6 Um modelo neural também se engana

O reranker `bge-reranker-v2-m3` sem ajuste **piora** a melhor configuração
da F6 no JurisTCU (−15,9%); impedido de ler o relatório, recupera tudo
(+17,9%). A interferência do relatório não é um artefato do BM25. Ajustei o
reranker com LoRA em 5 mil consultas do treino do JUÁ, com o trecho exato da
resposta como positivo: **[resultado a completar quando a avaliação terminar]**.

## 4. O que muda no artigo

**A tese fica mais forte e mais honesta:**

1. *Como cortar o documento?* → **A estrutura importa, mas pouco, e só em
   consultas que se parecem com a ementa.** Com 7.567 consultas novas, o corte
   estrutural vence de forma consistente, e o segmentador automático basta.
2. *Qual parte indexar?* → **Tire o relatório, mas só os pedaços que são 100%
   relatório.** A versão da F6 tinha um modo de falha conhecido e corrigido.
3. *E se não quisermos decidir à mão?* → **Um modelo aprende os pesos e chega
   à mesma regra**, transferindo entre coleções.

**A ligação entre as perguntas, que dá unidade ao texto:** quando o pipeline
seleciona conteúdo por seção, a estrutura do corte deixa de ser detalhe. É ela
que separa um ganho robusto de um ganho que inverte de sinal.

## 5. Limitações que ficam

- As 50 consultas reais de log do JurisTCU **continuam sem poder**: todas as
  configurações melhoram, nenhuma é significativa.
- O JUÁ mede uma tarefa diferente (*known-item*, consultas em forma de tese).
  A vantagem estrutural vale para ela.
- A decisão de corpus (12.880 × 113.827) continua aberta, e vale para estes
  números também.

## 6. O que preciso decidir com a equipe

1. 🔴 **Mergear a F7?** Pelo critério escrito no pré-registro, ela passa: H1
   não replicou como estava, mas a correção (H8b) confirmou em dados não
   vistos, e a pergunta original ganhou resposta com poder.
2. 🟠 **A tabela principal do artigo** passa a ter três colunas (JurisTCU, JUÁ
   natural, JUÁ difícil) e a receita recomendada passa a ser o `toca`.
3. 🟡 **Ainda o corpus** (pendente desde 05/09).

## Estado técnico

| | |
|---|---|
| Branch | `leo/f7-evolucao`, local, não mergeada |
| Módulos novos | `jua`, `rerank`, `finetune_reranker`, `ltr`, `replicacao`, `painel` |
| Mudança em código existente | só o parâmetro `criterio` em `sections.filtrar` (padrão reproduz a F6) |
| Reprodução | `.\scripts\rodada_f7.ps1` refaz a F7 inteira, pulando o que já existe |
| Bugs achados no caminho | normalização desalinhada no LTR v1; truncamento no fine-tune; ambos travados |
