import copy
import sqlite3
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from autoapply.modules.applying.models import (
    ApplicationAttempt,
    ApplicationCandidate,
    ApplicationOutcome,
    ApplicationResult,
    ApplyMode,
    AttemptOutcome,
    FieldKind,
    FormField,
)
from autoapply.modules.applying.runner import run_applications
from autoapply.modules.applying.store import count_applied_on, has_applied, list_pending_questions, record_attempt
from autoapply.modules.config.loader import parse_config_data
from autoapply.modules.config.models import Config
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import insert_job, list_jobs

NOW = datetime(2026, 10, 21, 14, 0)
SALARY_FIELD = FormField(
    element_id="salario", kind=FieldKind.NUMBER, label="Pretensão salarial em USD", required=True, value=None, options=[]
)


def build_apply(
    results: dict[str, ApplicationResult], calls: list[str]
) -> Callable[[ApplicationCandidate], ApplicationResult]:
    def apply(candidate: ApplicationCandidate) -> ApplicationResult:
        calls.append(candidate.job.id)
        return results[candidate.job.id]

    return apply


def build_result(outcome: ApplicationOutcome, pending_fields: list[FormField] | None = None) -> ApplicationResult:
    return ApplicationResult(outcome=outcome, reason=f"motivo {outcome}", pending_fields=pending_fields or [])


def build_config(valid_data: dict[str, object], base_dir: Path, daily_limit: int) -> Config:
    data = copy.deepcopy(valid_data)
    data["regras"]["limite_diario"] = daily_limit
    return parse_config_data(data, base_dir)


def prepare_candidates(
    connection: sqlite3.Connection, build_job: Callable[..., Job], job_ids: list[str]
) -> list[ApplicationCandidate]:
    candidates = []
    for job_id in job_ids:
        job = build_job(id=job_id, status=JobStatus.AWAITING_RESUME)
        insert_job(connection, job)
        candidates.append(
            ApplicationCandidate(job=job, resume_file=Path(f"vagas/{job_id}/cv.pdf"), job_answers={}, score=80)
        )
    return candidates


def record_applied(connection: sqlite3.Connection, job_id: str) -> None:
    record_attempt(
        connection,
        ApplicationAttempt(
            job_id=job_id,
            mode=ApplyMode.NORMAL,
            outcome=AttemptOutcome.APPLIED,
            reason=None,
            resume_file=None,
            attempted_at=NOW,
        ),
    )


def read_statuses(connection: sqlite3.Connection) -> dict[str, JobStatus]:
    return {job.id: job.status for job in list_jobs(connection)}


def test_run_applications_stops_at_the_daily_limit_counting_earlier_applications(
    connection: sqlite3.Connection, valid_data: dict[str, object], base_dir: Path, build_job: Callable[..., Job]
) -> None:
    insert_job(connection, build_job(id="antes"))
    record_applied(connection, "antes")
    candidates = prepare_candidates(connection, build_job, ["a", "b", "c"])
    calls = []
    waits = []
    apply = build_apply({job_id: build_result(ApplicationOutcome.APPLIED) for job_id in ["a", "b", "c"]}, calls)

    summary = run_applications(
        connection,
        build_config(valid_data, base_dir, daily_limit=2),
        candidates,
        ApplyMode.SEARCH,
        False,
        apply,
        lambda: waits.append(NOW),
        lambda: NOW,
        lambda entry: None,
    )

    assert calls == ["a"]
    assert waits == []
    assert summary.limit_reached is True
    assert summary.not_attempted == 2
    assert count_applied_on(connection, date(2026, 10, 21)) == 2


def test_run_applications_records_each_outcome_and_skips_jobs_already_applied(
    connection: sqlite3.Connection, valid_data: dict[str, object], base_dir: Path, build_job: Callable[..., Job]
) -> None:
    candidates = prepare_candidates(connection, build_job, ["ok", "pendente", "falha", "manual", "repetida"])
    record_applied(connection, "repetida")
    calls = []
    waits = []
    apply = build_apply(
        {
            "ok": build_result(ApplicationOutcome.APPLIED),
            "pendente": build_result(ApplicationOutcome.PENDING, [SALARY_FIELD]),
            "falha": build_result(ApplicationOutcome.FAILED),
            "manual": build_result(ApplicationOutcome.ALREADY_APPLIED),
        },
        calls,
    )
    shown = []

    summary = run_applications(
        connection,
        build_config(valid_data, base_dir, daily_limit=15),
        candidates,
        ApplyMode.SEARCH,
        False,
        apply,
        lambda: waits.append(NOW),
        lambda: NOW,
        shown.append,
    )

    assert calls == ["ok", "pendente", "falha", "manual"]
    assert len(waits) == 3
    assert [entry.result.outcome for entry in summary.entries] == [
        ApplicationOutcome.APPLIED,
        ApplicationOutcome.PENDING,
        ApplicationOutcome.FAILED,
        ApplicationOutcome.ALREADY_APPLIED,
        ApplicationOutcome.ALREADY_APPLIED,
    ]
    assert shown == summary.entries
    assert summary.limit_reached is False
    assert summary.not_attempted == 0
    statuses = read_statuses(connection)
    assert statuses["ok"] == JobStatus.APPLIED
    assert statuses["pendente"] == JobStatus.PENDING_QUESTION
    assert statuses["falha"] == JobStatus.FAILED
    assert statuses["manual"] == JobStatus.APPLIED
    assert count_applied_on(connection, date(2026, 10, 21)) == 2
    assert has_applied(connection, "manual") is True
    [question] = list_pending_questions(connection)
    assert (question.job_id, question.question, question.field_kind) == (
        "pendente",
        "Pretensão salarial em USD",
        FieldKind.NUMBER,
    )


def test_run_applications_in_simulation_ignores_the_limit_and_writes_nothing(
    connection: sqlite3.Connection, valid_data: dict[str, object], base_dir: Path, build_job: Callable[..., Job]
) -> None:
    insert_job(connection, build_job(id="antes"))
    record_applied(connection, "antes")
    candidates = prepare_candidates(connection, build_job, ["a", "b"])
    calls = []
    apply = build_apply(
        {
            "a": build_result(ApplicationOutcome.SIMULATED),
            "b": build_result(ApplicationOutcome.PENDING, [SALARY_FIELD]),
        },
        calls,
    )

    summary = run_applications(
        connection,
        build_config(valid_data, base_dir, daily_limit=1),
        candidates,
        ApplyMode.SEARCH,
        True,
        apply,
        lambda: None,
        lambda: NOW,
        lambda entry: None,
    )

    assert calls == ["a", "b"]
    assert summary.limit_reached is False
    assert read_statuses(connection) == {
        "antes": JobStatus.COLLECTED,
        "a": JobStatus.AWAITING_RESUME,
        "b": JobStatus.AWAITING_RESUME,
    }
    assert count_applied_on(connection, date(2026, 10, 21)) == 1
    assert list_pending_questions(connection) == []
