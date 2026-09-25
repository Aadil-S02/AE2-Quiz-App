"""Quiz session logic, independent of any GUI.

QuizSession drives one attempt at a quiz: it holds the selected questions,
tracks the candidate's answers, and produces a final QuizResult. Keeping
this separate from Tkinter means the whole flow of "answer questions, get
scored" can be unit tested without opening a single window.
"""

from __future__ import annotations

from dataclasses import dataclass

from models import Question, QuestionBank, QuizResult


class NoQuestionsAvailableError(Exception):
    """Raised when a quiz is started for a category with no questions."""


@dataclass
class AnsweredQuestion:
    """A record of how the candidate answered one question in the session."""

    question: Question
    selected_index: int

    @property
    def was_correct(self) -> bool:
        return self.question.is_correct(self.selected_index)


class QuizSession:
    """Tracks progress through one quiz attempt from start to finish."""

    def __init__(self, questions: list[Question], candidate_name: str, category: str):
        if not questions:
            raise NoQuestionsAvailableError(
                f"No questions are available for category '{category}'."
            )
        self.questions = questions
        self.candidate_name = candidate_name
        self.category = category
        self._current_index = 0
        self._answers: list[AnsweredQuestion] = []

    @classmethod
    def start(
        cls,
        bank: QuestionBank,
        candidate_name: str,
        category: str,
        num_questions: int,
        rng=None,
    ) -> "QuizSession":
        """Build a session by sampling questions from ``bank`` for ``category``.

        Raises NoQuestionsAvailableError if the category has zero questions.
        """
        questions = bank.sample(category, num_questions, rng=rng)
        return cls(questions, candidate_name, category)

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    @property
    def current_question_number(self) -> int:
        """1-based number of the question currently being answered."""
        return self._current_index + 1

    def current_question(self) -> Question:
        """The question the candidate should answer next.

        Raises IndexError if the quiz has already finished.
        """
        if self.is_finished():
            raise IndexError("The quiz has already finished; there is no current question.")
        return self.questions[self._current_index]

    def submit_answer(self, selected_index: int) -> bool:
        """Record the candidate's answer to the current question and advance.

        Returns True if the answer was correct. Raises IndexError if the
        quiz has already finished.
        """
        question = self.current_question()
        self._answers.append(AnsweredQuestion(question=question, selected_index=selected_index))
        self._current_index += 1
        return question.is_correct(selected_index)

    def is_finished(self) -> bool:
        """True once every question has been answered."""
        return self._current_index >= len(self.questions)

    def score(self) -> int:
        """Number of questions answered correctly so far."""
        return sum(1 for answer in self._answers if answer.was_correct)

    def build_result(self) -> QuizResult:
        """Produce a QuizResult summarising this attempt.

        Raises RuntimeError if the quiz has not been fully completed yet,
        since a partial result would be misleading to persist.
        """
        if not self.is_finished():
            raise RuntimeError("Cannot build a result before the quiz is finished.")
        return QuizResult(
            candidate_name=self.candidate_name,
            category=self.category,
            score=self.score(),
            total=self.total_questions,
        )

    def review(self) -> list[AnsweredQuestion]:
        """Return every answered question, for a post-quiz review screen."""
        return list(self._answers)