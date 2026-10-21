from pathlib import Path

import pytest

from autoapply.modules.applying.job_answers import load_job_answers
from autoapply.modules.config.models import ConfigError

ANSWERS_FILE = """# Respostas desta vaga

Respostas usadas só nesta vaga.

| Pergunta | Resposta |
| -------- | -------- |
| Você aceita contratação PJ? | Sim |
| Pretensão salarial | 7500 |
| Mensagem | Gostei muito do produto de vocês. |
"""


def test_load_job_answers_without_file_is_empty(tmp_path: Path) -> None:
    assert load_job_answers(tmp_path) == {}


def test_load_job_answers_reads_table_with_normalized_questions(tmp_path: Path) -> None:
    (tmp_path / "respostas.md").write_text(ANSWERS_FILE, encoding="utf-8")

    assert load_job_answers(tmp_path) == {
        "voce aceita contratacao pj": "Sim",
        "pretensao salarial": "7500",
        "mensagem": "Gostei muito do produto de vocês.",
    }


def test_load_job_answers_reports_repeated_question_with_line(tmp_path: Path) -> None:
    (tmp_path / "respostas.md").write_text(ANSWERS_FILE + "| Mensagem! | Outra |\n", encoding="utf-8")

    with pytest.raises(ConfigError) as error:
        load_job_answers(tmp_path)

    assert [(issue.line, issue.field) for issue in error.value.issues] == [(10, "respostas")]
