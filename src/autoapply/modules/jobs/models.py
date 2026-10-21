from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class JobStatus(StrEnum):
    COLLECTED = "coletada"
    IGNORED = "ignorada"
    EVALUATED = "avaliada"
    AWAITING_RESUME = "aguardando_cv"


@dataclass(frozen=True)
class Job:
    id: str
    title: str
    company: str
    location: str
    workplace: str | None
    posted: str | None
    description: str | None
    url: str
    search_term: str
    status: JobStatus
    discard_reason: str | None
    collected_at: datetime


@dataclass(frozen=True)
class JobCard:
    id: str
    title: str
    company: str
    location: str


@dataclass(frozen=True)
class JobDetail:
    title: str
    company: str
    location: str
    posted: str | None
    workplace: str | None
    description: str
    has_easy_apply: bool
