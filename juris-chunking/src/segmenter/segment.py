"""Aplica as regras de rules.py e devolve spans rotulados.

Algoritmo (seção F2 do plano_implementacao.md): localizar todas as
ocorrências de `SECTION_PATTERNS`, ordenar por posição e aceitar só as
que avançam o estado em `SECTION_ORDER` (relatorio -> fundamentacao ->
dispositivo) — isso já faz o dedupe (uma seção só "começa" uma vez) e
evita que uma frase-marcador recorrente (ex.: "Trata-se de" reaparecendo
dentro do voto) crie uma fronteira espúria depois que o estado já avançou.

Exceção: `dispositivo` é buscado só DEPOIS da última transição já aceita
(não desde o início do texto como as demais). Motivo (achado empírico):
acórdãos frequentemente citam um acórdão anterior por inteiro como
precedente, ainda na ementa/relatório ("...de seguinte teor, in verbis:
'ACÓRDÃO Nº 059/2002 [...] VISTOS, relatados e discutidos [...]'"), o
que dispara o marcador de VISTOS muito antes do dispositivo real. Restringir
a busca ao trecho após a última seção já encontrada elimina essas citações
sem precisar da última ocorrência do documento inteiro — o próprio
dispositivo às vezes cita OUTRO acórdão dentro de si (ex.: no item "9.x"),
e usar a última ocorrência do texto inteiro pularia esse trecho citado e
perderia parte do dispositivo real (medido: piora a cobertura de
`dispositivo` de 96% para 80% num teste com 3000 docs). Por isso a regra
final é "primeira ocorrência após a transição anterior", não "primeira do
documento" nem "última do documento".

`ementa` não tem padrão próprio (ver rules.py): se a primeira marca aceita
for `relatorio`, o prefixo [0, marca) é rotulado `ementa`. Se a primeira
marca aceita for outra (ex.: o segmentador só achou `dispositivo`, sem
achar a abertura do relatório), o prefixo é `FALLBACK_LABEL` — não dá para
distinguir ementa de relatório dentro dele com as marcas disponíveis, e
fingir que é só ementa mascararia esse buraco na cobertura.

Fallback quando nenhuma marca é encontrada: documento inteiro rotulado
como FALLBACK_LABEL ("indefinido"). A taxa de fallback deve ser reportada
como resultado em si (ver E2 do plano_tecnico.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from .rules import FALLBACK_LABEL, SECTION_ORDER, SECTION_PATTERNS


@dataclass
class LabeledSpan:
    doc_id: str
    section: str  # um de: ementa | relatorio | fundamentacao | dispositivo | indefinido
    start: int
    end: int


class Segmenter:
    def _forward_transitions(self, text: str) -> list[tuple[int, str]]:
        """Todas as ocorrências de SECTION_PATTERNS, ordenadas por posição,
        filtradas para só avançar em SECTION_ORDER (dedupe + anti-retrocesso).

        `dispositivo` é tratado à parte: usa a ÚLTIMA ocorrência do
        marcador (não a primeira) — ver docstring do módulo."""
        last_label = SECTION_ORDER[-1]
        matches: list[tuple[int, str]] = [
            (m.start(), label)
            for label, pattern in SECTION_PATTERNS
            for m in pattern.finditer(text)
            if label != last_label
        ]
        matches.sort(key=lambda item: item[0])

        transitions: list[tuple[int, str]] = []
        state = -1  # -1 = antes de qualquer seção conhecida (ementa implícita)
        for pos, label in matches:
            idx = SECTION_ORDER.index(label)
            if idx <= state:
                continue
            state = idx
            transitions.append((pos, label))

        floor = transitions[-1][0] if transitions else -1
        candidates = [
            m.start()
            for label, pattern in SECTION_PATTERNS
            if label == last_label
            for m in pattern.finditer(text)
            if m.start() > floor
        ]
        if candidates:
            transitions.append((min(candidates), last_label))

        return transitions

    def segment(self, doc_id: str, text: str) -> list[LabeledSpan]:
        if not text:
            return []

        transitions = self._forward_transitions(text)
        if not transitions:
            return [LabeledSpan(doc_id, FALLBACK_LABEL, 0, len(text))]

        spans: list[LabeledSpan] = []
        first_pos, first_label = transitions[0]
        if first_pos > 0:
            prefix_label = "ementa" if first_label == "relatorio" else FALLBACK_LABEL
            spans.append(LabeledSpan(doc_id, prefix_label, 0, first_pos))

        for i, (pos, label) in enumerate(transitions):
            end = transitions[i + 1][0] if i + 1 < len(transitions) else len(text)
            spans.append(LabeledSpan(doc_id, label, pos, end))

        return spans

    def fallback_rate(self, spans_by_doc: dict[str, list[LabeledSpan]]) -> float:
        """Fração de documentos cujo único span é FALLBACK_LABEL."""
        if not spans_by_doc:
            return 0.0
        n_fallback = sum(
            1
            for spans in spans_by_doc.values()
            if len(spans) == 1 and spans[0].section == FALLBACK_LABEL
        )
        return n_fallback / len(spans_by_doc)
