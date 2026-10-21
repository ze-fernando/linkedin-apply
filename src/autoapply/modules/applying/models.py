from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ApplyMode(StrEnum):
    SEARCH = "busca"
    NORMAL = "normal"


class FieldKind(StrEnum):
    NUMBER = "numero"
    TEXT = "texto"
    FREE_TEXT = "texto_livre"
    SELECT = "select"
    RADIO = "radio"


class AttemptOutcome(StrEnum):
    APPLIED = "aplicada"
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
