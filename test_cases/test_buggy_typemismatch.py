from solution import format_score, stringify_list


def test_format_score_int():
    assert format_score(85) == "85%"


def test_format_score_zero():
    assert format_score(0) == "0%"


def test_stringify_list_basic():
    assert stringify_list([1, 2, 3]) == "1, 2, 3"


def test_stringify_list_single():
    assert stringify_list([42]) == "42"
