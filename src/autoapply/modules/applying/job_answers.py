from pathlib import Path

from autoapply.modules.config.loader import parse_answers_table
from autoapply.modules.config.models import ConfigError, MarkdownSection

JOB_ANSWERS_FILE = "respostas.md"


def load_job_answers(folder: Path) -> dict[str, str]:
    answers_path = folder / JOB_ANSWERS_FILE
    if not answers_path.is_file():
        return {}
    lines = list(enumerate(answers_path.read_text(encoding="utf-8").splitlines(), start=1))
    parsed = parse_answers_table(MarkdownSection(heading_line=1, lines=lines))
    if parsed.issues:
        raise ConfigError(parsed.issues)
    return parsed.answers
