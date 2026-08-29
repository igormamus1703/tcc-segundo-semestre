import pytest

from src.tokenization import count_tokens, token_windows


def test_count_tokens_matches_encoding_length():
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    text = "Acórdão do Tribunal de Contas da União, com acentuação e cedilha: ção, ã, é."
    assert count_tokens(text) == len(enc.encode(text))


def test_token_windows_empty_text_returns_no_windows():
    assert token_windows("", 10, 5) == []


def test_token_windows_rejects_invalid_stride():
    with pytest.raises(ValueError):
        token_windows("algum texto", 10, 0)
    with pytest.raises(ValueError):
        token_windows("algum texto", 10, 11)


def test_token_windows_covers_whole_text_without_gaps():
    text = " ".join(f"palavra{i}" for i in range(300))
    windows = token_windows(text, size=20, stride=10)

    assert windows[0][0] == 0
    assert windows[-1][1] == len(text)
    for (_, end), (next_start, _) in zip(windows, windows[1:]):
        assert next_start <= end  # sem buraco entre janelas consecutivas


def test_token_windows_respects_size_and_stride_in_token_count():
    text = " ".join(f"palavra{i}" for i in range(300))
    windows = token_windows(text, size=20, stride=10)

    for start, end in windows[:-1]:  # a última pode ser parcial
        assert count_tokens(text[start:end]) == 20


def test_token_windows_includes_final_partial_window():
    text = "um texto curto"
    assert count_tokens(text) < 20  # garante que cabe numa janela só
    windows = token_windows(text, size=20, stride=10)

    assert len(windows) == 1
    assert windows[0] == (0, len(text))


def test_token_windows_handles_dense_accented_text_without_drift():
    # muitos acentos em sequência, para forçar limites de token colados a
    # fronteiras de caractere multi-byte em UTF-8 (risco listado na seção 5
    # do plano_implementacao.md).
    text = "ação " * 200 + "ção não pão coração"
    windows = token_windows(text, size=15, stride=7)

    assert windows[0][0] == 0
    assert windows[-1][1] == len(text)
    for start, end in windows[:-1]:
        # arredondar o limite de byte para o caractere mais próximo pode
        # deslocar a contagem por no máximo ~1 token, nunca mais que isso.
        assert abs(count_tokens(text[start:end]) - 15) <= 1
