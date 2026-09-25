# Onboarding & Compliance Quiz

## 1. Introduction

I work within a professional services environment where new employees are
expected to become familiar with a broad range of internal expectations very
quickly. This can include company policies, health and safety procedures,
data protection obligations, workplace conduct, and basic numeracy relevant
to day-to-day tasks. In many organisations, onboarding material of this kind
is delivered as static documents - namely PDFs, slide decks, or intranet
pages - that new starters are expected to read independently. This creates
two problems: managers have no reliable way of confirming the material has
actually sunk in, and staff have no quick way to check their own
understanding before it matters.

This project addresses both problems with a Minimum Viable Product: an
Onboarding & Compliance Quiz built as a desktop application in Python using
Tkinter. A user selects one or all of the following categories: Company
Policies, Health & Safety, Data Protection, Workplace Ethics, or Numeracy,
and completes a short multiple-choice quiz, receiving an immediate score and
a question-by-question review of anything answered incorrectly. An HR
administrator can manage the question bank through the same application, and
every attempt is logged to a results history that can be exported for
reporting.

Its relevance to the organisation is from a few angles. It turns a passive
reading exercise into something active and measurable, giving HR and line
managers actual visibility into whether onboarding material has landed,
rather than just trusting that it has. It also requires no server, database,
or ongoing licence cost, which matters for something that is, at this stage,
a proof of concept rather than a funded system. And because the core logic -
validation, scoring, and storage - is kept separate from the interface, it
could later sit behind a different front end, such as a web app, without
being rebuilt from scratch. This document covers how the application was
designed, built, tested, and documented.

## 2. Design

### 2.1 GUI Design

The application is built around a small set of screens, navigated from a
central Home screen. The wireframes below show the planned layout and user
journey.

[INSERT FIGMA WIREFRAME SCREENSHOTS HERE - Home screen, Start Quiz screen,
Quiz Question screen, and Manage Question Bank screen. Optional link to the
Figma file: INSERT LINK]

### 2.2 Functional and Non-Functional Requirements

**Functional requirements** - what the application must do:

| ID | Requirement |
|----|-------------|
| FR1 | Users can select a quiz category (or all categories) and complete a multiple-choice quiz. |
| FR2 | All user input (candidate name, new question data) is validated before being accepted. |
| FR3 | On completing a quiz, the user sees an immediate score and a review of any incorrect answers. |
| FR4 | An administrator can add and delete questions from the question bank via the GUI. |
| FR5 | The question bank and quiz results persist to CSV files between sessions. |
| FR6 | Users can export the question bank or results history to CSV. |
| FR7 | Users can view a history of every past quiz attempt. |

**Non-functional requirements** - how the application should perform:

| ID | Requirement |
|----|-------------|
| NFR1 (Usability) | The GUI is navigable without training, with legible input fields in both light and dark mode. |
| NFR2 (Reliability) | The application handles missing or malformed data files gracefully - a bad row is skipped with a warning, not a crash. |
| NFR3 (Maintainability) | Business logic (validation, scoring, persistence) is kept separate from the GUI, so it can be tested and reused without Tkinter. |
| NFR4 (Performance) | The application responds to user actions (loading the question bank, scoring a quiz) without a perceptible delay. |
| NFR5 (Portability) | Runs on any platform with Python 3.10+ and Tkinter, with no dependencies beyond the standard library. |

### 2.3 Tech Stack Outline

- **Language:** Python 3.10+
- **GUI framework:** Tkinter, with `ttk` for themed widgets (Treeview, Combobox) - standard library, no install needed, no runtime dependencies.
- **Data storage:** CSV files via Python's built-in `csv` module - plain-text, human-readable, and proportionate to the scale of a question bank and results log; a full database would be overkill.
- **Testing:** `pytest`, covering the validation, model, storage, and quiz session layers.
- **Version control and CI:** Git and GitHub, with GitHub Actions running the test suite automatically on every push.

### 2.4 Code Design Document

The core classes and how they relate to one another:

