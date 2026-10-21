from pathlib import Path

import pytest

from autoapply.modules.config.answers import find_answer, normalize_question
from autoapply.modules.config.loader import parse_config_data


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Aceita contratação PJ?", "aceita contratacao pj"),
        ("  Nível de   inglês  ", "nivel de ingles"),
        ("Possui deficiência (PcD)?", "possui deficiencia pcd"),
        ("Disponibilidade para início / viagens", "disponibilidade para inicio viagens"),
    ],
)
def test_normalize_question_removes_case_accents_punctuation_and_extra_spaces(
    question: str, expected: str
) -> None:
    assert normalize_question(question) == expected


def test_find_answer_matches_question_written_differently(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    config = parse_config_data(valid_data, base_dir)

    assert find_answer(config, "  ACEITA PJ ? ") == "Sim"


def test_find_answer_returns_none_for_unknown_question(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    config = parse_config_data(valid_data, base_dir)

    assert find_answer(config, "Possui CNH categoria B?") is None
