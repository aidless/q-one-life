from src.lca import (
    lca_alignment_loss,
    one_hot,
    run_algorithm_slice,
    softmax,
    toy_tree,
)


def test_lca_and_depth():
    tree = toy_tree()
    assert tree.lca("dog", "cat") == "animal"
    assert tree.lca("dog", "car") == "root"
    assert tree.depth("dog") == 2
    assert tree.depth("root") == 0


def test_information_content_and_distance():
    tree = toy_tree()
    assert tree.information_content("root") == 0.0
    assert tree.information_content("animal") > 0.0
    assert tree.distance_information("dog", "cat") > 0.0
    assert tree.distance_depth("dog", "cat") == 2.0
    assert tree.distance_depth("dog", "car") == 4.0


def test_distance_matrix_symmetric_zero_diagonal():
    tree = toy_tree()
    info = tree.distance_matrix("information")
    depth = tree.distance_matrix("depth")
    n = len(info)
    assert n == 4
    assert all(abs(info[i][j] - info[j][i]) < 1e-12
               for i in range(n) for j in range(n))
    assert all(depth[i][i] == 0.0 for i in range(n))


def test_softmax_and_one_hot():
    probs = softmax([[1.0, 1.0]])
    assert abs(sum(probs[0]) - 1.0) < 1e-12
    assert one_hot([1], 3) == [[0.0, 1.0, 0.0]]


def test_alignment_loss_modes_and_bad_mode():
    tree = toy_tree()
    matrix = tree.distance_matrix("information")
    logits = [[2.0, 0.0, 0.0, 0.0]]
    ce = lca_alignment_loss(logits, [0], matrix, "CE")
    bce = lca_alignment_loss(logits, [0], matrix, "BCE")
    assert ce > 0.0 and bce > 0.0
    try:
        lca_alignment_loss(logits, [0], matrix, "INVALID")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid alignment_mode must raise")


def test_algorithm_slice_runs():
    out = run_algorithm_slice()
    assert out["status"] == "algorithm_slice"
    assert out["lca_dog_cat"] == "animal"
    assert out["alignment_loss_ce"] > 0.0
