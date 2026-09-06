# docsleo — caderno de bordo do Leonardo Marques

Registro do que eu fiz, decidi e medi neste projeto. Não é documentação de
código (essa vive nos `README.md` do repo) — é o **histórico de decisões e
evidências**, escrito para virar matéria-prima das seções de Metodologia,
Resultados e Discussão do artigo final.

> O padrão de trabalho da equipe (branch → teste → merge → anotar) está no
> [README.md da raiz do repositório](../../README.md#fluxo-de-trabalho-obrigatório).
> Esta pasta é a minha instância desse padrão.

Regra que sigo aqui: **toda decisão registrada diz (a) qual era a alternativa,
(b) qual evidência decidiu e (c) o que muda no artigo se ela for revertida.**
Decisão sem evidência anotada é decisão que vamos ter de redescobrir em
novembro, na semana da entrega.

## Organização

```
docsleo/
└── branches/
    └── <nome-da-branch>/        uma pasta por branch de trabalho
        ├── README.md            o que a branch faz + checklist de merge
        ├── NN-*.md              decisões, achados e execução
        ├── testes/              estado da suíte e o que cada teste trava
        └── resultados/          números medidos, por retriever
```

## Branches

| Branch | Assunto | Status |
|---|---|---|
| [leo/f4-indexacao-e-docs](branches/leo-f4-indexacao-e-docs/) | F4 (indexação e runs) + F5 (avaliação), e a divergência de corpus | 🟡 em teste |

## Atalhos para o que mais importa

| Se você quer... | Vá em |
|---|---|
| Entender o problema mais urgente do projeto | [02-achado-corpus.md](branches/leo-f4-indexacao-e-docs/02-achado-corpus.md) |
| Saber quais números do artigo estão errados | [07-numeros-para-o-artigo.md](branches/leo-f4-indexacao-e-docs/07-numeros-para-o-artigo.md) |
| Saber o que precisa ser decidido pela equipe | [08-decisoes-pendentes.md](branches/leo-f4-indexacao-e-docs/08-decisoes-pendentes.md) |
| Ver o primeiro nDCG@10 e os recortes | [resultados/](branches/leo-f4-indexacao-e-docs/resultados/) |
| Montar o ambiente numa máquina nova | [01-ambiente-setup.md](branches/leo-f4-indexacao-e-docs/01-ambiente-setup.md) |
