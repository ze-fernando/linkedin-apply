from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Resume:
    name: str
    path: Path
    is_default: bool
    searches: list[str]
    text: str
    problem: str | None


class DefaultResumeUnreadable(Exception):
    pass
