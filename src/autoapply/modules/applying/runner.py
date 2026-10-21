import sqlite3
from collections.abc import Callable
from datetime import datetime

from autoapply.modules.applying.models import (
    ApplicationAttempt,
    ApplicationCandidate,
    ApplicationOutcome,
    ApplicationResult,
    ApplyMode,
    AttemptOutcome,
    PendingQuestion,
    RunEntry,
    RunSummary,
)
from autoapply.modules.applying.store import count_applied_on, has_applied, record_attempt, replace_pending_questions
from autoapply.modules.config.models import Config
from autoapply.modules.jobs.models import JobStatus
from autoapply.modules.jobs.store import update_job_status

ALREADY_APPLIED_REASON = "já aplicada antes"
RECORDED_OUTCOMES = {
    ApplicationOutcome.APPLIED: (AttemptOutcome.APPLIED, JobStatus.APPLIED),
    ApplicationOutcome.ALREADY_APPLIED: (AttemptOutcome.ALREADY_APPLIED, JobStatus.APPLIED),
    ApplicationOutcome.PENDING: (AttemptOutcome.PENDING, JobStatus.PENDING_QUESTION),
    ApplicationOutcome.FAILED: (AttemptOutcome.FAILED, JobStatus.FAILED),
}


def build_pending_questions(job_id: str, result: ApplicationResult, created_at: datetime) -> list[PendingQuestion]:
    return [
        PendingQuestion(
            job_id=job_id, question=field.label, field_kind=field.kind, options=field.options, created_at=created_at
        )
        for field in result.pending_fields
    ]


def record_result(
    connection: sqlite3.Connection,
    candidate: ApplicationCandidate,
    mode: ApplyMode,
    result: ApplicationResult,
    attempted_at: datetime,
) -> None:
    attempt_outcome, status = RECORDED_OUTCOMES[result.outcome]
    record_attempt(
        connection,
        ApplicationAttempt(
            job_id=candidate.job.id,
            mode=mode,
            outcome=attempt_outcome,
            reason=result.reason,
            resume_file=str(candidate.resume_file),
            attempted_at=attempted_at,
        ),
    )
    update_job_status(connection, candidate.job.id, status)
    if result.outcome != ApplicationOutcome.FAILED:
        replace_pending_questions(
            connection, candidate.job.id, build_pending_questions(candidate.job.id, result, attempted_at)
        )


def is_limit_reached(connection: sqlite3.Connection, config: Config, now: datetime) -> bool:
    return count_applied_on(connection, now.date()) >= config.regras.limite_diario


def run_applications(
    connection: sqlite3.Connection,
    config: Config,
    candidates: list[ApplicationCandidate],
    mode: ApplyMode,
    simulate: bool,
    apply: Callable[[ApplicationCandidate], ApplicationResult],
    wait: Callable[[], None],
    clock: Callable[[], datetime],
    show: Callable[[RunEntry], None],
) -> RunSummary:
    entries = []
    attempted = False
    for index, candidate in enumerate(candidates):
        if not simulate and is_limit_reached(connection, config, clock()):
            return RunSummary(entries=entries, limit_reached=True, not_attempted=len(candidates) - index)
        if has_applied(connection, candidate.job.id):
            already_applied = ApplicationResult(ApplicationOutcome.ALREADY_APPLIED, ALREADY_APPLIED_REASON, [])
            entry = RunEntry(candidate, already_applied)
        else:
            if attempted:
                wait()
            attempted = True
            result = apply(candidate)
            if not simulate:
                record_result(connection, candidate, mode, result, clock())
            entry = RunEntry(candidate, result)
        entries.append(entry)
        show(entry)
    return RunSummary(entries=entries, limit_reached=False, not_attempted=0)
