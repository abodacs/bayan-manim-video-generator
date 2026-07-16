from scripts.check_python_comments import find_comment_violations


def test_english_comments_are_allowed() -> None:
    assert find_comment_violations("# Reshape the Arabic text") == []


def test_non_english_alphabetic_characters_are_rejected() -> None:
    violations = find_comment_violations("# مرحبا بالعالم")

    assert len(violations) == 1
    assert violations[0].line == 1
    assert violations[0].column == 0
    assert violations[0].letters == ("م", "ر", "ح", "ب", "ا", "ل", "ع")


def test_arabic_strings_are_allowed() -> None:
    source = 'message = "مرحبا بالعالم"  # English comment'

    assert find_comment_violations(source) == []
