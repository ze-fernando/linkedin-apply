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
    PHONE = "telefone"
    PHONE_COUNTRY = "codigo_pais"
    UNKNOWN = "desconhecido"


class StepAction(StrEnum):
    NEXT = "avancar"
    REVIEW = "revisar"
    SUBMIT = "enviar"


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
