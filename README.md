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

## Datasets

Não são versionados no Git (grandes demais). Ver `scripts/README.md` para
o script de download e `data/README.md` para a estrutura esperada depois
de baixar.
