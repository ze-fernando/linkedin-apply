import sqlite3
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pytest

from autoapply.modules.applying.models import ApplicationAttempt, ApplyMode, AttemptOutcome, FieldKind, PendingQuestion
from autoapply.modules.applying.store import (
    count_applied_on,
    has_applied,
    list_pending_questions,
    record_attempt,
    replace_pending_questions,
)
from autoapply.shared.database import open_database


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = open_database(tmp_path / "autoapply.db")
    yield connection
    connection.close()


def build_attempt(job_id: str, outcome: AttemptOutcome, attempted_at: datetime) -> ApplicationAttempt:
    return ApplicationAttempt(
        job_id=job_id,
        mode=ApplyMode.SEARCH,
        outcome=outcome,
        reason=None,
        resume_file="vagas/pasta/cv.pdf",
        attempted_at=attempted_at,
    )


def test_count_applied_on_counts_only_applications_sent_that_day(connection: sqlite3.Connection) -> None:
    record_attempt(connection, build_attempt("a", AttemptOutcome.APPLIED, datetime(2026, 10, 21, 9, 0)))
    record_attempt(connection, build_attempt("b", AttemptOutcome.APPLIED, datetime(2026, 10, 21, 23, 59)))
    record_attempt(connection, build_attempt("c", AttemptOutcome.PENDING, datetime(2026, 10, 21, 10, 0)))
    record_attempt(connection, build_attempt("d", AttemptOutcome.FAILED, datetime(2026, 10, 21, 11, 0)))
    record_attempt(connection, build_attempt("e", AttemptOutcome.APPLIED, datetime(2026, 10, 20, 23, 59)))

    assert count_applied_on(connection, date(2026, 10, 21)) == 2
    assert count_applied_on(connection, date(2026, 10, 22)) == 0


def test_has_applied_is_true_only_after_an_applied_attempt(connection: sqlite3.Connection) -> None:
    record_attempt(connection, build_attempt("pendente", AttemptOutcome.PENDING, datetime(2026, 10, 21, 9, 0)))
    record_attempt(connection, build_attempt("enviada", AttemptOutcome.PENDING, datetime(2026, 10, 21, 9, 0)))
    record_attempt(connection, build_attempt("enviada", AttemptOutcome.APPLIED, datetime(2026, 10, 21, 10, 0)))

    assert has_applied(connection, "enviada") is True
    assert has_applied(connection, "pendente") is False
    assert has_applied(connection, "nunca") is False


def build_question(job_id: str, question: str, kind: FieldKind, options: list[str]) -> PendingQuestion:
    return PendingQuestion(
        job_id=job_id,
        question=question,
        field_kind=kind,
        options=options,
        created_at=datetime(2026, 10, 21, 9, 0),
    )


def test_replace_pending_questions_keeps_only_the_latest_questions_of_each_job(
    connection: sqlite3.Connection,
) -> None:
    old_question = build_question("a", "Possui CNH?", FieldKind.RADIO, ["Sim", "Não"])
    other_job = build_question("b", "How many years with AWS?", FieldKind.NUMBER, [])
    new_question = build_question("a", "Nível de espanhol", FieldKind.SELECT, ["Básico", "Fluente"])
    replace_pending_questions(connection, "a", [old_question, build_question("a", "Cidade", FieldKind.TEXT, [])])
    replace_pending_questions(connection, "b", [other_job])

    replace_pending_questions(connection, "a", [new_question])

    assert list_pending_questions(connection) == [other_job, new_question]


def test_replace_pending_questions_with_empty_list_clears_the_job(connection: sqlite3.Connection) -> None:
    replace_pending_questions(connection, "a", [build_question("a", "Possui CNH?", FieldKind.RADIO, ["Sim", "Não"])])

    replace_pending_questions(connection, "a", [])

    assert list_pending_questions(connection) == []
