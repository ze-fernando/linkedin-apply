import sqlite3
from collections.abc import Callable
from datetime import datetime

import pytest

from autoapply.modules.applying.models import ApplicationAttempt, ApplyMode, AttemptOutcome
from autoapply.modules.applying.store import record_attempt
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import insert_job
from autoapply.modules.matching.models import Analyzer, JobAnalysis
from autoapply.modules.matching.store import save_analysis
from autoapply.modules.reporting.models import ReportEntry
from autoapply.modules.reporting.report import build_report

SINCE = datetime(2026, 10, 15)
CITY_FAILURE = "tipo de campo não suportado: 'Cidade'"
TAILORED_PDF = "curriculos-enviados/2026-10-21-empresa-e-dev.pdf"


def add_job(
    connection: sqlite3.Connection,
    build_job: Callable[..., Job],
    job_id: str,
    score: int | None = None,
    status: JobStatus = JobStatus.EVALUATED,
    collected_at: datetime = datetime(2026, 10, 9, 8, 0),
) -> None:
    insert_job(
        connection,
        build_job(
            id=job_id,
            company=f"Empresa {job_id}",
            title=f"Dev {job_id}",
            url=f"https://www.linkedin.com/jobs/view/{job_id}/",
            status=status,
            collected_at=collected_at,
        ),
    )
    if score is not None:
        save_analysis(
            connection,
            JobAnalysis(
                job_id=job_id,
                resume_name="Back-end",
                score=score,
                pre_score=50,
                summary="Resumo.",
                requirements=[],
                keywords=[],
                gap=[],
                analyzer=Analyzer.KEYWORDS,
                model=None,
                analyzed_at=collected_at,
            ),
        )


def add_attempt(
    connection: sqlite3.Connection,
    job_id: str,
    mode: ApplyMode,
    outcome: AttemptOutcome,
    attempted_at: datetime,
    reason: str | None = None,
    resume_file: str = "cv_base/dotnet.docx",
) -> None:
    record_attempt(
        connection,
        ApplicationAttempt(
            job_id=job_id,
            mode=mode,
            outcome=outcome,
            reason=reason,
            resume_file=resume_file,
            attempted_at=attempted_at,
        ),
    )


def fill_history(connection: sqlite3.Connection, build_job: Callable[..., Job]) -> sqlite3.Connection:
    for job_id, score in [("a", 90), ("b", 80), ("c", 75), ("d", 72), ("e", 85), ("f", 70), ("x", 71), ("y", None)]:
        add_job(connection, build_job, job_id, score)
    add_job(connection, build_job, "g", status=JobStatus.IGNORED, collected_at=datetime(2026, 10, 20, 9, 0))
    add_job(connection, build_job, "h", status=JobStatus.IGNORED, collected_at=datetime(2026, 10, 1, 9, 0))
    add_attempt(connection, "a", ApplyMode.SEARCH, AttemptOutcome.FAILED, datetime(2026, 10, 10, 9, 0), "antiga")
    add_attempt(connection, "a", ApplyMode.SEARCH, AttemptOutcome.APPLIED, datetime(2026, 10, 20, 9, 0))
    add_attempt(connection, "b", ApplyMode.NORMAL, AttemptOutcome.PENDING, datetime(2026, 10, 16, 9, 0))
    add_attempt(connection, "b", ApplyMode.NORMAL, AttemptOutcome.FAILED, datetime(2026, 10, 18, 9, 0), CITY_FAILURE)
    add_attempt(connection, "c", ApplyMode.NORMAL, AttemptOutcome.FAILED, datetime(2026, 10, 17, 9, 0), CITY_FAILURE)
    add_attempt(connection, "d", ApplyMode.NORMAL, AttemptOutcome.FAILED, datetime(2026, 10, 21, 9, 0), "erro de validação")
    add_attempt(connection, "x", ApplyMode.NORMAL, AttemptOutcome.FAILED, datetime(2026, 10, 21, 10, 0), "etapa sem botão")
    add_attempt(connection, "y", ApplyMode.NORMAL, AttemptOutcome.FAILED, datetime(2026, 10, 21, 11, 0), "formulário longo")
    add_attempt(
        connection, "e", ApplyMode.NORMAL, AttemptOutcome.APPLIED, datetime(2026, 10, 21, 12, 0), resume_file=TAILORED_PDF
    )
    add_attempt(connection, "f", ApplyMode.NORMAL, AttemptOutcome.ALREADY_APPLIED, datetime(2026, 10, 22, 9, 0))
    return connection


@pytest.fixture
def history(connection: sqlite3.Connection, build_job: Callable[..., Job]) -> sqlite3.Connection:
    return fill_history(connection, build_job)


def test_build_report_counts_every_attempt_in_the_period_and_lists_the_last_one_per_job(
    history: sqlite3.Connection,
) -> None:
    report = build_report(history, SINCE)

    assert report.counts == {
        (ApplyMode.SEARCH, AttemptOutcome.APPLIED): 1,
        (ApplyMode.NORMAL, AttemptOutcome.APPLIED): 1,
        (ApplyMode.NORMAL, AttemptOutcome.ALREADY_APPLIED): 1,
        (ApplyMode.NORMAL, AttemptOutcome.PENDING): 1,
        (ApplyMode.NORMAL, AttemptOutcome.FAILED): 5,
    }
    assert report.ignored == 1
    assert report.completion_rate == pytest.approx(2 / 8)
    assert report.failure_reasons == [(CITY_FAILURE, 2), ("erro de validação", 1), ("etapa sem botão", 1)]
    assert [(entry.job_id, entry.outcome) for entry in report.entries] == [
        ("f", AttemptOutcome.ALREADY_APPLIED),
        ("e", AttemptOutcome.APPLIED),
        ("y", AttemptOutcome.FAILED),
        ("x", AttemptOutcome.FAILED),
        ("d", AttemptOutcome.FAILED),
        ("a", AttemptOutcome.APPLIED),
        ("b", AttemptOutcome.FAILED),
        ("c", AttemptOutcome.FAILED),
    ]
    assert report.entries[1] == ReportEntry(
        job_id="e",
        attempted_at=datetime(2026, 10, 21, 12, 0),
        mode=ApplyMode.NORMAL,
        outcome=AttemptOutcome.APPLIED,
        company="Empresa e",
        title="Dev e",
        score=85,
        resume_file=TAILORED_PDF,
        tailored=True,
        url="https://www.linkedin.com/jobs/view/e/",
    )
    assert (report.entries[2].score, report.entries[2].tailored) == (None, False)


def test_build_report_without_start_includes_the_whole_history(history: sqlite3.Connection) -> None:
    report = build_report(history, None)

    assert report.counts[(ApplyMode.SEARCH, AttemptOutcome.FAILED)] == 1
    assert report.ignored == 2
    assert report.failure_reasons[0] == (CITY_FAILURE, 2)
    assert len(report.entries) == 8


def test_build_report_without_attempts_has_no_completion_rate(connection: sqlite3.Connection) -> None:
    report = build_report(connection, SINCE)

    assert (report.counts, report.ignored, report.completion_rate, report.failure_reasons, report.entries) == (
        {},
        0,
        None,
        [],
        [],
    )
