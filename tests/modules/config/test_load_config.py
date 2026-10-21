import copy
from collections.abc import Callable
from pathlib import Path

import pytest

from autoapply.modules.config.loader import load_config
from autoapply.modules.config.models import ConfigError, ConfigIssue


def line_number_of(config_path: Path, fragment: str) -> int:
    lines = config_path.read_text(encoding="utf-8").splitlines()
    return next(index for index, line in enumerate(lines, start=1) if fragment in line)


def collect_issues(config_path: Path) -> list[ConfigIssue]:
    with pytest.raises(ConfigError) as raised:
        load_config(config_path)
    return raised.value.issues


def test_load_config_reads_frontmatter_answers_table_and_generic_answer(
    valid_data: dict[str, object], base_dir: Path, write_config: Callable[..., Path]
) -> None:
    config = load_config(write_config(copy.deepcopy(valid_data)))

    assert config.perfil.nome == "Maria Teste da Silva"
    assert config.curriculos[0].arquivo == base_dir / "cv_base/backend.docx"
    assert config.respostas == {"aceita contratacao pj": "Sim", "nivel de ingles": "Intermediário"}
    assert config.resposta_generica == "Tenho interesse na vaga."


def test_load_config_reports_validation_error_with_field_line(
    valid_data: dict[str, object], write_config: Callable[..., Path]
) -> None:
    data = copy.deepcopy(valid_data)
    data["pretensao"]["pleno"]["pj"]["formulario"] = 9500
    config_path = write_config(data)

    issues = collect_issues(config_path)

    assert issues == [
        ConfigIssue(
            line=line_number_of(config_path, "formulario: 9500"),
            field="pretensao.pleno.pj.formulario",
            problem="Value error, deve estar entre min (7000) e max (9000)",
        )
    ]


def test_load_config_reports_yaml_syntax_error_with_line(
    valid_data: dict[str, object], write_config: Callable[..., Path]
) -> None:
    config_path = write_config(copy.deepcopy(valid_data))
    broken_text = config_path.read_text(encoding="utf-8").replace("cidade: São Paulo", "cidade: São: Paulo")
    config_path.write_text(broken_text, encoding="utf-8")

    [issue] = collect_issues(config_path)

    assert issue.line == line_number_of(config_path, "cidade: São: Paulo")
    assert issue.field == "yaml"
    assert "mapping values are not allowed here" in issue.problem


@pytest.mark.parametrize("text", ["# Só markdown\n", "---\nperfil:\n  nome: Maria\n"])
def test_load_config_reports_missing_frontmatter(base_dir: Path, text: str) -> None:
    config_path = base_dir / "config.md"
    config_path.write_text(text, encoding="utf-8")

    issues = collect_issues(config_path)

    assert issues == [
        ConfigIssue(line=1, field="frontmatter", problem="o arquivo deve começar com um bloco YAML entre linhas ---")
    ]


def test_load_config_reports_duplicated_question_after_normalization(
    valid_data: dict[str, object], write_config: Callable[..., Path]
) -> None:
    body = """
# Respostas padrão

| Pergunta | Resposta |
| --- | --- |
| Aceita PJ? | Sim |
| aceita pj | Não |

# Resposta genérica

> Tenho interesse na vaga.
"""
    config_path = write_config(copy.deepcopy(valid_data), body)

    issues = collect_issues(config_path)

    assert issues == [
        ConfigIssue(
            line=line_number_of(config_path, "| aceita pj | Não |"),
            field="respostas",
            problem="pergunta repetida (igual após normalizar): aceita pj",
        )
    ]


def test_load_config_points_empty_generic_answer_to_its_heading(
    valid_data: dict[str, object], write_config: Callable[..., Path]
) -> None:
    body = "\n# Resposta genérica\n\nTexto fora do blockquote.\n"
    config_path = write_config(copy.deepcopy(valid_data), body)

    issues = collect_issues(config_path)

    assert issues == [
        ConfigIssue(
            line=line_number_of(config_path, "# Resposta genérica"),
            field="resposta_generica",
            problem="Value error, não pode ficar vazia",
        )
    ]


def test_load_config_reports_missing_generic_answer_section_without_line(
    valid_data: dict[str, object], write_config: Callable[..., Path]
) -> None:
    config_path = write_config(copy.deepcopy(valid_data), "\n# Respostas padrão\n")

    issues = collect_issues(config_path)

    assert issues == [ConfigIssue(line=None, field="resposta_generica", problem="Value error, não pode ficar vazia")]


def test_load_config_reports_body_and_frontmatter_issues_together(
    valid_data: dict[str, object], write_config: Callable[..., Path]
) -> None:
    data = copy.deepcopy(valid_data)
    data["regras"]["limite_diario"] = 0
    body = """
# Respostas padrão

| Pergunta | Resposta |
| --- | --- |
| Aceita PJ? | Sim |
| Aceita PJ | Sim |

# Resposta genérica

> Tenho interesse na vaga.
"""
    config_path = write_config(data, body)

    issues = collect_issues(config_path)

    assert [issue.field for issue in issues] == ["respostas", "regras.limite_diario"]


@pytest.mark.parametrize("frontmatter", ["", "- só\n- uma lista\n"])
def test_load_config_reports_frontmatter_that_is_not_a_mapping(base_dir: Path, frontmatter: str) -> None:
    config_path = base_dir / "config.md"
    config_path.write_text(f"---\n{frontmatter}---\n", encoding="utf-8")

    issues = collect_issues(config_path)

    assert issues == [
        ConfigIssue(line=2, field="frontmatter", problem="o bloco YAML deve ter os campos do config (chave: valor)")
    ]
