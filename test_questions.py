import pytest

from models import Question


def make_question(question_id="q1", category="Numeracy", correct_index=0):
    return Question.create(
        question_id=question_id,
        category=category,
        text="What is 12 squared?",
        options=["144", "124", "132", "164"],
        correct_index=correct_index,
    )


def test_question_create_rejects_invalid_data():
    with pytest.raises(ValueError):
        Question.create(
            question_id="q1",
            category="Not A Real Category",
            text="Text",
            options=["A", "B"],
            correct_index=0,
        )


def test_question_is_correct():
    question = make_question(correct_index=0)
    assert question.is_correct(0) is True
    assert question.is_correct(1) is False


def test_question_round_trips_through_row():
    question = make_question()
    row = question.to_row()
    rebuilt = Question.from_row(row)
    assert rebuilt == question