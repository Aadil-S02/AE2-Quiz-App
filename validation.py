"""Pure validation functions for quiz data.

Every function here is deterministic: given the same arguments it always
returns the same result and never touches the filesystem, the GUI, or any
other outside state. That makes them trivial to unit test and safe to reuse
anywhere in the app (form validation, CSV import, quiz engine, etc).

All validators raise ``ValueError`` on invalid input with a message describing
what was wrong, rather than returning a bool. This keeps calling code simple:
either validation succeeds and execution continues, or it raises and the
caller (GUI or CSV loader) decides how to present that to the user.
"""

from __future__ import annotations

MIN_OPTIONS = 2
MAX_OPTIONS = 5

def validate_non_empty_text(value: str, field_name: str) -> str:
    """Return ``value`` stripped of surrounding whitespace.

    Raises ValueError if ``value`` is not a string, or is empty/whitespace-only.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


def validate_category(category: str, allowed_categories: list[str]) -> str:
    """Return ``category`` if it is one of ``allowed_categories`` (case-insensitive).

    Returns the canonical (correctly-cased) category name from
    ``allowed_categories`` rather than whatever casing the caller supplied.
    """
    cleaned = validate_non_empty_text(category, "Category")
    for allowed in allowed_categories:
        if cleaned.lower() == allowed.lower():
            return allowed
    raise ValueError(
        f"'{cleaned}' is not a recognised category. "
        f"Choose one of: {', '.join(allowed_categories)}."
    )


def validate_options(options: list[str]) -> list[str]:
    """Validate a list of answer options for a multiple-choice question.

    Requires between MIN_OPTIONS and MAX_OPTIONS options, each non-empty,
    with no duplicates (case-insensitive). Returns the cleaned (stripped)
    list of options in their original order.
    """
    if not isinstance(options, list):
        raise ValueError("Options must be provided as a list.")
    if not (MIN_OPTIONS <= len(options) <= MAX_OPTIONS):
        raise ValueError(
            f"A question must have between {MIN_OPTIONS} and {MAX_OPTIONS} options "
            f"(got {len(options)})."
        )

    cleaned = [validate_non_empty_text(option, "Option") for option in options]

    seen_lowercase = set()
    for option in cleaned:
        key = option.lower()
        if key in seen_lowercase:
            raise ValueError(f"Duplicate option found: '{option}'.")
        seen_lowercase.add(key)

    return cleaned


def validate_correct_index(correct_index: int, options: list[str]) -> int:
    """Validate that ``correct_index`` is a valid position within ``options``."""
    if isinstance(correct_index, bool) or not isinstance(correct_index, int):
        raise ValueError("Correct answer index must be a whole number.")
    if not (0 <= correct_index < len(options)):
        raise ValueError(
            f"Correct answer index must be between 0 and {len(options) - 1} "
            f"(got {correct_index})."
        )
    return correct_index


def validate_question_data(
    category: str,
    text: str,
    options: list[str],
    correct_index: int,
    allowed_categories: list[str],
) -> dict:
    """Validate a full set of question fields together.

    Returns a dict of cleaned values: {category, text, options, correct_index}.
    Raises ValueError describing the first problem found.
    """
    cleaned_category = validate_category(category, allowed_categories)
    cleaned_text = validate_non_empty_text(text, "Question text")
    cleaned_options = validate_options(options)
    cleaned_correct_index = validate_correct_index(correct_index, cleaned_options)

    return {
        "category": cleaned_category,
        "text": cleaned_text,
        "options": cleaned_options,
        "correct_index": cleaned_correct_index,
    }


def validate_candidate_name(name: str) -> str:
    """Validate the name a quiz-taker enters before starting a quiz."""
    cleaned = validate_non_empty_text(name, "Name")
    if len(cleaned) > 100:
        raise ValueError("Name is too long (100 characters maximum).")
    return cleaned
