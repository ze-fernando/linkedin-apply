from dataclasses import dataclass


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


class ResumeStructureError(Exception):
    pass
