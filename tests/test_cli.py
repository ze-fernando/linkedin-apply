import pytest
from typer.testing import CliRunner

from autoapply.main import app

TUTORIAL_STEPS = [
    "cp config.example.md config.md",
    "autoapply validate",
    "autoapply login",
    "autoapply run --simulate",
    "autoapply run",
    "autoapply pending",
    "--interactive",
]


def test_tutorial_prints_the_steps_in_order() -> None:
    result = CliRunner().invoke(app, ["--tutorial"])

    assert result.exit_code == 0
    positions = [result.output.index(step) for step in TUTORIAL_STEPS]
    assert positions == sorted(positions)


@pytest.mark.parametrize("arguments", [["-h"], ["run", "-h"]])
def test_short_help_option_works_like_help(arguments: list[str]) -> None:
    short = CliRunner().invoke(app, arguments, env={"COLUMNS": "200"})
    long = CliRunner().invoke(app, [*arguments[:-1], "--help"], env={"COLUMNS": "200"})

    assert short.exit_code == 0
    assert short.output == long.output


def test_run_help_lists_the_english_flags() -> None:
    result = CliRunner().invoke(app, ["run", "--help"], env={"COLUMNS": "200"})

    for flag in ["--auto", "--simulate", "--skip-collect", "--interactive", "--visible", "--config"]:
        assert flag in result.output


@pytest.mark.parametrize(
    "arguments", [["rodar", "--help"], ["run", "--simular", "--help"], ["apply", "--prontas", "--help"]]
)
def test_old_portuguese_names_are_usage_errors(arguments: list[str]) -> None:
    assert CliRunner().invoke(app, arguments).exit_code == 2


ROOT_EXAMPLES = [
    "autoapply run --simulate",
    "autoapply run --auto --interactive",
    "autoapply run --skip-collect --auto",
    "autoapply run --skip-collect --simulate",
    "autoapply apply <job> --auto --interactive",
    "autoapply apply --ready --auto",
    "autoapply search --visible",
    "autoapply jobs --status avaliada",
    "autoapply pending",
]
RUN_EXAMPLES = ["autoapply run --simulate", "autoapply run --auto --interactive", "autoapply run --skip-collect --auto"]
APPLY_EXAMPLES = ["autoapply apply <job> --simulate", "autoapply apply --ready --auto --interactive"]


@pytest.mark.parametrize(
    ("arguments", "examples"),
    [(["-h"], ROOT_EXAMPLES), (["run", "-h"], RUN_EXAMPLES), (["apply", "-h"], APPLY_EXAMPLES)],
    ids=["raiz", "run", "apply"],
)
def test_help_shows_examples_combining_the_flags(arguments: list[str], examples: list[str]) -> None:
    result = CliRunner().invoke(app, arguments, env={"COLUMNS": "200"})

    assert "Exemplos" in result.output
    for example in examples:
        assert example in result.output
