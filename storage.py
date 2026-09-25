"""CSV-backed persistence for questions and quiz results.

Each repository class owns one CSV file and is responsible for translating
between rows on disk and domain objects (Question / QuizResult). Malformed
rows are skipped rather than crashing the whole load, since a single bad row
(e.g. from manual CSV editing) shouldn't make the entire question bank or
results history unusable.
"""

from __future__ import annotations

import csv
from pathlib import Path

from models import Question, QuizResult


class StorageError(Exception):
    """Raised when a CSV file cannot be read or written due to I/O problems."""


QUESTION_FIELDS = ["question_id", "category", "text", "options", "correct_index"]
RESULT_FIELDS = ["candidate_name", "category", "score", "total", "percentage", "timestamp"]


class QuestionRepository:
    """Reads and writes the question bank CSV file."""

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)

    def load_all(self) -> tuple[list[Question], list[str]]:
        """Load every question from the CSV file.

        Returns a tuple of (questions, warnings). ``warnings`` contains a
        human-readable message for each row that was skipped because it was
        malformed, so the GUI can inform the user without aborting the load.
        If the file does not exist yet, returns ([], []) since an empty bank
        is a normal starting state, not an error.
        """
        if not self.csv_path.exists():
            return [], []

        questions: list[Question] = []
        warnings: list[str] = []
        try:
            with self.csv_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for line_number, row in enumerate(reader, start=2):
                    try:
                        questions.append(Question.from_row(row))
                    except (ValueError, KeyError) as exc:
                        warnings.append(f"Row {line_number}: skipped ({exc})")
        except OSError as exc:
            raise StorageError(f"Could not read question file '{self.csv_path}': {exc}") from exc

        return questions, warnings

    def save_all(self, questions: list[Question]) -> None:
        """Overwrite the CSV file with the given list of questions."""
        try:
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            with self.csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=QUESTION_FIELDS)
                writer.writeheader()
                for question in questions:
                    writer.writerow(question.to_row())
        except OSError as exc:
            raise StorageError(f"Could not write question file '{self.csv_path}': {exc}") from exc


class ResultRepository:
    """Reads and appends to the quiz results history CSV file."""

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)

    def load_all(self) -> tuple[list[QuizResult], list[str]]:
        """Load every past result from the CSV file.

        Returns a tuple of (results, warnings), following the same
        skip-and-report-malformed-rows approach as QuestionRepository.load_all.
        """
        if not self.csv_path.exists():
            return [], []

        results: list[QuizResult] = []
        warnings: list[str] = []
        try:
            with self.csv_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for line_number, row in enumerate(reader, start=2):
                    try:
                        results.append(QuizResult.from_row(row))
                    except (ValueError, KeyError) as exc:
                        warnings.append(f"Row {line_number}: skipped ({exc})")
        except OSError as exc:
            raise StorageError(f"Could not read results file '{self.csv_path}': {exc}") from exc

        return results, warnings

    def append(self, result: QuizResult) -> None:
        """Append one result to the CSV file, creating it with a header if needed."""
        try:
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            file_exists = self.csv_path.exists()
            with self.csv_path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(result.to_row())
        except OSError as exc:
            raise StorageError(f"Could not write results file '{self.csv_path}': {exc}") from exc

    def export_to(self, destination: str | Path) -> None:
        """Copy the results file to a new location chosen by the user (e.g. for export)."""
        results, _ = self.load_all()
        destination_repo = ResultRepository(destination)
        try:
            destination_repo.csv_path.parent.mkdir(parents=True, exist_ok=True)
            with destination_repo.csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
                writer.writeheader()
                for result in results:
                    writer.writerow(result.to_row())
        except OSError as exc:
            raise StorageError(f"Could not export results to '{destination}': {exc}") from exc