"""Regex das macro-seções do acórdão (E2 do plano_tecnico.md; calibrado
seção 149-156 do plano_implementacao.md).

Calibrado sobre o corpus real (ver `data/interim/corpus_docs.jsonl`), não
sobre suposições do plano técnico original: os marcadores tipográficos
`EMENTA`, `RELATÓRIO` e `VOTO` (usados na v0 do plano técnico) quase não
ocorrem no texto — as colunas do CSV do TCU trazem o conteúdo da seção sem
o cabeçalho (ver seção 1 do plano_implementacao.md).

- `ementa` não tem marcador próprio: é sempre a primeira seção quando
  presente (ordem canônica de `ingest.assemble_document`), então o
  segmentador a infere como o prefixo antes do primeiro marcador de
  `relatorio` — ver docstring de `segment.py`.
- Abertura de `relatorio`: dezenas de fórmulas de abertura levantadas por
  amostragem estatística sobre milhares de acórdãos (`Trata-se`, `Cuidam
  os autos`, `Adoto como relatório`, `Por registrar as [...]`, etc.).
- Fronteira `relatorio` -> `fundamentacao`: "É o relatório".
- Fronteira `fundamentacao` -> `dispositivo`: a coluna ACORDAO
  praticamente sempre abre com "VISTOS, relatados e discutidos"; a busca
  é restrita ao trecho após a transição anterior (ver `segment.py`) para
  não confundir com citações de acórdãos anteriores transcritas por
  inteiro no relatório/voto.

Curva de iteração — `python -m src.segmenter.validate` no corpus inteiro
(113.827 acórdãos), acurácia global por caractere contra os spans ouro:

| iteração | acurácia global | causa da mudança |
|---|---|---|
| v0 (padrões do plano técnico, sem cabeçalho no texto) | não medível (~0% de match) | marcadores certos não ocorrem no texto assemblado |
| v1 (padrões calibrados por amostra; 1ª ocorrência de tudo) | 0.6973 | baseline funcional |
| v2 (`dispositivo`: busca só após a transição anterior, 1ª ocorrência) | 0.7581 | citação de acórdão anterior ("in verbis: 'ACÓRDÃO [...] VISTOS...'") disparava `dispositivo` cedo demais |
| v3 (+ "Adoto como relatório", maior cobertura de aberturas) | 0.8928 | ~25% dos relatórios abrem com essa fórmula, ausente da v1 |
| v4 (+ "Por registrar as [...]", prefixo numerado "2. Adoto...") | 0.9249 | boilerplate comum antes do verbo principal |
| v5 final (+ "Inicialmente,", `Tratam-se`, `Incorporo a este relatório`, `Examinam-se`, `Aprecia-se`) | **0.9271** | cauda longa de variantes de abertura; ganho marginal — convergiu |

Resultado final por seção (`results/tables/segmenter_validation.json`):
cobertura/precisão de `relatorio` 0.928/0.981, `fundamentacao`
0.907/0.952, `dispositivo` 0.989/0.790, `ementa` 0.935/0.561.
`fallback_rate` (doc inteiro "indefinido") = 1.64%.

Limitação conhecida (discutir no TCC): `ementa` e `dispositivo` têm
precisão mais baixa porque ambos herdam erro de fronteira alheio —
`ementa` é o prefixo até o marcador de `relatorio` (se esse marcador cair
depois do início real do relatório, o excesso vira "ementa" por engano);
`dispositivo` frequentemente extrapola o fim real do doc quando o texto
final tem itens numerados extensos que o gold_span de ACORDAO já cobria
por inteiro mas cuja fronteira interna (VISTOS de citação embutida) o
regex ainda confunde em ~21% dos casos. `relatorio` e `fundamentacao` são
os mais confiáveis (>90% em ambas as métricas) — coerente com serem as
seções mais usadas na comparação `structural_pred` vs. `structural_gold`.
"""

from __future__ import annotations

import re

# Cada entrada: (rótulo de seção, padrão que marca o INÍCIO da seção).
# `ementa` não entra aqui de propósito (ver docstring do módulo).
SECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "relatorio",
        re.compile(
            # `(?:\d+\.\s*)?` e `(?:Inicialmente,?\s+)?` no início: muitos
            # relatórios abrem com numeração de parágrafo ("2. Adoto como
            # relatório...") e/ou "Inicialmente, " antes do verbo principal.
            r"^\s*(?:\d+\.\s*)?(?:Inicialmente,?\s+)?(?:"
            r"Trata(?:-se|m-se)|Cuida-se|Cuida o presente|"
            r"Cuidam(?:-se)? os (?:presentes )?autos|"
            r"Tratam os (?:presentes )?autos|"
            r"Adoto,? como (?:o )?[Rr]elat[óo]rio|Adoto como parte|"
            r"Incorporo a (?:este|o) relat[óo]rio|"
            r"Por registrar as|"
            r"Versam? (?:os autos|estes autos|a presente)|"
            r"Em exame|Examina[m]?-se|Trata o presente processo|Este processo|"
            r"O presente processo|Os presentes autos|Apreci[ao](?:m)?-se|"
            r"Permito-me (?:transcrever|adotar)|"
            r"Em (?:sess[ãa]o|aprecia[çc][ãa]o)|Transcrevo|Reproduzo|"
            r"Inicio (?:este relat[óo]rio|o (?:presente )?relat[óo]rio)|"
            r"Documento classificado como"
            r")\b",
            re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "fundamentacao",
        re.compile(r"\bÉ\s+o\s+[Rr]elat[óo]rio\.?", re.IGNORECASE),
    ),
    (
        "dispositivo",
        re.compile(
            r"^\s*(?:"
            r"VISTOS?,?\s+relatados?\s+e\s+discutidos?|"
            r"ACORDAM\s+os\s+Ministros|Os\s+Ministros\s+do\s+Tribunal|"
            r"O\s+Tribunal\s+Pleno|O\s+Plen[áa]rio,?\s+diante|"
            r"A\s+(?:Primeira|Segunda)\s+C[âa]mara,?\s+diante"
            r")\b",
            re.MULTILINE | re.IGNORECASE,
        ),
    ),
]

# Ordem canônica de transição — usada por segment.py para aceitar só
# marcas que avançam o estado (evita retrocesso e falsos positivos depois
# que uma seção posterior já foi encontrada).
SECTION_ORDER: list[str] = ["relatorio", "fundamentacao", "dispositivo"]

FALLBACK_LABEL = "indefinido"