- **Question** - one multiple-choice question (`question_id`, `category`, `text`, `options`, `correct_index`). Built via `create()`, which validates the data first; converts to and from a CSV row via `to_row()`/`from_row()`.
- **QuestionBank** - holds a list of `Question` objects and provides `add()`, `remove()`, `by_category()`, and `sample()` (used to pick questions for a quiz).
- **QuizResult** - one completed quiz attempt (`candidate_name`, `category`, `score`, `total`, `timestamp`), with a computed `percentage` property.
- **QuizSession** - drives one quiz attempt: asks each `Question` from a `QuestionBank` in turn, records an `AnsweredQuestion` for each answer, and produces a `QuizResult` once finished.
- **AnsweredQuestion** - one answered question within a session (`question`, `selected_index`, `was_correct`).
- **QuestionRepository** - reads and writes `Question` objects to `questions.csv`.
- **ResultRepository** - reads, appends, and exports `QuizResult` objects to `results.csv`.

`QuestionBank` holds many `Question` objects. `QuizSession` draws questions
from a `QuestionBank`, records `AnsweredQuestion` entries as it goes, and
produces one `QuizResult` at the end. `QuestionRepository` and
`ResultRepository` persist `Question` and `QuizResult` objects respectively.

## 3. Development

The application is split into five layers: validation, domain models,
persistence, quiz session logic, and the GUI. Each has one responsibility.
The lower four know nothing about Tkinter, so they can be tested without
opening a single window.

### 3.1 Validation

`validation.py` holds pure functions. Given the same input, they always
return the same output, and none of them touch a file or the GUI. Each one
raises a `ValueError` with a specific message rather than returning `True`
or `False`, so calling code doesn't need an extra step to work out what went
wrong:

```python
def validate_options(options: list[str]) -> list[str]:
    if not isinstance(options, list):
        raise ValueError("Options must be provided as a list.")
    if not (MIN_OPTIONS <= len(options) <= MAX_OPTIONS):
        raise ValueError(
            f"A question must have between {MIN_OPTIONS} and {MAX_OPTIONS} "
            f"options (got {len(options)})."
        )
    cleaned = [validate_non_empty_text(option, "Option") for option in options]
    seen_lowercase = set()
    for option in cleaned:
        key = option.lower()
        if key in seen_lowercase:
            raise ValueError(f"Duplicate option found: '{option}'.")
        seen_lowercase.add(key)
    return cleaned
```

Keeping this separate from the GUI and from `Question` means the same rules
apply whether a question comes from the form or a CSV file. There is one
place that decides what counts as valid, not two.

### 3.2 Domain Models

`models.py` defines `Question`, `QuizResult`, and `QuestionBank`. `Question`
is built through a `create()` classmethod rather than its constructor
directly, so that validation always runs before an instance can exist:

```python
@classmethod
def create(cls, question_id, category, text, options, correct_index,
           allowed_categories=None) -> "Question":
    cleaned = validate_question_data(
        category=category, text=text, options=options,
        correct_index=correct_index,
        allowed_categories=allowed_categories or CATEGORIES,
    )
    return cls(question_id=question_id, **cleaned)
```

This means an invalid `Question` object can never exist in memory (i.e if
the data doesn't pass validation then construction won't complete).
`QuestionBank` wraps a list of questions and adds what the app needs, such
as `sample()`, which picks a random subset and accepts an optional seeded
random generator so a test can reproduce its behaviour exactly.

### 3.3 Persistence

`storage.py` reads and writes the CSV files. Rather than letting one bad row
fail the entire file, `load_all()` skips it and records a warning instead:

```python
for line_number, row in enumerate(reader, start=2):
    try:
        questions.append(Question.from_row(row))
    except (ValueError, KeyError) as exc:
        warnings.append(f"Row {line_number}: skipped ({exc})")
```

This matters in practice, since the question bank is a plain text file that
could easily be hand-edited, and one bad row shouldn't take the whole quiz
offline. The GUI surfaces these warnings rather than hiding them.

### 3.4 Quiz Session Logic

