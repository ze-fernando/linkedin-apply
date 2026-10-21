import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from autoapply.modules.applying.models import ApplicationAttempt, AttemptOutcome, FieldKind, PendingQuestion


def save_job_folder(connection: sqlite3.Connection, job_id: str, folder: Path) -> None:
    connection.execute("INSERT OR REPLACE INTO job_folders (job_id, folder) VALUES (?, ?)", [job_id, str(folder)])


def find_job_folder(connection: sqlite3.Connection, job_id: str) -> Path | None:
    row = connection.execute("SELECT folder FROM job_folders WHERE job_id = ?", [job_id]).fetchone()
    return None if row is None else Path(row[0])


def record_attempt(connection: sqlite3.Connection, attempt: ApplicationAttempt) -> None:
    connection.execute(
        "INSERT INTO application_attempts (job_id, mode, outcome, reason, resume_file, attempted_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            attempt.job_id,
            attempt.mode,
            attempt.outcome,
            attempt.reason,
            attempt.resume_file,
            attempt.attempted_at.isoformat(),
        ],
    )


def count_applied_on(connection: sqlite3.Connection, day: date) -> int:
    row = connection.execute(
        "SELECT COUNT(*) FROM application_attempts WHERE outcome = ? AND date(attempted_at) = ?",
        [AttemptOutcome.APPLIED, day.isoformat()],
    ).fetchone()
    return row[0]


def has_applied(connection: sqlite3.Connection, job_id: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM application_attempts WHERE job_id = ? AND outcome = ? LIMIT 1",
        [job_id, AttemptOutcome.APPLIED],
    ).fetchone()
    return row is not None


def replace_pending_questions(connection: sqlite3.Connection, job_id: str, questions: list[PendingQuestion]) -> None:
    connection.execute("DELETE FROM pending_questions WHERE job_id = ?", [job_id])
    connection.executemany(
        "INSERT INTO pending_questions (job_id, question, field_kind, options, created_at) VALUES (?, ?, ?, ?, ?)",
        [
            [
                question.job_id,
                question.question,
                question.field_kind,
                json.dumps(question.options, ensure_ascii=False),
                question.created_at.isoformat(),
            ]
            for question in questions
        ],
    )


def list_pending_questions(connection: sqlite3.Connection) -> list[PendingQuestion]:
    rows = connection.execute(
        "SELECT job_id, question, field_kind, options, created_at FROM pending_questions ORDER BY id"
    ).fetchall()
    return [
        PendingQuestion(
            job_id=job_id,
            question=question,
            field_kind=FieldKind(field_kind),
            options=json.loads(options),
            created_at=datetime.fromisoformat(created_at),
        )
        for job_id, question, field_kind, options, created_at in rows
    ]
