"""E1 — Ingestão e caracterização (plano_implementacao.md, seções 0-1).

Corpus final = acórdãos íntegros do TCU (dados abertos, um CSV por ano,
2003-2023), montados a partir das colunas de seção (SUMARIO, RELATORIO,
VOTO, DECLARACAOVOTO, VOTOCOMPLEMENTAR, VOTOMINISTROREVISOR, ACORDAO), com
as fronteiras dessas colunas registradas como spans "ouro". Os qrels e as
150 queries vêm do JurisTCU e são remapeados de doc_id (excerto) para
doc_id (acórdão) via join por (NUMACORDAO, ANOACORDAO, COLEGIADO).

O download dos CSVs é feito por `scripts/download_datasets.py tcu_acordaos`
e `... juristcu` (raiz do repositório), para <raiz>/data/. Este módulo lê a
partir de lá.

GATE RESIDUAL: se o join cobrir menos de 90% dos acórdãos referenciados ou
menos de 90% das entradas de qrel forem preservadas, parar e revisar (ver
seção 0.5 do plano_implementacao.md) — não seguir silenciosamente com um
corpus degradado.
"""

from __future__ import annotations

import csv
import html
import json
import re
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

csv.field_size_limit(2**28)


def _format_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


class Progress:
    """Log de progresso por tempo decorrido (não por \\r) — para ficar
    visível ao ler o output de um processo em background, não só num
    terminal interativo. Uma linha a cada `interval` segundos, no máximo."""

    def __init__(self, label: str, total: int | None = None, interval: float = 2.0):
        self.label = label
        self.total = total
        self.interval = interval
        self.start = time.monotonic()
        self._last_print = 0.0
        self._done = False

    def update(self, current: int, extra: str = "", force: bool = False) -> None:
        now = time.monotonic()
        if not force and (self._done or now - self._last_print < self.interval):
            return
        self._last_print = now
        elapsed = now - self.start
        if self.total:
            pct = min(current / self.total * 100, 100.0)
            rate = current / elapsed if elapsed > 0 else 0
            eta = (self.total - current) / rate if rate > 0 else 0
            msg = (
                f"  [{self.label}] {pct:5.1f}% "
                f"({_format_bytes(current)}/{_format_bytes(self.total)}) "
                f"decorrido={elapsed:5.1f}s eta={eta:5.1f}s"
            )
        else:
            msg = f"  [{self.label}] {current} processados, decorrido={elapsed:5.1f}s"
        if extra:
            msg += f" {extra}"
        print(msg, flush=True)

    def done(self, extra: str = "") -> None:
        elapsed = time.monotonic() - self.start
        msg = f"  [{self.label}] concluído em {elapsed:5.1f}s"
        if extra:
            msg += f" — {extra}"
        print(msg, flush=True)
        self._done = True

# juris-chunking/src/ingest.py -> parent.parent.parent = raiz do repositório
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_ROOT = REPO_ROOT / "data"

JURISTCU_DIR = DATA_ROOT / "juristcu"
JURISTCU_DOCS = JURISTCU_DIR / "doc.csv"
JURISTCU_QUERIES = JURISTCU_DIR / "query.csv"
JURISTCU_QRELS = JURISTCU_DIR / "qrel.csv"

TCU_DIR = DATA_ROOT / "tcu_acordaos"
TCU_YEARS = range(2003, 2024)

INTERIM_DIR = Path(__file__).resolve().parent.parent / "data" / "interim"
RESULTS_TABLES_DIR = Path(__file__).resolve().parent.parent.parent / "results" / "tables"

# Ordem canônica de montagem do texto do acórdão -> rótulo Section (base.py).
# Ver tabela da seção 0 do plano_implementacao.md.
SECTION_COLUMNS: list[tuple[str, str]] = [
    ("SUMARIO", "ementa"),
    ("RELATORIO", "relatorio"),
    ("VOTO", "fundamentacao"),
    ("DECLARACAOVOTO", "fundamentacao"),
    ("VOTOCOMPLEMENTAR", "fundamentacao"),
    ("VOTOMINISTROREVISOR", "fundamentacao"),
    ("ACORDAO", "dispositivo"),
]

