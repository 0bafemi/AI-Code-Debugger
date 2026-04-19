def update_score(current_score, outcome, attempt_number):
    """
    Update game score based on guess outcome.
    Win: add max(100 - 10 * attempt_number, 10) points.
    Wrong guess: subtract 5 points.
    """
    if outcome == "Win":
        return current_score + max(100 - 10 * attempt_number, 10)
    else:
        return current_score + 5  # Bug: wrong guesses should subtract 5, not add 5
