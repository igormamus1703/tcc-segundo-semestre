# TCC — Segmentação Estrutural de Acórdãos para RI Jurídica

Comparação de estratégias de chunking (fixo, recursivo, estrutural) na
recuperação de informação sobre acórdãos do Tribunal de Contas da União
(TCU), avaliando BM25 e um retriever denso.

- **`plano_tecnico.md`** — plano completo: arquitetura, stack, cronograma
  (16 semanas) e roteiro de leitura. Documento de referência, não muda com
  frequência.
- **`plano_implementacao.md`** — plano de execução fase a fase (F0–F5),
  com os achados empíricos do corpus real e o que cada fase precisa
  entregar. **É este que diz "o que fazer agora"** — comece por ele.
- **`juris-chunking/`** — todo o código do pipeline (ingestão, segmentador,
  chunkers, indexação, avaliação). Ver `juris-chunking/README.md` para o
  setup e o status de cada fase.
- **`results/`** — resultados medidos: `corpus/` (caracterização do corpus) e
  `experiments/AAAAMMDD-HHMM_rotulo/` (uma pasta por rodada, com manifesto de
  reprodutibilidade). Ver `results/README.md`.
- **`docs/`** — caderno de bordo de cada integrante (`docs/docsleo/` etc.):
  decisões, achados e evidências que viram o texto do artigo.

> 📍 **Começando agora, ou voltando ao projeto?** Leia o **[PLANO.md](PLANO.md)**:
> estado atual, o que já foi feito, o que falta e quem decide o quê. Este README
> cobre o *como trabalhar*; o PLANO cobre o *o que fazer*.

## Onde o projeto está (07/09/2026)

| | |
|---|---|
| **Feito** | F0–F5 implementadas; corpus de 12.880 acórdãos; 2,2 M chunks; experimento 5 estratégias × 2 retrievers |
| **Resposta à pergunta do TCC** | O chunking estrutural **não** melhora a recuperação — nenhuma diferença é significativa, em nenhum retriever |
| **Resultado significativo** | **BM25 supera o retriever denso** (p < 0,001), o único resultado com significância |
| **Bloqueio** | 🔴 Decidir o corpus oficial: o artigo diz 113.827 documentos, o código produz 12.880 |
| **Testes** | 115 passando |

Detalhes, próximos passos e o que cada um pode pegar: **[PLANO.md](PLANO.md)**.
O status fase a fase está em `plano_implementacao.md`.

## Para quem está entrando no projeto agora

1. Clone o repositório.
2. Siga `juris-chunking/README.md` (seção "Setup") — venv, download dos
   datasets e montagem do corpus, nessa ordem. O primeiro download pesado
   é de ~6 GB; `scripts/README.md` explica como evitar problemas se o
   repositório estiver numa pasta sincronizada por nuvem (OneDrive/Drive/
   Dropbox).
3. Leia `plano_implementacao.md` seção 0 para entender a decisão de corpus
   (por que não usamos o JurisTCU cru) antes de mexer em qualquer coisa —
   evita redescobrir o que já foi decidido.

## Fluxo de trabalho obrigatório

**Vale para todo mundo que trabalha neste repositório, sem exceção.** Não são
recomendações: é o processo do projeto.

São quatro passos, nesta ordem: **branch → testar → anotar → merge**.

### 1. Trabalhe numa branch, nunca direto na `main`

```bash
git checkout -b <seu-nome>/<assunto-curto>     # ex.: leo/f4-indexacao-e-docs
```

A `main` só recebe código que já rodou e foi revisado. Commits pequenos, com
mensagem simples e direta dizendo **o que foi feito e por quê**. Nada de
linhas de co-autoria, assinatura de ferramenta ou emoji na mensagem: o commit
é do integrante da equipe, e este é um trabalho acadêmico com autoria em jogo.

### 2. Teste antes de pedir merge

```bash
cd juris-chunking && pytest -q     # tem que estar verde
```

Mudou comportamento? **Escreva o teste junto.** Dê preferência a testar o que
falha em silêncio — encoding, alinhamento de índices, cache inválido,
normalização divergente entre indexação e busca. Erro que estoura exceção você
descobre sozinho; o que só piora o número passa direto e vai parar no artigo.

Antes de rodar no corpus inteiro, faça o smoke test:

```bash
python -m src.chunkers.run --strategy all --limit-docs 500
python -m src.run_experiments --strategy all --retriever bm25 --limit-queries 10
```

### 3. Anote tudo na SUA pasta de documentação

**Toda a documentação da equipe fica dentro de `docs/`** — uma subpasta por
integrante, para não poluir a raiz do repositório:

```
docs/
└── docs<nome>/
    └── branches/
        └── <nome-da-branch>/
            ├── README.md        o que a branch faz + checklist de merge
            ├── NN-assunto.md    decisões, achados, execução
            └── resultados/      números medidos, com o comando que os gerou
```

| Integrante | Pasta |
|---|---|
| Leonardo Marques | `docs/docsleo/` ([exemplo pronto, use como modelo](docs/docsleo/)) |
| João Vitor Manfrim | `docs/docsjoao/` |
| Felipe Ribas | `docs/docsfelipe/` |
| Igor Mamus | `docs/docsigor/` |

Toda anotação precisa ter, no mínimo: **data e autor**, **o comando exato**
(copiável, não parafraseado), **o número que saiu** e o artefato que o
comprova, **a decisão tomada** e a alternativa descartada, e **o que ficou em
aberto**.

> **Por que isso é obrigatório e não burocracia:** o número **113.827
> documentos** entrou no nosso artigo e no nosso pôster, e só descobrimos que
> ele não corresponde ao que o código produz porque alguém foi ler a mensagem
> de um commit de agosto. Se a decisão de filtrar o corpus tivesse sido anotada
> quando foi tomada, o artigo nunca teria saído com o número errado. Ver
> [docs/docsleo/branches/leo-f4-indexacao-e-docs/02-achado-corpus.md](docs/docsleo/branches/leo-f4-indexacao-e-docs/02-achado-corpus.md).

**Nenhum número vai para o artigo sem estar anotado com o artefato que o
comprova.** Se você não consegue apontar o arquivo em `results/` que gerou
aquele valor, ele não entra.

**O mesmo vale para figuras.** Toda figura sai de `python -m src.plots`, que
estampa no rodapé a rodada, a data, o corpus, o modelo e o commit — lidos do
manifesto. Ao levar uma figura para a sua pasta de docs, coloque-a em
`resultados/figuras/<nome-da-rodada>/`, nunca solta. Uma imagem sem contexto
vira, em três semanas, um gráfico que ninguém sabe de onde veio.

### 4. Só então o merge

Abra o merge com o `README.md` da sua branch preenchido (o que mudou, testes
verdes, o que precisa de revisão) e **espere a revisão de quem é dono da fase
que você tocou**. Se a sua branch muda números que já estão no artigo ou no
pôster, diga isso explicitamente — é o tipo de mudança que não pode passar
despercebida.

### Regra final, que vale mais que as outras

**Reporte o que aconteceu, não o que devia ter acontecido.** Se o teste falhou,
diga que falhou e mostre a saída. Se o resultado deu nulo, escreva que deu
nulo. Um resultado nulo bem medido é um TCC completo (`plano_tecnico.md` §7);
um resultado inflado que a banca desmonta na defesa, não.

## Datasets

Não são versionados no Git (grandes demais). Ver `scripts/README.md` para
o script de download e `data/README.md` para a estrutura esperada depois
de baixar.
