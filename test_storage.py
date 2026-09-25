from models import Question, QuizResult
from storage import QuestionRepository, ResultRepository


def make_question(question_id="q1"):
    return Question.create(
        question_id=question_id,
        category="Numeracy",
        text="What is 12 squared?",
        options=["144", "124", "132", "164"],
        correct_index=0,
    )


def test_question_repository_returns_empty_when_file_missing(tmp_path):
    repo = QuestionRepository(tmp_path / "missing.csv")
    questions, warnings = repo.load_all()
    assert questions == []
    assert warnings == []


def test_question_repository_round_trip(tmp_path):
    repo = QuestionRepository(tmp_path / "questions.csv")
    original = [make_question("q1"), make_question("q2")]
    repo.save_all(original)

    loaded, warnings = repo.load_all()

    assert warnings == []
    assert [q.question_id for q in loaded] == ["q1", "q2"]
    assert loaded[0].options == original[0].options


def test_question_repository_skips_malformed_rows_with_warning(tmp_path):
    csv_path = tmp_path / "questions.csv"
    csv_path.write_text(
        "question_id,category,text,options,correct_index\n"
        "q1,Numeracy,What is 12 squared?,144|124|132|164,0\n"
        "q2,NotARealCategory,Bad row,A|B,0\n",
        encoding="utf-8",
    )
    repo = QuestionRepository(csv_path)

    questions, warnings = repo.load_all()

    assert [q.question_id for q in questions] == ["q1"]
    assert len(warnings) == 1
    assert "Row 3" in warnings[0]


def test_result_repository_append_and_load(tmp_path):
    repo = ResultRepository(tmp_path / "results.csv")
    repo.append(QuizResult(candidate_name="Ada", category="Numeracy", score=4, total=5))
    repo.append(QuizResult(candidate_name="Grace", category="Numeracy", score=5, total=5))

    results, warnings = repo.load_all()

    assert warnings == []
    assert [r.candidate_name for r in results] == ["Ada", "Grace"]


def test_result_repository_export_to_creates_new_file(tmp_path):
    source = ResultRepository(tmp_path / "results.csv")
    source.append(QuizResult(candidate_name="Ada", category="Numeracy", score=4, total=5))

    destination_path = tmp_path / "export" / "backup.csv"
    source.export_to(destination_path)

    exported, _ = ResultRepository(destination_path).load_all()
    assert len(exported) == 1
    assert exported[0].candidate_name == "Ada"