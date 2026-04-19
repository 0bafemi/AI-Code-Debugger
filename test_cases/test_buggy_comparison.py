from solution import is_adult, is_passing_grade


def test_adult_at_exactly_18():
    assert is_adult(18) is True


def test_adult_below_18():
    assert is_adult(17) is False


def test_adult_above_18():
    assert is_adult(21) is True


def test_passing_grade_at_boundary():
    assert is_passing_grade(60) is True


def test_passing_grade_below():
    assert is_passing_grade(59) is False


def test_passing_grade_above():
    assert is_passing_grade(75) is True
