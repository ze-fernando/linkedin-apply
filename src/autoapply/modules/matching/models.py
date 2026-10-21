from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


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