`quiz_score_and_progress.py` contains `QuizSession`, which tracks a single
attempt from the first question to the final score. It exposes a small,
deliberate set of methods - `current_question()`, `submit_answer()`,
`is_finished()`, `build_result()` - so the GUI only ever needs to call these,
never reach into the session's internal state directly:

```python
def submit_answer(self, selected_index: int) -> bool:
    question = self.current_question()
    self._answers.append(AnsweredQuestion(question, selected_index))
    self._current_index += 1
    return question.is_correct(selected_index)
```

If a quiz is started for a category with no questions, `QuizSession.start()`
raises a custom `NoQuestionsAvailableError` rather than a generic error,
which lets the GUI show a specific, useful message instead of a stack trace.

### 3.5 GUI

`gui.py` is built as a stack of Tkinter `Frame` screens, swapped in and out
by a single `App` controller:

```python
def show_screen(self, screen_class, **kwargs):
    if self._current_screen is not None:
        self._current_screen.destroy()
    self._current_screen = screen_class(self._container, self, **kwargs)
    self._current_screen.pack(fill="both", expand=True)
```

Each screen only calls into the layers above, it never opens a CSV file or
runs validation logic itself. Wherever something can go wrong - a malformed
CSV, an invalid answer, missing input - the call is wrapped in
`try`/`except` and shown to the user as a `messagebox`, rather than crashing
the application outright.

## 4. Testing

### 4.1 Testing Strategy and Methodology

Two testing approaches were used, matched to what each part of the
application actually is. The validation, model, storage, and quiz session
layers are pure logic with no GUI involved, so they were covered by
automated `pytest` unit tests, several written before the code they test,
following Test-Driven Development: write a test that fails because the
function doesn't exist yet (Red), then write just enough code to make it
pass (Green). This suits these functions well, since each one always
produces the same result for a given input.

The GUI (`gui.py`) was tested manually instead. Tkinter has no built-in way
to simulate a button click in an automated test, and GitHub Actions runs on
a machine with no display, so an automated GUI test wouldn't run there
anyway. Manual testing meant running the application directly and working
through the full user journey: taking a quiz, managing the question bank,
and reviewing results, repeated after every meaningful change.

Together, these are what make the CI pipeline meaningful: on every push,
GitHub Actions installs the project's dependencies and runs the full
`pytest` suite automatically, catching a regression in the logic layers
immediately, while the GUI is checked by hand first.

### 4.2 Outcomes of Application Testing

#### 4.2.1 Manual Test Outcomes

| Test Case | Steps | Expected Result | Actual Result | Pass/Fail |
|---|---|---|---|---|
| Take a quiz | Select a category, answer all 5 questions | Final score and a correct/incorrect review are shown | As expected | Pass |
| Add a question | Fill in category, text, 4 options, mark one correct, save | New question appears in the question bank list | As expected | Pass |
| Delete a question | Select a question, click Delete Selected, confirm | Question is removed from the list | As expected | Pass |
| Export question bank | Click Export to CSV, choose a location | A CSV file is created at that location | As expected | Pass |
| View results history | Complete a quiz, then open Results History | The completed attempt appears in the list | As expected | Pass |
| Export results history | Click Export to CSV on the Results screen | A CSV file is created at that location | As expected | Pass |
| Start quiz with no name entered | Leave the name field blank, click Start Quiz | An error message is shown, quiz does not start | As expected | Pass |
| Name field visibility (dark mode) | Open Start Quiz screen with system dark mode enabled | Name entry box is clearly visible with a solid border | Border was black on a dark background, effectively invisible | Fail |
| Name field visibility (dark mode, after fix) | Same as above, after adding an explicit white background and grey outline | Name entry box is clearly visible with a solid border | As expected | Pass |

[INSERT SCREENSHOT: name field before fix, black border invisible on dark
background]
[INSERT SCREENSHOT: name field after fix, white background with clear
border]

#### 4.2.2 Unit Testing Outcome

