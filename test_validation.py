import pytest

from validation import (
    validate_candidate_name,
    validate_category,
    validate_correct_index,
    validate_non_empty_text,
    validate_options,
    validate_question_data,
)


def test_validate_non_empty_text_strips_whitespace():
    assert validate_non_empty_text("  hello  ", "Field") == "hello"


@pytest.mark.parametrize("value", ["", "   ", None, 123])
def test_validate_non_empty_text_rejects_invalid(value):
    with pytest.raises(ValueError):
        validate_non_empty_text(value, "Field")


def test_validate_category_is_case_insensitive_and_returns_canonical():
    assert validate_category("health & safety", ["Health & Safety"]) == "Health & Safety"


def test_validate_category_rejects_unknown_category():
    with pytest.raises(ValueError):
        validate_category("Not A Category", ["Health & Safety"])


def test_validate_options_accepts_valid_list():
    options = ["A", "B", "C", "D"]
    assert validate_options(options) == options


def test_validate_options_rejects_too_few():
    with pytest.raises(ValueError):
        validate_options(["Only one"])


def test_validate_options_rejects_duplicates_case_insensitive():
    with pytest.raises(ValueError):
        validate_options(["Yes", "No", "yes"])


def test_validate_correct_index_accepts_valid_index():
    assert validate_correct_index(1, ["A", "B", "C"]) == 1


@pytest.mark.parametrize("index", [-1, 3, "1", True])
def test_validate_correct_index_rejects_invalid(index):
    with pytest.raises(ValueError):
        validate_correct_index(index, ["A", "B", "C"])


def test_validate_question_data_returns_cleaned_dict():
    result = validate_question_data(
        category=" numeracy ",
        text="  What is 12 squared?  ",
        options=["144", "124", "132", "164"],
        correct_index=0,
        allowed_categories=["Numeracy"],
    )
    assert result == {
        "category": "Numeracy",
        "text": "What is 12 squared?",
        "options": ["144", "124", "132", "164"],
        "correct_index": 0,
    }


def test_validate_candidate_name_rejects_overly_long_name():
    with pytest.raises(ValueError):
        validate_candidate_name("x" * 101)


def test_validate_candidate_name_is_deterministic():
    assert validate_candidate_name("Ada Lovelace") == validate_candidate_name("Ada Lovelace")