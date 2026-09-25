"""Domain model classes for the onboarding quiz.

These classes represent the core concepts of the app (a question, a
completed quiz result, and a bank of questions) and know nothing about
Tkinter or CSV files. Keeping them independent of the GUI and storage layers
makes them easy to unit test.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from datetime import datetime

import random

from validation import validate_question_data


CATEGORIES = [
    "Company Policies",
    "Health & Safety",
    "Data Protection",
    "Workplace Ethics",
    "Numeracy",
]


@dataclass
class Question:
    """A single multiple-choice question.

    Attributes:
        question_id: Unique identifier (stable across saves/loads).
        category: One of the values in CATEGORIES.
        text: The question prompt shown to the user.
        options: The list of possible answers.
        correct_index: Index into ``options`` of the correct answer.
    """

    question_id: str
    category: str
    text: str
    options: list[str]
    correct_index: int

    @classmethod
    def create(
        cls,
        question_id: str,
        category: str,
        text: str,
        options: list[str],
        correct_index: int,
        allowed_categories: list[str] | None = None,
    ) -> "Question":
        """Validate inputs and construct a Question.

        This is the preferred way to build a Question from user-supplied or
        CSV-sourced data, since it runs full validation first. Raises
        ValueError if any field is invalid.
        """
        cleaned = validate_question_data(
            category=category,
            text=text,
            options=options,
            correct_index=correct_index,
            allowed_categories=allowed_categories or CATEGORIES,
        )
        return cls(
            question_id=question_id,
            category=cleaned["category"],
            text=cleaned["text"],
            options=cleaned["options"],
            correct_index=cleaned["correct_index"],
        )

    @property
    def correct_answer(self) -> str:
        """The text of the correct option."""
        return self.options[self.correct_index]

    def is_correct(self, selected_index: int) -> bool:
        """Return True if ``selected_index`` matches the correct answer."""
        return selected_index == self.correct_index

    def to_row(self) -> dict:
        """Convert to a flat dict suitable for writing to a CSV row.

        Options are joined with '|' since CSV columns cannot hold a list
        directly, and a plain comma would clash with the CSV delimiter and
        with commas that might appear inside an option's text.
        """
        return {
            "question_id": self.question_id,
            "category": self.category,
            "text": self.text,
            "options": "|".join(self.options),
            "correct_index": str(self.correct_index),
        }

    @classmethod
    def from_row(cls, row: dict) -> "Question":
        """Build a Question from a CSV row dict, validating its contents.

        Raises ValueError (via Question.create) if the row's data is invalid,
        or KeyError if a required column is missing.
        """
        options = row["options"].split("|")
        correct_index = int(row["correct_index"])
        return cls.create(
            question_id=row["question_id"],
            category=row["category"],
            text=row["text"],
            options=options,
            correct_index=correct_index,
        )

@dataclass
class QuizResult:
    """A record of one completed quiz attempt, ready for persistence.

    Attributes:
        candidate_name: Name entered by the person taking the quiz.
        category: The category quizzed on (or "All").
        score: Number of questions answered correctly.
        total: Total number of questions asked.
        timestamp: When the attempt was completed.
    """

    candidate_name: str
    category: str
    score: int
    total: int
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def percentage(self) -> float:
        """Score as a percentage of total, or 0.0 if total is 0."""
        if self.total == 0:
            return 0.0
        return round((self.score / self.total) * 100, 1)

    def to_row(self) -> dict:
        """Convert to a flat dict suitable for writing to a CSV row."""
        return {
            "candidate_name": self.candidate_name,
            "category": self.category,
            "score": str(self.score),
            "total": str(self.total),
            "percentage": str(self.percentage),
            "timestamp": self.timestamp.isoformat(timespec="seconds"),
        }

    @classmethod
    def from_row(cls, row: dict) -> "QuizResult":
        """Build a QuizResult from a CSV row dict."""
        return cls(
            candidate_name=row["candidate_name"],
            category=row["category"],
            score=int(row["score"]),
            total=int(row["total"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )
class QuestionBank:
    """An in-memory collection of Question objects with lookup helpers.

    This wraps a plain list so callers get convenience methods (filter by
    category, pick a random sample) without needing to know the underlying
    storage format. It does not read or write files itself - see
    storage.py for that.
    """

    def __init__(self, questions: list[Question] | None = None):
        self._questions: list[Question] = list(questions) if questions else []

    def __len__(self) -> int:
        return len(self._questions)

    def all(self) -> list[Question]:
        """Return every question in the bank."""
        return list(self._questions)

    def add(self, question: Question) -> None:
        """Add a question to the bank."""
        self._questions.append(question)

    def remove(self, question_id: str) -> None:
        """Remove the question with the given id, if present."""
        self._questions = [q for q in self._questions if q.question_id != question_id]

    def categories_present(self) -> list[str]:
        """Return the distinct categories currently in the bank, in CATEGORIES order."""
        present = {q.category for q in self._questions}
        return [c for c in CATEGORIES if c in present]

    def by_category(self, category: str) -> list[Question]:
        """Return all questions in the given category (empty list if none)."""
        if category == "All":
            return self.all()
        return [q for q in self._questions if q.category == category]

    def sample(self, category: str, count: int, rng: random.Random | None = None) -> list[Question]:
        """Return up to ``count`` random questions from ``category``.

        If the category has fewer than ``count`` questions, all of them are
        returned (shuffled) rather than raising an error. Pass ``rng`` for a
        seeded, reproducible selection (used in tests); defaults to the
        module-level random generator otherwise.
        """
        rng = rng or random
        pool = self.by_category(category)
        actual_count = min(count, len(pool))
        return rng.sample(pool, actual_count)    