As an example of this process: `test_questions.py` was written before
`models.py` existed at all, so the first run failed on collection with
`ModuleNotFoundError: No module named 'models'`.

[INSERT SCREENSHOT: Red - ModuleNotFoundError, models.py does not exist yet]

Once the `Question` class was implemented in `models.py`, the same test
file passed - 21 tests in total, covering `test_validation.py` and
`test_questions.py`.

[INSERT SCREENSHOT: Green - Question implemented, 21 passed]

The same Red-Green approach was followed for the rest of `models.py`,
`storage.py`, and `quiz_score_and_progress.py`, taking the finished suite to
40 tests passing across all four non-GUI layers.

## 5. Documentation

### 5.1 User Documentation

The application opens on a Home screen with three options: Take a Quiz,
Manage Question Bank, and View Results History.

**Taking a quiz**: enter a name, choose a category (or "All"), and answer
five questions one at a time. On the last question, a final score and a
review of any incorrect answers are shown, and the attempt is saved
automatically.

**Managing the question bank**: the current questions are listed with their
category and correct answer. 'Add Question' opens a form for a new category,
question text, up to five options, and which one is correct. Any invalid
entries (missing text, duplicate options, no answer marked correct) are
rejected with a clear message. 'Delete Selected' removes a question after
confirmation, and 'Export to CSV' saves a copy of the question bank to any
location.

**Viewing results**: Every past attempt is listed with the candidate's name,
category, score, and date, and can be exported the same way.

All data is stored as plain CSV files under `data/` - `questions.csv` for
the question bank, and `results.csv`, created automatically after the first
completed quiz.

### 5.2 Technical Documentation

Setting up and running the project locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python3 run_app.py    # run the application
pytest                # run the test suite
```

The full breakdown of how the code works, including the five-layer
architecture, and what each class and function is responsible for, is
covered in Section 3 (Development) above. The CI configuration in
`.github/workflows/ci.yml` runs the same `pytest` command automatically on
every push to GitHub.

## 6. Evaluation

The layered structure turned out to be the right call. Splitting validation,
models, storage, and quiz logic away from the GUI meant most of the
application could genuinely be developed test-first, and when something
broke, it was almost always obvious which layer it broke in. The graceful
degradation approach in `storage.py` - skipping a malformed CSV row with a
warning instead of crashing - also proved its worth in practice rather than
just in theory, as a hand-typed CSV file can easily pick up a stray typo.

A few real defects came up too, not just process slips. The question bank
was originally drafted as plain text with commas inside a few answer
options. That silently broke the CSV parser: a misunderstanding of how
comma-delimited data behaves, and it went unnoticed until the file was
actually loaded and inspected, rather than just proofread. The Tkinter
styling had a real defect as well. The application worked correctly, but
the name field's border rendered solid black regardless of the system's
colour scheme, making it invisible on a dark background. Manually testing
on a dark-mode machine caught it; nothing in the code itself raised an
error.

Some of what went wrong was closer to process than logic. A file would
appear broken when it was actually just unsaved. A decorator once ended up
indented under the wrong class by a single misplaced space, and a GUI file
was accidentally created inside the `data` folder rather than the project
root. None of these took long to fix once spotted, but each was a reminder
that "the code doesn't work" often just means "the code I'm looking at
isn't the code that ran."

There are gaps too. The GUI has no automated tests, so a regression there
can only be caught by hand - a deliberate trade-off given Tkinter's limits
in a headless CI environment, but still a real limitation. The question
bank only supports multiple-choice questions; short-answer or numeric
questions were considered and left out to keep the MVP scope realistic. And
the wireframes were produced after the application was built rather than
before it - a design-first pass would likely have caught the dark mode
contrast issue before testing did.

## References

- [Python 3 documentation](https://docs.python.org/3/)
- [Tkinter documentation](https://docs.python.org/3/library/tkinter.html)
- [pytest documentation](https://docs.pytest.org/)
- [Python csv module documentation](https://docs.python.org/3/library/csv.html)
- [GitHub Actions documentation](https://docs.github.com/en/actions)
