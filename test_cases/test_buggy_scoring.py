from solution import update_score


def test_wrong_guess_subtracts_points():
    assert update_score(100, "Too High", 1) == 95


def test_multiple_wrong_guesses():
    score = update_score(100, "Too Low", 1)
    score = update_score(score, "Too High", 2)
    assert score == 90


def test_win_first_attempt():
    assert update_score(0, "Win", 1) == 90  # 100 - 10*1 = 90


def test_win_enforces_minimum():
    assert update_score(0, "Win", 15) == 10  # min 10 points
