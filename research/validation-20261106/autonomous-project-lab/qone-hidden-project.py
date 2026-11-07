def test_host_hidden_median():
    from src.core import run
    assert run({"datasets": {"x": [1, 3, 5]}})["median"] == 3

def test_host_hidden_even():
    from src.core import run
    assert run({"datasets": {"x": [1, 3, 5, 7]}})["median"] == 4
