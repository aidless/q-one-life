def test_pb_hidden_modal():
    from src.core import run
    assert run({"datasets": {"answers": ["1", "1", "2"]}})["chosen"] == "1"

def test_pb_hidden_parse():
    from src.core import parse_answer
    assert parse_answer("The answer is 19.") == "19"
