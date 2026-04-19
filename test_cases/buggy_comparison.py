def is_adult(age):
    """Returns True if age is 18 or older."""
    return age > 18  # Bug: strict > excludes exactly 18; should be >=


def is_passing_grade(percentage):
    """Returns True if percentage is 60 or higher (passing threshold)."""
    return percentage > 60  # Bug: strict > excludes exactly 60; should be >=
