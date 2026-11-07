from src.core import summarize_rubric, run


def test_summary():
    s = summarize_rubric()
    assert s["paper_id"] == 'rice'
    assert s["rubric_leaves"] == 361
    assert s["categories"]


def test_run():
    assert run({"datasets": {"items": [1, 2, 3]}})["count"] == 3


def test_status_is_honest():
    assert run({"datasets": {"items": []}})["status"] == "architecture_stub"
