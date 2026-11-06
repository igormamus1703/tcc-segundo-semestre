# Branch `leo/fechamento` — encerramento do projeto

**Autor:** Leonardo Marques · **Data:** 06/11/2026 · **Status:** ✅ mergeada na `main` em 06/11/2026

Fecha as pontas soltas antes da entrega dos artefatos. **Nenhum número muda.**

## O que mudou

| O quê | Por quê |
|---|---|
| `src/replicacao.py`, `configs/f7_replicacao.json`, `configs/f7_replicacao_final.json` e `tests/test_replicacao.py` trazidos da `leo/f7-evolucao` | A rodada `20261005-2216_f7_replicacao_final`, de onde saem as tabelas da F7 usadas no artigo, estava na `main` sem o código que a gerou. Os módulos compartilhados são idênticos nas duas branches, então os arquivos entram sem adaptação |
| JUÁ-Juris no `scripts/download_datasets.py` | O `src/jua.py` dependia de um dataset que nenhum script baixava |
| Documentação no estado final | README, PLANO, planos e READMEs das pastas ainda falavam em F0–F6, 191 testes e corpus em aberto; o rascunho de texto da F7 completa não dizia que foi superado pela decisão de escopo de 06/10 |
| Branch `leo/f7-enxuta` apagada do GitHub | Já estava inteira na `main`; manter duas branches da F7 confundia quem visita o repositório |

## Como verificar

```bash
cd juris-chunking && pytest -q              # 206 passed
python -m src.replicacao --help
cd .. && python scripts/download_datasets.py jua   # baixa, ou confere que já existem, os 4 arquivos do JUÁ
```

Resultado em 06/11/2026:

- **206 passed** (201 + os 5 da replicação).
- Os quatro arquivos do JUÁ-Juris no Hugging Face têm o mesmo tamanho dos
  usados nos experimentos, baixados em 05/10/2026.
- O download de `qrels/test.tsv` numa pasta vazia criou a subpasta `qrels/` e
  gerou um arquivo com SHA-256 idêntico ao local.

## Decisões

- **A F7 que vai para o artigo é a enxuta.** A decisão é de 06/10 e está no
  §5 do [README da leo-f7-enxuta](../leo-f7-enxuta/README.md); esta branch só
  a deixa explícita nos documentos que ainda não diziam isso.
- **A `leo/f7-evolucao` continua no GitHub, sem merge,** como registro do que
  foi tentado (ranker aprendido, reranker com cross-encoder e ajuste fino,
  com ganho pequeno ou negativo para a complexidade acrescentada) e como base
  para trabalhos futuros.
- **A especificação final da replicação cita rodadas da exploração** (fusão no
  JUÁ, ranker aprendido, reranker), que só existem na branch-arquivo. Ficou
  como está, porque é o arquivo que gerou a tabela; para refazer essas linhas
  é preciso a branch-arquivo.
- **Não foram regeradas as tabelas da F5** calculadas antes da correção do bug
  dos empates. O efeito é na terceira casa decimal dos recortes, IC e poder;
  as médias não mudam (conferido na rodada `20260906-0515_bm25`). Fica
  registrado no `PLANO.md` e no `plano_implementacao.md`.

## Em aberto

- Escrever o artigo com a F7 enxuta (próxima fase da entrega).
