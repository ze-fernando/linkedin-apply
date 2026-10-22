import re
from pathlib import Path

from autoapply.modules.config.models import Config, ConfigError, ConfigIssue
from autoapply.shared.text import remove_accents

NON_WORD_PATTERN = re.compile(r"[^\w\s]")
WHITESPACE_PATTERN = re.compile(r"\s+")
ANSWERS_SECTION = "respostas padrao"
MISSING_ANSWERS_TABLE_ISSUE = ConfigIssue(
    line=None, field="respostas", problem="tabela de Respostas padrão não encontrada"
)


def normalize_question(question: str) -> str:
    without_punctuation = NON_WORD_PATTERN.sub(" ", remove_accents(question).lower())
    return WHITESPACE_PATTERN.sub(" ", without_punctuation).strip()


def find_answer(config: Config, question: str) -> str | None:
    return config.respostas.get(normalize_question(question))


def format_table_cell(text: str) -> str:
    return " ".join(text.replace("|", "/").split())


def find_last_answer_row(lines: list[str]) -> int | None:
    in_section = False
    last_row = None
    for index, line in enumerate(lines):
        if line.startswith("# "):
            in_section = normalize_question(line[2:]) == ANSWERS_SECTION
        elif in_section and line.strip().startswith("|"):
            last_row = index
    return last_row


def add_config_answer(config_path: Path, question: str, answer: str) -> None:
    lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)
    last_row = find_last_answer_row(lines)
    if last_row is None:
        raise ConfigError([MISSING_ANSWERS_TABLE_ISSUE])
    lines.insert(last_row + 1, f"| {format_table_cell(question)} | {format_table_cell(answer)} |\n")
    config_path.write_text("".join(lines), encoding="utf-8")
