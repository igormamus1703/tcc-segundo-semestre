from src.retrieval import max_pooling, sum_top_k


def test_max_pooling_picks_best_chunk_per_doc():
    chunk_scores = [
        ("c1", "docA", 0.5),
        ("c2", "docA", 0.9),
        ("c3", "docB", 0.3),
    ]
    assert max_pooling(chunk_scores) == {"docA": 0.9, "docB": 0.3}


def test_sum_top_k_sums_best_k_scores_per_doc():
    chunk_scores = [
        ("c1", "docA", 0.5),
        ("c2", "docA", 0.9),
        ("c3", "docA", 0.1),
        ("c4", "docB", 0.3),
    ]
    result = sum_top_k(chunk_scores, k=2)
    assert result["docA"] == 0.5 + 0.9
    assert result["docB"] == 0.3
