from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from autoapply.modules.config.models import Config
from autoapply.modules.jobs.models import Job


class ApplyMode(StrEnum):
    SEARCH = "busca"
    NORMAL = "normal"


class FieldKind(StrEnum):
    NUMBER = "numero"
    TEXT = "texto"
    FREE_TEXT = "texto_livre"
    SELECT = "select"
    RADIO = "radio"
    PHONE = "telefone"
    PHONE_COUNTRY = "codigo_pais"
    UNKNOWN = "desconhecido"


class StepAction(StrEnum):
    NEXT = "avancar"
    REVIEW = "revisar"
    SUBMIT = "enviar"


class DecisionAction(StrEnum):
    FILL = "preencher"
    KEEP = "manter"
    PENDING = "pendente"
    SKIP = "pular"
    FAIL = "falhar"


class AnswerSource(StrEnum):
    PROFILE = "perfil"
    JOB = "respostas.md"
    CONFIG = "config.md"
    RULE = "regra"
    LINKEDIN = "LinkedIn"
    GENERIC = "resposta genérica"


class AttemptOutcome(StrEnum):
    APPLIED = "aplicada"
    ALREADY_APPLIED = "ja_aplicada"
    PENDING = "pendente"
    FAILED = "falhou"


@dataclass(frozen=True)
class ApplicationAttempt:
    job_id: str
    mode: ApplyMode
    outcome: AttemptOutcome
    reason: str | None
    resume_file: str | None
    attempted_at: datetime


@dataclass(frozen=True)
class PendingQuestion:
    job_id: str
    question: str
    field_kind: FieldKind
    options: list[str]
    created_at: datetime


@dataclass(frozen=True)
class FormField:
    element_id: str
    kind: FieldKind
    label: str
    required: bool
    value: str | None
    options: list[str]


@dataclass(frozen=True)
class FormStep:
    title: str
    fields: list[FormField]
    has_resume_upload: bool
    has_follow_company: bool
    action: StepAction | None
    errors: list[str]


@dataclass(frozen=True)
class SalaryQuestion:
    is_pj: bool
    foreign_currency: bool


@dataclass(frozen=True)
class FieldDecision:
    action: DecisionAction
    value: str | None
    source: AnswerSource | None
    reason: str | None


@dataclass(frozen=True)
class AnswerContext:
    config: Config
    job_answers: dict[str, str]
    job_title: str


class ApplicationOutcome(StrEnum):
    APPLIED = "aplicada"
    ALREADY_APPLIED = "ja_aplicada"
    PENDING = "pendente"
    FAILED = "falhou"
    SIMULATED = "simulada"


@dataclass(frozen=True)
class ApplicationResult:
    outcome: ApplicationOutcome
    reason: str | None
    pending_fields: list[FormField]


@dataclass(frozen=True)
class FolderResume:
    path: Path | None
    problem: str | None


@dataclass(frozen=True)
class ApplicationCandidate:
    job: Job
    resume_file: Path
    job_answers: dict[str, str]
    score: int | None


@dataclass(frozen=True)
class RunEntry:
    candidate: ApplicationCandidate
    result: ApplicationResult


@dataclass(frozen=True)
class RunSummary:
    entries: list[RunEntry]
    limit_reached: bool
    not_attempted: int


@dataclass(frozen=True)
class FolderJob:
    job: Job
    folder: Path
    score: int | None
