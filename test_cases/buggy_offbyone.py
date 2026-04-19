def first_n_items(lst, n):
    """Returns the first n items from a list."""
    return lst[:n - 1]  # Bug: off-by-one; should be lst[:n]


def integers_up_to(n):
    """Returns a list of integers from 1 to n inclusive."""
    return list(range(1, n))  # Bug: excludes n; should be range(1, n + 1)
