def format_score(score):
    """Returns score formatted as a percentage string, e.g. 85 -> '85%'."""
    return score + "%"  # Bug: int + str raises TypeError; should be str(score) + "%"


def stringify_list(numbers):
    """Returns a comma-separated string of integers, e.g. [1, 2, 3] -> '1, 2, 3'."""
    return ", ".join(numbers)  # Bug: join requires strings; should be str(n) for n in numbers
