from src.pipeline import split_90_10, train_and_evaluate


def test_split_is_90_10_and_disjoint():
    rows = [{"text": f"comment {i}", "label": "toxic" if i % 4 == 0 else "non_toxic"}
            for i in range(100)]
    train, val = split_90_10(rows, seed=1)
    assert len(train) == 90
    assert len(val) == 10
    assert {r["text"] for r in train}.isdisjoint({r["text"] for r in val})


def test_split_is_deterministic():
    rows = [{"text": f"row {i}", "label": "non_toxic"} for i in range(50)]
    assert split_90_10(rows, seed=7) == split_90_10(rows, seed=7)


def test_linear_probe_runs():
    train = [
        {"text": "this is a friendly and kind comment", "label": "non_toxic"},
        {"text": "you are stupid and I hate you", "label": "toxic"},
        {"text": "thanks for the helpful explanation", "label": "non_toxic"},
        {"text": "shut up idiot nobody likes you", "label": "toxic"},
    ]
    val = [
        {"text": "that was a nice helpful answer", "label": "non_toxic"},
        {"text": "you are an idiot", "label": "toxic"},
    ]
    result = train_and_evaluate(train, val)
    assert result["train_rows"] == 4
    assert result["val_rows"] == 2
    assert 0.0 <= result["accuracy"] <= 1.0
    assert result["coef_shape"][0] == 1


def test_real_data_slice_runs_with_small_limit():
    from src.pipeline import run_reproduction_slice

    out = run_reproduction_slice(limit=200)
    assert out["status"] == "partial_reproduction_slice"
    assert out["rows_loaded"] == 200
    assert out["split"]["train_rows"] == 180
    assert out["split"]["val_rows"] == 20