_CITATION_TAG = re.compile(
    r"<(acordao_decisao_tcu|processo)\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL
)
_PARA_BREAK_TAG = re.compile(r"</(p|td|tr)>", re.IGNORECASE)
_LINE_BREAK_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<[^>]+>")
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_BLANK_LINE = re.compile(r"\n{3,}")


def normalize_html(raw: str | None) -> str:
    """Normaliza uma coluna de texto do CSV de acórdãos do TCU.

    Ordem das regras (seção 1 do plano_implementacao.md): entidades HTML,
    tags de citação (mantém só o texto interno), fechamento de parágrafo/
    célula/linha vira quebra dupla (separador de parágrafo, útil para o
    RecursiveCharacterTextSplitter), `<br>` vira quebra simples, demais tags
    somem, espaços/linhas em branco colapsam.
    """
    if not raw:
        return ""
    text = html.unescape(raw)
    text = _CITATION_TAG.sub(lambda m: m.group(2), text)
    text = _PARA_BREAK_TAG.sub("\n\n", text)
    text = _LINE_BREAK_TAG.sub("\n", text)
    text = _ANY_TAG.sub("", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MULTI_BLANK_LINE.sub("\n\n", text)
    return text.strip()


@dataclass
class GoldSpan:
    section: str
    start: int
    end: int


@dataclass
class CorpusDoc:
    doc_id: str
    text: str
    gold_spans: list[GoldSpan]
    ano: int
    colegiado: str
    tipo_processo: str


def assemble_document(row: dict) -> tuple[str, list[GoldSpan]]:
    """Concatena as colunas de seção normalizadas, registrando os spans ouro.

    Colunas vazias são puladas. Sem cabeçalho de seção injetado (seção 1):
    o texto final deve se parecer com um acórdão corrido de verdade.
    """
    parts: list[str] = []
    spans: list[GoldSpan] = []
    cursor = 0
    for column, section in SECTION_COLUMNS:
        chunk = normalize_html(row.get(column))
        if not chunk:
            continue
        if parts:
            parts.append("\n\n")
            cursor += 2
        start = cursor
        parts.append(chunk)
        cursor += len(chunk)
        spans.append(GoldSpan(section=section, start=start, end=cursor))
    return "".join(parts), spans


def _norm_num(value: str | None) -> str | None:
    """'358.0' / '358' -> '358'; vazio/inválido -> None."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return str(int(float(value)))
    except ValueError:
        return None


def _norm_colegiado(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().casefold()


def _join_key(num: str | None, ano: str | None, colegiado: str | None) -> tuple | None:
    n, a, c = _norm_num(num), _norm_num(ano), _norm_colegiado(colegiado)
    if n is None or a is None or c is None:
        return None
    return (n, a, c)


def load_tcu_acordaos(wanted_keys: set[tuple]) -> dict[tuple, CorpusDoc]:
    """Lê os CSVs anuais do TCU e monta um CorpusDoc só para as chaves em
    `wanted_keys` (as referenciadas pelo JurisTCU — ver build_corpus).

    Monta o texto (assemble_document, com todo o custo de regex de
    normalização) só para quem interessa: os CSVs anuais trazem TODOS os
    acórdãos do ano (~114k no total), mas o corpus final usa só os ~13k
    referenciados. Filtrar aqui evita normalizar os outros ~101k à toa.
    """
    by_key: dict[tuple, CorpusDoc] = {}
    years = [y for y in TCU_YEARS if (TCU_DIR / f"acordao-completo-{y}.csv").exists()]
    for i, ano in enumerate(years, start=1):
        path = TCU_DIR / f"acordao-completo-{ano}.csv"
        size = path.stat().st_size
        progress = Progress(f"TCU {ano} ({i}/{len(years)})", total=size)
        n_ano = 0
        # Dados abertos do TCU: predominantemente UTF-8, mas alguns anos têm
        # bytes isolados inválidos (herança de conversões antigas). Substitui
        # em vez de falhar — não afeta o restante do texto do documento.
        with path.open(encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f, delimiter="|")
            for row_num, row in enumerate(reader):
                if row_num % 2000 == 0:
                    progress.update(f.buffer.tell())
                if (row.get("TIPO") or "").strip().upper() != "ACÓRDÃO":
                    continue
                key = _join_key(row.get("NUMACORDAO"), row.get("ANOACORDAO"), row.get("COLEGIADO"))
                if key is None or key in by_key or key not in wanted_keys:
                    continue
                text, spans = assemble_document(row)
                if not text:
                    continue
                doc_id = f"{key[0]}-{key[1]}-{key[2].replace(' ', '_')}"
                by_key[key] = CorpusDoc(
                    doc_id=doc_id,
                    text=text,
                    gold_spans=spans,
                    ano=int(key[1]),
                    colegiado=(row.get("COLEGIADO") or "").strip(),
                    tipo_processo=(row.get("TIPOPROCESSO") or "").strip(),
                )
                n_ano += 1
        progress.done(f"{n_ano} acórdãos novos, total acumulado {len(by_key)}/{len(wanted_keys)}")
        if len(by_key) == len(wanted_keys):
            print("  Todas as chaves referenciadas já foram encontradas — parando cedo.", flush=True)
            break
    return by_key


def ensure_corpus_downloaded() -> None:
    missing = [p for p in (JURISTCU_DOCS, JURISTCU_QUERIES, JURISTCU_QRELS) if not p.exists()]
    if missing:
        nomes = ", ".join(p.name for p in missing)
        raise FileNotFoundError(
            f"Faltando em {JURISTCU_DIR}: {nomes}. Rode "
            "`python scripts/download_datasets.py juristcu` na raiz do "
            "repositório."
        )
    if not TCU_DIR.exists() or not any(TCU_DIR.glob("acordao-completo-*.csv")):
        raise FileNotFoundError(
            f"Nenhum CSV de acórdão encontrado em {TCU_DIR}. Rode "
            "`python scripts/download_datasets.py tcu_acordaos` na raiz do "
            "repositório."
        )


def build_corpus(out_dir: Path = INTERIM_DIR) -> dict:
    """Executa o join JurisTCU -> acórdãos TCU, monta o corpus e remapeia
    queries/qrels. Grava os artefatos de `out_dir` e retorna o relatório de
    join (também gravado em join_report.json)."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1ª leitura do doc.csv: só as chaves de junção (rápido, ~16k linhas).
    # Feito antes de abrir os CSVs do TCU para poder filtrar o parsing
    # pesado (assemble_document) só nos acórdãos que interessam.
    juristcu_rows: list[tuple[str, tuple | None]] = []
    referenced_keys: set[tuple] = set()
    with JURISTCU_DOCS.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = _join_key(row.get("NUMACORDAO"), row.get("ANOACORDAO"), row.get("COLEGIADO"))
            juristcu_rows.append((row["KEY"], key))
            if key is not None:
                referenced_keys.add(key)
    n_juristcu_docs = len(juristcu_rows)

    tcu_by_key = load_tcu_acordaos(referenced_keys)

    # doc_id do JurisTCU (KEY) -> doc_id do acórdão (via join).
    juristcu_key_to_acordao: dict[str, str] = {}
    n_matched = 0
    for juristcu_key, key in juristcu_rows:
        if key is not None and key in tcu_by_key:
            juristcu_key_to_acordao[juristcu_key] = tcu_by_key[key].doc_id
            n_matched += 1

    # Corpus final = interseção entre chaves referenciadas pelo JurisTCU e
    # acórdãos de fato encontrados nos CSVs do TCU (ver docstring de
    # load_tcu_acordaos) — não todo acórdão publicado no período. Os CSVs
    # anuais do TCU trazem todos os acórdãos do ano (~114k no total); usá-los
    # inteiros multiplicaria o custo de embedding/indexação por ~9x sem ganho
    # de realismo: a densidade de relevância nos ~13k referenciados já
    # reproduz a mesma proporção agulha-no-palheiro do JurisTCU original.
    corpus_docs = {d.doc_id: d for d in tcu_by_key.values()}

    # Queries: cópia direta.
    queries = []
    with JURISTCU_QUERIES.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            queries.append({"query_id": row["ID"], "text": row["TEXT"], "source": row["SOURCE"]})

    # Qrels: remapear DOC_ID (excerto) -> doc_id (acórdão); score = máximo
    # entre entradas que colidem no mesmo acórdão.
    qrel_scores: dict[tuple[str, str], int] = {}
    n_qrel_total = 0
    n_qrel_dropped = 0
    with JURISTCU_QRELS.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            n_qrel_total += 1
            acordao_id = juristcu_key_to_acordao.get(row["DOC_ID"])
            if acordao_id is None:
                n_qrel_dropped += 1
                continue
            k = (row["QUERY_ID"], acordao_id)
            score = int(float(row["SCORE"]))
            qrel_scores[k] = max(score, qrel_scores.get(k, score))

    # Gravar artefatos.
    with (out_dir / "corpus_docs.jsonl").open("w", encoding="utf-8") as f:
        for doc in corpus_docs.values():
            f.write(
                json.dumps(
                    {
                        "doc_id": doc.doc_id,
                        "text": doc.text,
                        "gold_spans": [s.__dict__ for s in doc.gold_spans],
                        "ano": doc.ano,
                        "colegiado": doc.colegiado,
                        "tipo_processo": doc.tipo_processo,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    with (out_dir / "queries.jsonl").open("w", encoding="utf-8") as f:
        for q in queries:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    with (out_dir / "qrels.trec").open("w", encoding="utf-8") as f:
        for (query_id, doc_id), score in sorted(qrel_scores.items()):
            f.write(f"{query_id} 0 {doc_id} {score}\n")

    report = {
        "n_juristcu_docs": n_juristcu_docs,
        "n_acordaos_referenciados": len(referenced_keys),
        "n_acordaos_encontrados": len(tcu_by_key),
        "n_docs_com_match": n_matched,
        "taxa_match_docs": round(n_matched / n_juristcu_docs, 4) if n_juristcu_docs else 0.0,
        "n_corpus_final": len(corpus_docs),
        "n_qrel_total": n_qrel_total,
        "n_qrel_preservados": n_qrel_total - n_qrel_dropped,
        "taxa_qrel_preservado": round((n_qrel_total - n_qrel_dropped) / n_qrel_total, 4)
        if n_qrel_total
        else 0.0,
        "n_qrel_pares_apos_colisao": len(qrel_scores),
    }
    with (out_dir / "join_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def check_gate(report: dict) -> None:
    """Gate residual (seção 0.5 do plano_implementacao.md): match e
    preservação de qrels devem ser >= 90%, senão parar."""
    if report["taxa_match_docs"] < 0.90:
        raise RuntimeError(
            f"Gate falhou: taxa de match de docs = {report['taxa_match_docs']:.1%} "
            "(< 90%). Ver join_report.json e considerar fallback para JurisTCU cru."
        )
    if report["taxa_qrel_preservado"] < 0.90:
        raise RuntimeError(
            f"Gate falhou: taxa de qrels preservados = {report['taxa_qrel_preservado']:.1%} "
            "(< 90%). Ver join_report.json e considerar fallback para JurisTCU cru."
        )


def corpus_stats(interim_dir: Path = INTERIM_DIR) -> dict:
    """Estatísticas do corpus final para o gate de viabilidade e EDA."""
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    token_counts = []
    section_presence = {s: 0 for _, s in SECTION_COLUMNS}
    n_docs = 0
    with (interim_dir / "corpus_docs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            n_docs += 1
            token_counts.append(len(enc.encode(doc["text"])))
            sections_in_doc = {s["section"] for s in doc["gold_spans"]}
            for s in sections_in_doc:
                section_presence[s] = section_presence.get(s, 0) + 1

    token_counts.sort()

    def pct(p: float) -> int:
        return token_counts[min(int(len(token_counts) * p), len(token_counts) - 1)]

    stats = {
        "n_docs": n_docs,
        "tokens_por_doc": {
            "mediana": pct(0.5),
            "p90": pct(0.90),
            "p99": pct(0.99),
            "media": round(statistics.mean(token_counts), 1) if token_counts else 0,
        },
        "presenca_secao": {
            s: round(c / n_docs, 4) if n_docs else 0.0 for s, c in section_presence.items()
        },
    }
    RESULTS_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    with (RESULTS_TABLES_DIR / "eda_stats.json").open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return stats


if __name__ == "__main__":
    ensure_corpus_downloaded()
    join_report = build_corpus()
    print("Relatório de join:", json.dumps(join_report, ensure_ascii=False, indent=2))
    check_gate(join_report)
    stats = corpus_stats()
    print("Estatísticas do corpus:", json.dumps(stats, ensure_ascii=False, indent=2))
    sys.exit(0)
