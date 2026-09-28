import json
import re
from datetime import datetime

import pytest

from src.experiment import Experimento, timestamp_slug


def test_timestamp_slug_ordenavel_e_sem_caractere_proibido():
    """A data vem primeiro para que a ordem alfabética seja a cronológica, e
    sem ':' porque o Windows recusa em nome de pasta."""
    slug = timestamp_slug(datetime(2026, 9, 6, 14, 35))
    assert slug == "20260906-1435"
    assert re.fullmatch(r"\d{8}-\d{4}", slug)
    assert timestamp_slug(datetime(2026, 1, 2, 3, 4)) < slug


def test_experimento_cria_estrutura_e_manifesto(tmp_path):
    with Experimento("bm25", config={"retrievers": ["bm25"]}, raiz=tmp_path) as exp:
        exp.registrar("fixed_512_256__bm25", {"n_chunks": 907914, "segundos": 426.7})

    assert exp.runs_dir.is_dir()
    assert exp.tables_dir.is_dir()
    assert exp.log_path.is_file()

    m = json.loads((exp.dir / "manifest.json").read_text(encoding="utf-8"))
    assert m["rotulo"] == "bm25"
    assert m["config"]["retrievers"] == ["bm25"]
    assert m["etapas"][0]["n_chunks"] == 907914
    assert m["fim"] is not None
    assert m["erro"] is None
    # o que torna a rodada reproduzível
    assert "commit" in m["git"]
    assert m["versoes"]["python"]
    assert "so" in m["hardware"]
    assert m["comando"]


def test_experimento_registra_a_falha_no_manifesto(tmp_path):
    """Rodada que quebrou no meio precisa ficar marcada — senão vira um
    resultado parcial indistinguível de um completo."""
    with pytest.raises(RuntimeError):
        with Experimento("quebrado", raiz=tmp_path) as exp:
            raise RuntimeError("estourou")

    m = json.loads((exp.dir / "manifest.json").read_text(encoding="utf-8"))
    assert "RuntimeError: estourou" in m["erro"]


def test_indice_lista_as_rodadas(tmp_path, monkeypatch):
    import src.experiment as ex

    monkeypatch.setattr(ex, "EXPERIMENTS_DIR", tmp_path)
    with ex.Experimento("primeira", raiz=tmp_path):
        pass
    with ex.Experimento("segunda", raiz=tmp_path):
        pass

    indice = (tmp_path / "INDICE.md").read_text(encoding="utf-8")
    assert "primeira" in indice and "segunda" in indice
    assert "não editar" in indice.lower()


def test_log_tem_horario(tmp_path):
    with Experimento("x", raiz=tmp_path) as exp:
        exp.log("mensagem de teste", echo=False)
    conteudo = exp.log_path.read_text(encoding="utf-8")
    assert "mensagem de teste" in conteudo
    assert re.search(r"\[\d{2}:\d{2}:\d{2}\]", conteudo)


# --- localizar a rodada mais recente (encadeamento de etapas) ---------------

def _rodada(base, nome, com_runs=True):
    d = base / nome
    (d / "runs").mkdir(parents=True)
    if com_runs:
        (d / "runs" / "x__bm25.trec").write_text("1 Q0 d 1 1.0 x\n", encoding="utf-8")
    return d


def test_ultima_rodada_pega_a_mais_recente_do_rotulo(tmp_path):
    from src.experiment import ultima_rodada

    _rodada(tmp_path, "20260101-1000_bm25")
    esperada = _rodada(tmp_path, "20260201-1000_bm25")
    _rodada(tmp_path, "20260301-1000_dense_bge_m3")
    assert ultima_rodada("bm25", raiz=tmp_path) == esperada


def test_ultima_rodada_nao_casa_rodada_derivada(tmp_path):
    """BUG REAL (28/09): com casamento por substring, 'bm25' pegava
    'cv_fusao_bm25_denso' e 'dense' pegava 'dense_peso_rel0.5'. O script
    encadearia a F6 a partir de uma rodada derivada, e o erro so apareceria
    como um numero estranho na tabela final."""
    from src.experiment import ultima_rodada

    base = _rodada(tmp_path, "20260101-1000_bm25")
    _rodada(tmp_path, "20260301-1000_cv_fusao_bm25_denso")
    _rodada(tmp_path, "20260301-1100_bm25_sec_sem_relatorio")
    assert ultima_rodada("bm25", raiz=tmp_path) == base

    denso = _rodada(tmp_path, "20260102-1000_dense_bge_m3")
    _rodada(tmp_path, "20260302-1000_dense_peso_rel0.5")
    assert ultima_rodada("dense_bge_m3", raiz=tmp_path) == denso


def test_ultima_rodada_aceita_substring_quando_pedido(tmp_path):
    from src.experiment import ultima_rodada

    _rodada(tmp_path, "20260101-1000_bm25")
    derivada = _rodada(tmp_path, "20260301-1000_cv_fusao_bm25_denso")
    assert ultima_rodada("bm25", raiz=tmp_path, exato=False) == derivada


def test_ultima_rodada_ignora_rodada_sem_runs(tmp_path):
    """Uma rodada que abortou antes de gravar qualquer .trec nao serve de
    entrada para a etapa seguinte; devolve-la faria o erro aparecer duas
    etapas adiante."""
    from src.experiment import ultima_rodada

    boa = _rodada(tmp_path, "20260101-1000_bm25")
    _rodada(tmp_path, "20260201-1000_bm25", com_runs=False)
    assert ultima_rodada("bm25", raiz=tmp_path) == boa


def test_ultima_rodada_sem_casar_devolve_none(tmp_path):
    from src.experiment import ultima_rodada

    _rodada(tmp_path, "20260101-1000_bm25")
    assert ultima_rodada("inexistente", raiz=tmp_path) is None
