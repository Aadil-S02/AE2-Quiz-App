import random

import pytest

from models import Question, QuestionBank
from quiz_score_and_progress import NoQuestionsAvailableError, QuizSession


def make_question(question_id, correct_index=0):
    return Question.create(
        question_id=question_id,
        category="Numeracy",
        text="What is 12 squared?",
        options=["144", "124", "132", "164"],
        correct_index=correct_index,
    )


def test_start_raises_when_category_has_no_questions():
    bank = QuestionBank([])
    with pytest.raises(NoQuestionsAvailableError):
        QuizSession.start(bank, "Ada", "Numeracy", num_questions=3)


def test_full_session_scores_correctly():
    questions = [make_question("q1", 0), make_question("q2", 0)]
    session = QuizSession(questions, candidate_name="Ada", category="Numeracy")

    assert session.current_question_number == 1
    assert session.submit_answer(0) is True  # correct
    assert session.submit_answer(1) is False  # incorrect
    assert session.is_finished() is True

    result = session.build_result()
    assert result.score == 1
    assert result.total == 2
    assert result.candidate_name == "Ada"


def test_current_question_raises_after_quiz_finished():
    session = QuizSession([make_question("q1", 0)], candidate_name="Ada", category="Numeracy")
    session.submit_answer(0)
    with pytest.raises(IndexError):
        session.current_question()


def test_build_result_raises_before_quiz_finished():
    session = QuizSession(
        [make_question("q1", 0), make_question("q2", 0)],
        candidate_name="Ada",
        category="Numeracy",
    )
    session.submit_answer(0)
    with pytest.raises(RuntimeError):
        session.build_result()


def test_start_samples_from_bank_reproducibly_with_seeded_rng():
    bank = QuestionBank([make_question(f"q{i}") for i in range(5)])
    session = QuizSession.start(
        bank, "Ada", "Numeracy", num_questions=3, rng=random.Random(1)
    )
    assert session.total_questions == 3


def test_review_records_every_answer():
    session = QuizSession(
        [make_question("q1", 0), make_question("q2", 0)],
        candidate_name="Ada",
        category="Numeracy",
    )
    session.submit_answer(0)
    session.submit_answer(2)

    review = session.review()

    assert len(review) == 2
    assert review[0].was_correct is True
    assert review[1].was_correct is False