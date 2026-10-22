from collections.abc import Callable
from pathlib import Path

from autoapply.modules.config.answers import add_config_answer, find_answer
from autoapply.modules.config.loader import load_config

LEVEL_QUESTION = "Qual o nível de proficiência em inglês? (1 Básico | 2 Intermediário | 3 Avançado)"


def test_add_config_answer_appends_a_row_to_the_answers_table(
    write_config: Callable[..., Path], valid_data: dict[str, object]
) -> None:
    config_path = write_config(valid_data)
    before = config_path.read_text(encoding="utf-8")

    add_config_answer(config_path, "Possui CNH?", "Sim")
    add_config_answer(config_path, LEVEL_QUESTION, "2")

    config = load_config(config_path)
    assert find_answer(config, "possui cnh") == "Sim"
    assert find_answer(config, LEVEL_QUESTION) == "2"
    assert find_answer(config, "Aceita contratação PJ?") == "Sim"
    assert config.resposta_generica == "Tenho interesse na vaga."
    assert config_path.read_text(encoding="utf-8") == before.replace(
        "| Nível de inglês | Intermediário |\n",
        "| Nível de inglês | Intermediário |\n"
        "| Possui CNH? | Sim |\n"
        "| Qual o nível de proficiência em inglês? (1 Básico / 2 Intermediário / 3 Avançado) | 2 |\n",
    )
