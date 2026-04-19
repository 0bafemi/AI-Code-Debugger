from solution import first_n_items, integers_up_to


def test_first_n_items_correct_count():
    assert first_n_items([10, 20, 30, 40, 50], 3) == [10, 20, 30]


def test_first_n_items_single():
    assert first_n_items([1, 2, 3], 1) == [1]


def test_integers_up_to_includes_n():
    assert integers_up_to(5) == [1, 2, 3, 4, 5]


def test_integers_up_to_one():
    assert integers_up_to(1) == [1]
