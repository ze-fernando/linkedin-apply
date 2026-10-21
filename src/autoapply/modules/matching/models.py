from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from autoapply.modules.config.models import ProvedorLlm


class Analyzer(StrEnum):
    CLAUDE = "claude"
    OPENCODE = "opencode"
    KEYWORDS = "palavras_chave"


@dataclass(frozen=True)
class JobAnalysis:
    job_id: str
    resume_name: str
    score: int
    pre_score: int
    summary: str
    requirements: list[str]
    keywords: list[str]
    gap: list[str]
    analyzer: Analyzer
    model: str | None
    analyzed_at: datetime


@dataclass(frozen=True)
class ResumeMatch:
    resume_name: str
    pre_score: int
    job_terms: list[str]
    missing_terms: list[str]


@dataclass(frozen=True)
class LlmAnalysis:
    resume_name: str
    score: int
    summary: str
    requirements: list[str]
    keywords: list[str]
    gap: list[str]


class ProviderFailure(Exception):
    pass


@dataclass(frozen=True)
class ProviderAnalysis:
    provider: ProvedorLlm
    model: str
    analysis: LlmAnalysis


@dataclass
class ProviderRun:
    providers: list[ProvedorLlm]
    consecutive_failures: dict[ProvedorLlm, int] = field(default_factory=dict)
