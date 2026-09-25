"""Tkinter GUI for the onboarding quiz app.

The app is built as a stack of "screen" Frames inside one root window, with
a simple controller (App) that swaps the visible screen. Each screen only
talks to the domain/logic layers (models, storage, quiz engine) - never to
raw CSV files directly - so the GUI stays a thin presentation layer.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from models import CATEGORIES, Question, QuestionBank
from quiz_score_and_progress import NoQuestionsAvailableError, QuizSession
from storage import QuestionRepository, ResultRepository, StorageError
from validation import validate_candidate_name, validate_question_data

DATA_DIR = Path(__file__).resolve().parent / "data"
QUESTIONS_CSV = DATA_DIR / "questions.csv"
RESULTS_CSV = DATA_DIR / "results.csv"

NUM_QUESTIONS_PER_QUIZ = 5


class App(tk.Tk):
    """Root application window; owns shared data and swaps between screens."""

    def __init__(self):
        super().__init__()
        self.title("New Starter Onboarding & Compliance Quiz")
        self.geometry("640x520")
        self.minsize(560, 440)

        self.question_repo = QuestionRepository(QUESTIONS_CSV)
        self.result_repo = ResultRepository(RESULTS_CSV)

        self._container = tk.Frame(self)
        self._container.pack(fill="both", expand=True)

        self._current_screen: tk.Frame | None = None
        self.show_screen(HomeScreen)

    def show_screen(self, screen_class, **kwargs):
        """Destroy the current screen and replace it with a new one."""
        if self._current_screen is not None:
            self._current_screen.destroy()
        self._current_screen = screen_class(self._container, self, **kwargs)
        self._current_screen.pack(fill="both", expand=True)

    def load_question_bank(self) -> QuestionBank:
        """Load the question bank from disk, surfacing any row warnings.

        Raises StorageError (shown by the caller) if the file itself cannot
        be read - a genuine I/O problem, as opposed to a bad row.
        """
        questions, warnings = self.question_repo.load_all()
        if warnings:
            messagebox.showwarning(
                "Some questions were skipped",
                "The following rows in the question file could not be loaded:\n\n"
                + "\n".join(warnings),
            )
        return QuestionBank(questions)


class HomeScreen(tk.Frame):
    """Landing screen with navigation to the main features."""

    def __init__(self, parent, app: App):
        super().__init__(parent, padx=24, pady=24)
        self.app = app

        tk.Label(
            self, text="Onboarding & Compliance Quiz", font=("Helvetica", 20, "bold")
        ).pack(pady=(0, 4))
        tk.Label(
            self,
            text="Test your knowledge of company policies, health & safety,\n"
            "data protection, workplace ethics, and numeracy.",
            justify="center",
        ).pack(pady=(0, 24))

        tk.Button(self, text="Take a Quiz", width=28, command=self._take_quiz).pack(pady=6)
        tk.Button(
            self, text="Manage Question Bank", width=28, command=self._manage_questions
        ).pack(pady=6)
        tk.Button(self, text="View Results History", width=28, command=self._view_results).pack(
            pady=6
        )
        tk.Button(self, text="Quit", width=28, command=app.destroy).pack(pady=(24, 0))

    def _take_quiz(self):
        self.app.show_screen(StartQuizScreen)

    def _manage_questions(self):
        self.app.show_screen(ManageQuestionsScreen)

    def _view_results(self):
        self.app.show_screen(ResultsHistoryScreen)

class StartQuizScreen(tk.Frame):
    """Collects the candidate's name and chosen category before starting."""

    def __init__(self, parent, app: App):
        super().__init__(parent, padx=24, pady=24)
        self.app = app

        try:
            self.bank = app.load_question_bank()
        except StorageError as exc:
            messagebox.showerror("Could not load questions", str(exc))
            self.bank = QuestionBank([])

        tk.Label(self, text="Start a Quiz", font=("Helvetica", 16, "bold")).pack(pady=(0, 16))

        form = tk.Frame(self)
        form.pack(pady=8)

        tk.Label(form, text="Your name:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.name_entry = tk.Entry(form, width=30, relief="solid", borderwidth=1, bg="white", fg="black", highlightthickness=1, highlightbackground="gray")
        self.name_entry.grid(row=0, column=1, padx=6, pady=6)

        tk.Label(form, text="Category:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        available_categories = self.bank.categories_present()
        self.category_var = tk.StringVar(
            value=available_categories[0] if available_categories else ""
        )
        self.category_menu = ttk.Combobox(
            form,
            textvariable=self.category_var,
            values=["All"] + available_categories,
            state="readonly",
            width=27,
        )
        self.category_menu.grid(row=1, column=1, padx=6, pady=6)
        if available_categories:
            self.category_menu.set("All")

        if not available_categories:
            tk.Label(
                self,
                text="No questions are available yet. Add some in 'Manage Question Bank'.",
                fg="red",
            ).pack(pady=8)

        button_row = tk.Frame(self)
        button_row.pack(pady=20)
        tk.Button(button_row, text="Back", width=12, command=self._go_home).grid(
            row=0, column=0, padx=6
        )
        tk.Button(
            button_row, text="Start Quiz", width=12, command=self._start_quiz
        ).grid(row=0, column=1, padx=6)

    def _go_home(self):
        self.app.show_screen(HomeScreen)

    def _start_quiz(self):
        try:
            name = validate_candidate_name(self.name_entry.get())
        except ValueError as exc:
            messagebox.showerror("Invalid name", str(exc))
            return

        category = self.category_var.get()
        if not category:
            messagebox.showerror("No category", "Please choose a category.")
            return

        try:
            session = QuizSession.start(self.bank, name, category, NUM_QUESTIONS_PER_QUIZ)
        except NoQuestionsAvailableError as exc:
            messagebox.showerror("No questions available", str(exc))
            return

        self.app.show_screen(QuizQuestionScreen, session=session)


class QuizQuestionScreen(tk.Frame):
    """Displays one question at a time and collects the selected answer."""

    def __init__(self, parent, app: App, session: QuizSession):
        super().__init__(parent, padx=24, pady=24)
        self.app = app
        self.session = session
        self.selected_index = tk.IntVar(value=-1)

        self._render_question()

    def _render_question(self):
        for widget in self.winfo_children():
            widget.destroy()

        question: Question = self.session.current_question()
        self.selected_index.set(-1)

        tk.Label(
            self,
            text=f"Question {self.session.current_question_number} of "
            f"{self.session.total_questions} - {self.session.category}",
            font=("Helvetica", 10, "italic"),
        ).pack(anchor="w")

        tk.Label(
            self, text=question.text, font=("Helvetica", 14, "bold"), wraplength=560, justify="left"
        ).pack(anchor="w", pady=(8, 16))

        for index, option in enumerate(question.options):
            tk.Radiobutton(
                self,
                text=option,
                variable=self.selected_index,
                value=index,
                wraplength=540,
                justify="left",
                anchor="w",
            ).pack(fill="x", pady=2)

        tk.Button(self, text="Submit Answer", command=self._submit_answer).pack(pady=20)

    def _submit_answer(self):
        selected = self.selected_index.get()
        if selected == -1:
            messagebox.showerror("No answer selected", "Please choose an answer before continuing.")
            return

        self.session.submit_answer(selected)

        if self.session.is_finished():
            self._finish_quiz()
        else:
            self._render_question()

    def _finish_quiz(self):
        result = self.session.build_result()
        try:
            self.app.result_repo.append(result)
        except StorageError as exc:
            messagebox.showerror("Could not save result", str(exc))

        self.app.show_screen(QuizResultScreen, session=self.session, result=result)


class QuizResultScreen(tk.Frame):
    """Shows the final score and a review of correct/incorrect answers."""

    def __init__(self, parent, app: App, session: QuizSession, result):
        super().__init__(parent, padx=24, pady=24)
        self.app = app

        tk.Label(self, text="Quiz Complete", font=("Helvetica", 18, "bold")).pack(pady=(0, 8))
        tk.Label(
            self,
            text=f"{result.candidate_name} scored {result.score} / {result.total} "
            f"({result.percentage}%) in {result.category}",
            font=("Helvetica", 12),
        ).pack(pady=(0, 16))

        review_frame = tk.Frame(self)
        review_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(review_frame, borderwidth=0)
        scrollbar = tk.Scrollbar(review_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for i, answered in enumerate(session.review(), start=1):
            colour = "green" if answered.was_correct else "red"
            mark = "Correct" if answered.was_correct else "Incorrect"
            text = f"{i}. {answered.question.text}\n   Your answer: {answered.question.options[answered.selected_index]} ({mark})"
            if not answered.was_correct:
                text += f"\n   Correct answer: {answered.question.correct_answer}"
            tk.Label(inner, text=text, fg=colour, justify="left", wraplength=540, anchor="w").pack(
                fill="x", pady=4, anchor="w"
            )

        tk.Button(self, text="Back to Home", command=lambda: app.show_screen(HomeScreen)).pack(
            pady=16
        )

class ManageQuestionsScreen(tk.Frame):
    """Lists, adds, and removes questions in the bank; supports CSV export."""

    def __init__(self, parent, app: App):
        super().__init__(parent, padx=16, pady=16)
        self.app = app

        try:
            self.bank = app.load_question_bank()
        except StorageError as exc:
            messagebox.showerror("Could not load questions", str(exc))
            self.bank = QuestionBank([])

        tk.Label(self, text="Manage Question Bank", font=("Helvetica", 16, "bold")).pack(
            anchor="w", pady=(0, 12)
        )

        columns = ("category", "text", "correct_answer")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=14)
        self.tree.heading("category", text="Category")
        self.tree.heading("text", text="Question")
        self.tree.heading("correct_answer", text="Correct Answer")
        self.tree.column("category", width=120)
        self.tree.column("text", width=300)
        self.tree.column("correct_answer", width=120)
        self.tree.pack(fill="both", expand=True)

        self._refresh_tree()

        button_row = tk.Frame(self)
        button_row.pack(pady=12)
        tk.Button(button_row, text="Add Question", command=self._add_question).grid(
            row=0, column=0, padx=4
        )
        tk.Button(button_row, text="Delete Selected", command=self._delete_selected).grid(
            row=0, column=1, padx=4
        )
        tk.Button(button_row, text="Export to CSV...", command=self._export_csv).grid(
            row=0, column=2, padx=4
        )
        tk.Button(button_row, text="Back", command=lambda: app.show_screen(HomeScreen)).grid(
            row=0, column=3, padx=4
        )

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for question in self.bank.all():
            self.tree.insert(
                "",
                "end",
                iid=question.question_id,
                values=(question.category, question.text, question.correct_answer),
            )

    def _add_question(self):
        AddQuestionDialog(self, on_saved=self._on_question_added)

    def _on_question_added(self, question: Question):
        self.bank.add(question)
        try:
            self.app.question_repo.save_all(self.bank.all())
        except StorageError as exc:
            messagebox.showerror("Could not save question", str(exc))
            return
        self._refresh_tree()

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Select a question to delete first.")
            return
        question_id = selected[0]
        if not messagebox.askyesno("Confirm delete", "Delete the selected question?"):
            return
        self.bank.remove(question_id)
        try:
            self.app.question_repo.save_all(self.bank.all())
        except StorageError as exc:
            messagebox.showerror("Could not save changes", str(exc))
            return
        self._refresh_tree()

    def _export_csv(self):
        destination = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="questions_export.csv",
        )
        if not destination:
            return
        try:
            self.app.question_repo.save_all(self.bank.all())
            QuestionRepository(destination).save_all(self.bank.all())
        except StorageError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        messagebox.showinfo("Export complete", f"Questions exported to:\n{destination}")


class AddQuestionDialog(tk.Toplevel):
    """A modal dialog for entering a new question's details."""

    def __init__(self, parent, on_saved):
        super().__init__(parent)
        self.title("Add Question")
        self.geometry("480x420")
        self.on_saved = on_saved
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        form = tk.Frame(self, padx=16, pady=16)
        form.pack(fill="both", expand=True)

        tk.Label(form, text="Category:").grid(row=0, column=0, sticky="w", pady=4)
        self.category_var = tk.StringVar(value=CATEGORIES[0])
        ttk.Combobox(
            form, textvariable=self.category_var, values=CATEGORIES, state="readonly"
        ).grid(row=0, column=1, sticky="ew", pady=4)

        tk.Label(form, text="Question text:").grid(row=1, column=0, sticky="nw", pady=4)
        self.text_entry = tk.Text(form, width=32, height=3)
        self.text_entry.grid(row=1, column=1, pady=4)

        self.option_entries: list[tk.Entry] = []
        self.correct_var = tk.IntVar(value=0)
        for i in range(4):
            tk.Label(form, text=f"Option {i + 1}:").grid(row=2 + i, column=0, sticky="w", pady=2)
            entry = tk.Entry(form, width=30)
            entry.grid(row=2 + i, column=1, sticky="w", pady=2)
            self.option_entries.append(entry)
            tk.Radiobutton(form, text="Correct", variable=self.correct_var, value=i).grid(
                row=2 + i, column=2, padx=6
            )

        button_row = tk.Frame(form)
        button_row.grid(row=7, column=0, columnspan=3, pady=16)
        tk.Button(button_row, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=6)
        tk.Button(button_row, text="Save", command=self._save).grid(row=0, column=1, padx=6)

    def _save(self):
        options = [entry.get() for entry in self.option_entries]
        try:
            cleaned = validate_question_data(
                category=self.category_var.get(),
                text=self.text_entry.get("1.0", "end"),
                options=options,
                correct_index=self.correct_var.get(),
                allowed_categories=CATEGORIES,
            )
        except ValueError as exc:
            messagebox.showerror("Invalid question", str(exc))
            return

        question_id = f"q{abs(hash((cleaned['text'], cleaned['category']))) % 1_000_000:06d}"
        question = Question(
            question_id=question_id,
            category=cleaned["category"],
            text=cleaned["text"],
            options=cleaned["options"],
            correct_index=cleaned["correct_index"],
        )
        self.on_saved(question)
        self.destroy()

class ResultsHistoryScreen(tk.Frame):
    """Displays past quiz results and allows exporting the history to CSV."""

    def __init__(self, parent, app: App):
        super().__init__(parent, padx=16, pady=16)
        self.app = app

        tk.Label(self, text="Results History", font=("Helvetica", 16, "bold")).pack(
            anchor="w", pady=(0, 12)
        )

        try:
            results, warnings = app.result_repo.load_all()
        except StorageError as exc:
            messagebox.showerror("Could not load results", str(exc))
            results, warnings = [], []
        if warnings:
            messagebox.showwarning(
                "Some results were skipped",
                "The following rows in the results file could not be loaded:\n\n"
                + "\n".join(warnings),
            )

        columns = ("candidate_name", "category", "score", "total", "percentage", "timestamp")
        tree = ttk.Treeview(self, columns=columns, show="headings", height=14)
        headings = {
            "candidate_name": "Name",
            "category": "Category",
            "score": "Score",
            "total": "Total",
            "percentage": "%",
            "timestamp": "When",
        }
        for col, label in headings.items():
            tree.heading(col, text=label)
            tree.column(col, width=100)
        tree.pack(fill="both", expand=True)

        for result in results:
            tree.insert(
                "",
                "end",
                values=(
                    result.candidate_name,
                    result.category,
                    result.score,
                    result.total,
                    result.percentage,
                    result.timestamp.strftime("%Y-%m-%d %H:%M"),
                ),
            )

        button_row = tk.Frame(self)
        button_row.pack(pady=12)
        tk.Button(button_row, text="Export to CSV...", command=self._export).grid(
            row=0, column=0, padx=4
        )
        tk.Button(button_row, text="Back", command=lambda: app.show_screen(HomeScreen)).grid(
            row=0, column=1, padx=4
        )

    def _export(self):
        destination = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="results_export.csv",
        )
        if not destination:
            return
        try:
            self.app.result_repo.export_to(destination)
        except StorageError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        messagebox.showinfo("Export complete", f"Results exported to:\n{destination}")


def main():
    """Entry point: create the data directory if needed and launch the app."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()