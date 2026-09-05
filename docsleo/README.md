# docsleo — caderno de bordo do Leonardo Marques

Registro **completo** do que foi feito, decidido e medido neste projeto, na
minha frente de trabalho. Não é documentação de código (essa vive nos
`README.md` do repo) — é o **histórico de decisões e evidências**, escrito
para virar matéria-prima das seções de Metodologia, Resultados e Discussão
do artigo final.

Regra que sigo aqui: **toda decisão registrada tem que dizer (a) qual era a
alternativa, (b) qual evidência decidiu, e (c) o que muda no artigo se a
decisão for revertida.** Decisão sem evidência anotada é decisão que vamos
ter que redescobrir em novembro, na semana da entrega.

---

## Convenção da equipe — vale para todos, não só para mim

> **Cada participante do projeto mantém a sua própria pasta de resultados com
> anotações em `.md`, e anota tudo lá: o que fez, o que decidiu, o que mediu,
> o que deu errado e por quê.**

Pastas por participante (mesma estrutura, um dono cada):

| Participante | Pasta |
|---|---|
| Leonardo Marques | `docsleo/` |
| João Vitor Manfrim | `docsjoao/` |
| Felipe Ribas | `docsfelipe/` |
| Igor Mamus | `docsigor/` |

Por que isso importa, concretamente: o número **113.827 documentos** entrou no
nosso artigo e no nosso pôster, e só descobrimos que ele não corresponde mais
ao que o código produz porque fomos ler a mensagem de um commit de agosto (ver
[02-achado-corpus.md](02-achado-corpus.md)). Se a decisão de filtrar o corpus
tivesse sido anotada em `.md` quando foi tomada, o artigo nunca teria saído com
o número errado. **Anotar não é burocracia — é o que impede a banca de achar
antes da gente.**

O que cada anotação precisa ter, no mínimo:
- **data** e **quem fez**;
- **o comando exato** que foi rodado (copiável, não parafraseado);
- **o número que saiu** (com o arquivo de artefato que o comprova);
- **a decisão tomada** e a alternativa descartada;
- **o que ainda está em aberto**.

---

## Índice

| Doc | Conteúdo |
|---|---|
| [01-ambiente-setup.md](01-ambiente-setup.md) | Como o ambiente foi montado nesta máquina, versões exatas, e o único passo manual obrigatório do projeto |
| [02-achado-corpus.md](02-achado-corpus.md) | **Crítico:** o corpus do código (12.881) ≠ o corpus do artigo (113.827). Evidência, causa e as opções |
| [03-referencias-verificadas.md](03-referencias-verificadas.md) | Verificação de todas as citações do artigo contra o arXiv — nenhuma citação fantasma |
| [04-modelos-embedding.md](04-modelos-embedding.md) | Escolha do embedder via MTEB-BR; resolve o `PREENCHER` do `models.yaml` |
| [05-diario-execucao.md](05-diario-execucao.md) | Diário cronológico: comandos rodados, saídas, tempos |
| [06-implementacao-f4.md](06-implementacao-f4.md) | F4/F5 implementadas: decisões de projeto e as armadilhas de biblioteca encontradas |
| [07-numeros-para-o-artigo.md](07-numeros-para-o-artigo.md) | **Tabela de substituição:** cada número do artigo × o valor medido. Nenhum número entra no texto final sem passar por aqui |
