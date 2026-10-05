# Reranker com cross-encoder: zero-shot e ajustado ao domínio

**Data:** 05/10/2026 · **Autor:** Leonardo Marques
**Código:** `src/rerank.py`, `src/finetune_reranker.py` · **Testes:** `tests/test_rerank.py`, `tests/test_finetune_reranker.py`

---

## O desenho

Documento longo → passagens → máximo (o MaxP de Dai & Callan 2019):

- **candidatos:** os 50 primeiros documentos de um run de primeiro estágio
  (o pré-registro dizia 100; o sidecar de cada run só guarda 50, ver adendo 1);
- **passagens:** os chunks que *venceram* cada documento em quatro buscas
  (BM25 e denso, com e sem relatório), até 4 por documento;
- **score do documento:** o maior score do `BAAI/bge-reranker-v2-m3` entre
  as passagens (janela de 1.024 tokens);
- **variantes, com os mesmos candidatos:**
  - `todas`: lê qualquer passagem;
  - `sem_relatorio`: só passagens fora do relatório. Quem não tem nenhuma
    vai para depois dos lidos, ou seja, é rebaixado;
  - `sem_relatorio_preserva` (exploratória): idem, mas quem só tem passagem
    de relatório é lido por ela. Separa o efeito de *o que se lê* do efeito de
    *quem é rebaixado*.

Os scores de cada par (consulta, chunk) vão para um cache em disco com
checkpoint: 12 mil pares no JurisTCU, 122 mil no JUÁ (~25 min a ~90 pares/s).

## Zero-shot: H6 e H7

Candidatos: a fusão das 4 da F6 (`fixed_512_256`).

| | JurisTCU | JUÁ-Juris (teste) |
|---|---:|---:|
| BM25 completo | 0,2490 | 0,2497 |
| fusão das 4 (os candidatos) | **0,3215** | 0,2215 |
| reranker, `todas` | 0,2704 | 0,2392 |
| reranker, `sem_relatorio` | 0,3189 | 0,2231 |
| reranker, `sem_relatorio_preserva` | 0,2629 | 0,2168 |
| documentos sem passagem permitida (`sem_relatorio`) | 16,6% | 13,8% |

| Comparação | JurisTCU | JUÁ-Juris |
|---|---:|---:|
| **H6** · reranker `todas` × fusão das 4 | **−15,9%** (p < 10⁻⁵) | +8,0% (p = 0,017) |
| **H7** · `sem_relatorio` × `todas` | **+17,9%** (p < 10⁻⁶) | **−6,7%** (p = 0,009) |
| `sem_relatorio_preserva` × `todas` | −2,8% (p = 0,31) | −9,4% (p < 10⁻⁵) |
| reranker `todas` × BM25 completo | +8,6% (p = 0,05) | −4,2% (p = 0,15) |

**H6 falha nas duas coleções:** o reranker genérico não supera a melhor
configuração de primeiro estágio. No JUÁ ele recupera parte do que a fusão da
F6 perdeu (+8%), mas não passa do BM25.

**H7 confirma no JurisTCU e se inverte no JUÁ**, o mesmo padrão do primeiro
estágio ([03](03-fronteira-e-criterio-toca.md)). Duas leituras:

1. **No JurisTCU, o ganho de H7 vem do rebaixamento, não da leitura.** A
   variante que preserva os documentos só-relatório perde o ganho todo
   (−2,8%, n.s.). Ou seja: ler a fundamentação em vez do relatório não muda
   muito o score que o modelo dá a um documento; o que ajuda é **empurrar para
   baixo os documentos cuja única evidência é o relatório**. É o mesmo
   mecanismo do recorte da F6, agora no segundo estágio.
2. **Até um modelo neural que lê consulta e passagem juntas se deixa levar
   pelo relatório no JurisTCU.** O efeito de interferência não é artefato do
   BM25.

## Ajustado ao domínio (LoRA)

*(preenchido quando o treino terminar)*
