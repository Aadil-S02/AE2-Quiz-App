import random

from models import Question, QuestionBank, QuizResult


def test_quiz_result_percentage():
    result = QuizResult(candidate_name="Ada", category="Numeracy", score=3, total=4)
    assert result.percentage == 75.0


def test_quiz_result_percentage_handles_zero_total():
    result = QuizResult(candidate_name="Ada", category="Numeracy", score=0, total=0)
    assert result.percentage == 0.0


def test_quiz_result_round_trips_through_row():
    result = QuizResult(candidate_name="Ada", category="Numeracy", score=2, total=5)
    row = result.to_row()
    rebuilt = QuizResult.from_row(row)
    assert rebuilt.candidate_name == result.candidate_name
    assert rebuilt.score == result.score
    assert rebuilt.total == result.total

def make_question(question_id="q1", category="Numeracy", correct_index=0):
    return Question.create(
        question_id=question_id,
        category=category,
        text="What is 12 squared?",
        options=["144", "124", "132", "164"],
        correct_index=correct_index,
    )


def test_question_bank_by_category_filters_correctly():
    bank = QuestionBank([
        make_question("q1", category="Numeracy"),
        make_question("q2", category="Health & Safety"),
    ])
    assert [q.question_id for q in bank.by_category("Numeracy")] == ["q1"]


def test_question_bank_by_category_all_returns_everything():
    bank = QuestionBank([make_question("q1"), make_question("q2")])
    assert len(bank.by_category("All")) == 2


def test_question_bank_sample_never_exceeds_available_questions():
    bank = QuestionBank([make_question("q1"), make_question("q2")])
    sampled = bank.sample("Numeracy", count=10, rng=random.Random(0))
    assert len(sampled) == 2


def test_question_bank_sample_is_reproducible_with_seeded_rng():
    bank = QuestionBank([make_question(f"q{i}") for i in range(5)])
    first = bank.sample("Numeracy", count=3, rng=random.Random(42))
    second = bank.sample("Numeracy", count=3, rng=random.Random(42))
    assert [q.question_id for q in first] == [q.question_id for q in second]


def test_question_bank_remove():
    bank = QuestionBank([make_question("q1"), make_question("q2")])
    bank.remove("q1")
    assert [q.question_id for q in bank.all()] == ["q2"]