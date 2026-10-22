import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from autoapply.modules.applying.models import FieldKind, PendingQuestion
from autoapply.modules.applying.pending import group_pending_questions
from autoapply.modules.applying.store import replace_pending_questions, save_job_folder
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import insert_job

CREATED_AT = datetime(2026, 10, 21, 22, 0)
ENGLISH = "Você possui inglês avançado?"


def add_pending_job(
    connection: sqlite3.Connection,
    build_job: Callable[..., Job],
    job_id: str,
    questions: list[str],
    status: JobStatus = JobStatus.PENDING_QUESTION,
) -> None:
    insert_job(connection, build_job(id=job_id, title=f"Vaga {job_id}", status=status))
    replace_pending_questions(
        connection,
        job_id,
        [
            PendingQuestion(
                job_id=job_id, question=question, field_kind=FieldKind.SELECT, options=["Yes", "No"], created_at=CREATED_AT
            )
            for question in questions
        ],
    )


def test_group_pending_questions_merges_equal_questions_and_says_where_to_answer(
    connection: sqlite3.Connection, build_job: Callable[..., Job], tmp_path: Path
) -> None:
    folder = tmp_path / "vagas" / "2026-10-21-empresa-busca"
    add_pending_job(connection, build_job, "normal", [ENGLISH, "Já trabalhou na T-Systems?"])
    add_pending_job(connection, build_job, "busca", ["você possui ingles avancado"])
    save_job_folder(connection, "busca", folder)
    add_pending_job(connection, build_job, "outra", [" Você possui inglês avançado ?"])
    add_pending_job(connection, build_job, "ja-aplicada", [ENGLISH, "Possui CNH?"], JobStatus.APPLIED)

    groups = group_pending_questions(connection)

    assert [(group.question, [job.id for job in group.jobs]) for group in groups] == [
        (ENGLISH, ["normal", "busca", "outra"]),
        ("Já trabalhou na T-Systems?", ["normal"]),
    ]
    assert (groups[0].field_kind, groups[0].options) == (FieldKind.SELECT, ["Yes", "No"])
    assert groups[0].answer_places == ["config.md", str(folder / "respostas.md")]
    assert groups[1].answer_places == ["config.md"]
