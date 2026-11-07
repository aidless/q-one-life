def test_host_hidden_modal_and_parse():
    from src.core import run, parse_answer
    assert parse_answer("Reasoning.\nThe answer is (19).") == "19"
    assert parse_answer("No answer") is None
    assert run({"datasets": {"answers": ["a", "a", "b"], "responses": []}})["chosen"] == "a"

def test_host_hidden_methods_return_answers():
    from src.core import cpw_answer, scw_answer
    responses = [
        "The answer is x", "The answer is x", "The answer is x",
        "The answer is y", "The answer is y",
    ]
    assert cpw_answer(responses) in ("x", "y")
    assert scw_answer(responses) in ("x", "y")
