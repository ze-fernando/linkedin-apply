from dataclasses import dataclass
from datetime import datetime

from autoapply.modules.applying.models import ApplyMode, AttemptOutcome


@dataclass(frozen=True)
class ReportEntry:
    job_id: str
    attempted_at: datetime
    mode: ApplyMode
    outcome: AttemptOutcome
    company: str
    title: str
    score: int | None
    resume_file: str | None
    tailored: bool
    url: str


@dataclass(frozen=True)
class Report:
    counts: dict[tuple[ApplyMode, AttemptOutcome], int]
    ignored: int
    completion_rate: float | None
    failure_reasons: list[tuple[str, int]]
    entries: list[ReportEntry]
