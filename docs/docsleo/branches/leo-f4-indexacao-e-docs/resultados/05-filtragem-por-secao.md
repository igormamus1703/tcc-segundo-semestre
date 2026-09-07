# Filtragem por seção: a intervenção que funcionou

**Data:** 07/09/2026 · **Autor:** Leonardo Marques
**Status:** ⚠️ resultado **exploratório**, feito fora do pipeline oficial —
precisa ser reimplementado em `src/` antes de ir para o artigo
**Corpus:** 12.880 acórdãos · 150 consultas · 2.219 qrels · retriever denso (bge-m3)

---

## O raciocínio que levou até aqui

Três medições encadeadas, todas desta branch:

1. **A relevância mora na fundamentação.** O voto ocupa 22,5% dos chunks e
   concentra **72,0%** do conteúdo julgado relevante
   ([03-analise-do-dominio](../03-analise-do-dominio.md)).
2. **Mas os retrievers buscam no relatório.** 65–74% dos chunks que vencem a
   agregação vêm do relatório, que tem 66,8% dos chunks e só 25,7% da
   relevância ([04-denso-parcial](04-denso-parcial.md)). Eles acham o termo
   **onde há mais texto, não onde há mais informação**.
3. **A estratégia de chunking não muda isso** — nenhuma diferença significativa
   em 16 pares testados.

Daí a pergunta: **e se o problema não for *como cortar*, e sim *o que
indexar*?**

## O experimento

Reusando o cache de embeddings já calculado (custo: minutos, zero reencode),
filtramos o índice FAISS por seção e reavaliamos. As consultas foram encodadas
em CPU para não disputar a GPU.

| Configuração | Chunks | nDCG@10 | MAP@10 | Recall@100 |
|---|---:|---:|---:|---:|
| completo (baseline) | 286.689 | 0,1853 | 0,0706 | **0,4224** |
| só relatório | 191.389 | 0,1447 | 0,0555 | 0,3514 |
| só ementa | 12.893 | 0,1081 | 0,0397 | 0,1876 |
| só dispositivo | 17.778 | 0,1049 | 0,0386 | 0,1753 |
| só fundamentação | 64.629 | 0,2104 | 0,0857 | 0,3712 |
| fundamentação + ementa | 77.522 | 0,2147 | 0,0870 | 0,3837 |
| **tudo menos o relatório** | **95.300** | **0,2167** | **0,0881** | 0,3928 |

**Descartar o relatório melhora o nDCG@10 em 16,9% usando um terço dos
chunks.**

## É significativo — e não depende da estrutura ouro

| Comparação | p | vitórias / empates / derrotas |
|---|---:|---|
| completo × **sem relatório** (ouro) | **0,00098** ✅ | 40 / 28 / 82 |
| completo × só fundamentação (ouro) | **0,0128** ✅ | 50 / 27 / 73 |
| completo × **sem relatório** (predito) | **0,0165** ✅ | 40 / 33 / 77 |
| completo × só fundamentação (predito) | 0,431 | 50 / 28 / 72 |
| sem relatório: **ouro × predito** | **0,722** | 51 / 47 / 52 |

Duas leituras importantes:

**1. O ganho é real.** Com p = 0,001 (ouro) e p = 0,017 (predito), é o segundo
resultado significativo do trabalho — e o primeiro que representa uma
*melhoria*, não uma comparação entre alternativas equivalentes.

**2. Funciona com o nosso segmentador.** `sem relatório (ouro)` × `sem relatório
(predito)` dá **p = 0,722**, com 47 empates em 150 consultas: as duas versões
são equivalentes. **Não é preciso ter o acórdão publicado em colunas** — o
segmentador de regras com 92,2% de acurácia entrega o mesmo ganho. É isso que
torna o achado aplicável a um acervo real.

## O trade-off, que precisa ser reportado

**O Recall@100 cai**: 0,4224 → 0,3928 (−7,0%). Faz sentido — ao descartar dois
terços do índice, alguns documentos que só eram alcançáveis por um trecho do
relatório deixam de ser recuperados.

Ou seja: **ganha-se precisão no topo e perde-se cobertura na cauda.** Para um
pipeline de RAG, onde o que entra no contexto do LLM são os primeiros
documentos, o nDCG@10 é a métrica que importa mais — mas a limitação tem que
estar declarada, não escondida.

## Por que isto é uma contribuição, e não só uma otimização

O trabalho perguntava *"como cortar o documento?"* e a resposta medida foi
*"tanto faz"*. Este resultado reformula a pergunta para **"qual parte do
documento indexar?"** — e essa tem resposta: **a fundamentação; o relatório
atrapalha**.

O que sustenta a afirmação:

- O **mecanismo foi medido antes** da intervenção (concentração de relevância
  por seção), não inventado depois para explicar o número.
- O ganho é **significativo** e vale também com estrutura predita.
- O índice fica **67% menor**, o que é ganho de custo além do de qualidade.
- É a resposta natural ao descompasso que documentamos: o retriever busca onde
  há volume de texto, e o volume está na parte errada.

## ⚠️ O que falta antes disto virar resultado do artigo

Este teste foi exploratório, num script fora do `src/`. Para virar resultado:

- [ ] **Reimplementar no pipeline**, como uma opção de indexação
      (`--secoes fundamentacao,ementa,dispositivo`), com testes
- [ ] Rodar também no **BM25** — só testamos no denso. O BM25 é o retriever
      mais forte do trabalho, e o efeito pode ser diferente
- [ ] Rodar nas **outras estratégias de chunking**, não só na `structural_gold`
      e `structural_pred` (as fixas não rotulam seção, mas o offset permite
      atribuir uma — é o mesmo mecanismo do recorte por seção)
- [ ] Verificar o efeito por **tipo de consulta**: nas consultas reais de log,
      que são as mais difíceis, o ganho se mantém?
- [ ] Testar a variante **ponderada** (peso por seção em vez de corte binário),
      que preservaria o recall
- [ ] Bootstrap de IC 95% e análise de poder, como nos demais resultados

## Como reproduzir

Os scripts exploratórios estão em `%TEMP%\claude\teste_secao.py` e
`teste_secao2.py` — **não versionados de propósito**, porque a versão que vale
é a que for implementada em `src/`. O procedimento:

1. Carregar `data/processed/<estrategia>/emb_BAAI__bge-m3.npy` e
   `chunk_ids_BAAI__bge-m3.json`
2. Ler a seção de cada chunk em `chunks.jsonl`, na mesma ordem dos ids
3. Filtrar as linhas da matriz, montar `faiss.IndexFlatIP` e buscar
4. Agregar com `max_pooling` e avaliar com `ranx`
