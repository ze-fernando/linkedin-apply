from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from autoapply.modules.config.models import ProvedorLlm


@dataclass(frozen=True)
class TextRun:
    text: str
    bold: bool


@dataclass(frozen=True)
class Bullet:
    lead: str
    text: str


@dataclass(frozen=True)
class ExperienceEntry:
    title: str
    period: str
    company: str
    company_detail: str
    bullets: list[Bullet]


@dataclass(frozen=True)
class EducationEntry:
    course: str
    period: str
    institution: str


@dataclass(frozen=True)
class SkillLine:
    label: str
    items: list[str]


@dataclass(frozen=True)
class ResumeDocument:
    name: str
    headline: str
    contact_lines: list[str]
    summary: str
    experiences: list[ExperienceEntry]
    education: list[EducationEntry]
    skill_lines: list[SkillLine]
    languages: list[TextRun]


@dataclass(frozen=True)
class TailoringPlan:
    summary: str
    bullet_orders: list[list[int]]
    skill_line_order: list[int]
    skill_item_orders: list[list[int]]


class TailoringStatus(StrEnum):
    USED = "usado"
    DISCARDED = "descartado"


@dataclass(frozen=True)
class TailoringResult:
    status: TailoringStatus
    pdf_path: Path | None
    reason: str | None
    provider: ProvedorLlm | None
    model: str | None


@dataclass(frozen=True)
class TailoredResume:
    job_id: str
    base_resume: Path
    pdf_path: Path | None
    status: TailoringStatus
    reason: str | None
    provider: ProvedorLlm | None
    model: str | None
    created_at: datetime


class ResumeStructureError(Exception):
    pass
