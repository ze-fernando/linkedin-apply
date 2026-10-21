import copy
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from autoapply.main import app

LONG_EXPERIENCE = [f"Experiência {number}: APIs REST com Python e PostgreSQL em produção." for number in range(8)]


@pytest.fixture
def readable_resumes(
    build_docx: Callable[..., Path], build_text_pdf: Callable[[str, list[str]], Path]
) -> None:
    build_docx("cv_base/backend.docx", paragraphs=["Maria Teste", *LONG_EXPERIENCE])
    build_text_pdf("cv_base/dados.pdf", ["Maria Teste", *LONG_EXPERIENCE])


def run_validate(base_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Result:
    monkeypatch.chdir(base_dir)
    return CliRunner().invoke(app, ["validar"])


def test_validate_shows_summary_and_exits_zero_when_everything_is_valid(
    valid_data: dict[str, object],
    base_dir: Path,
    write_config: Callable[..., Path],
    readable_resumes: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_config(copy.deepcopy(valid_data))

    result = run_validate(base_dir, monkeypatch)

    assert result.exit_code == 0, result.output
    for expected in [
        "Maria Teste da Silva",
        "maria.teste@example.com",
        "+55 11 91234-5678",
        "junior, pleno",
        "CLT, PJ",
        "Back-end",
        "Dados",
        "2 respostas padrão",
        "resposta genérica: ok",
        "config.md válido",
    ]:
        assert expected in result.output


def test_validate_lists_config_issues_and_exits_two(
    valid_data: dict[str, object],
    base_dir: Path,
    write_config: Callable[..., Path],
    readable_resumes: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = copy.deepcopy(valid_data)
    data["regras"]["limite_diario"] = 0
    data["perfil"]["telefone"] = "11 91234-5678"
    config_path = write_config(data)
    lines = config_path.read_text(encoding="utf-8").splitlines()
    limit_line = next(number for number, line in enumerate(lines, start=1) if "limite_diario: 0" in line)

    result = run_validate(base_dir, monkeypatch)

    assert result.exit_code == 2, result.output
    assert "config.md inválido (2 erros)" in result.output
    assert "regras.limite_diario" in result.output
    assert str(limit_line) in result.output
    assert "perfil.telefone" in result.output
    assert "deve começar com +55" in result.output


def test_validate_warns_about_unreadable_secondary_resume_and_exits_zero(
    valid_data: dict[str, object],
    base_dir: Path,
    write_config: Callable[..., Path],
    build_docx: Callable[..., Path],
    build_blank_pdf: Callable[[str], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_docx("cv_base/backend.docx", paragraphs=["Maria Teste", *LONG_EXPERIENCE])
    build_blank_pdf("cv_base/dados.pdf")
    write_config(copy.deepcopy(valid_data))

    result = run_validate(base_dir, monkeypatch)

    assert result.exit_code == 0, result.output
    assert "texto insuficiente" in result.output
    assert "1 currículo ignorado" in result.output


def test_validate_fails_with_exit_two_when_default_resume_is_unreadable(
    valid_data: dict[str, object],
    base_dir: Path,
    write_config: Callable[..., Path],
    build_blank_pdf: Callable[[str], Path],
    build_text_pdf: Callable[[str, list[str]], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_blank_pdf("cv_base/scan.pdf")
    build_text_pdf("cv_base/dados.pdf", ["Maria Teste", *LONG_EXPERIENCE])
    data = copy.deepcopy(valid_data)
    data["curriculos"][0]["arquivo"] = "cv_base/scan.pdf"
    write_config(data)

    result = run_validate(base_dir, monkeypatch)

    assert result.exit_code == 2, result.output
    assert "currículo padrão 'Back-end' inválido" in result.output
    assert "Traceback" not in result.output


def test_validate_reports_missing_config_file_and_exits_two(base_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = run_validate(base_dir, monkeypatch)

    assert result.exit_code == 2, result.output
    assert "config.md não encontrado" in result.output
    assert "Traceback" not in result.output


@pytest.fixture
def fake_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[list[str]], None]:
    def install(executables: list[str]) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir(exist_ok=True)
        for name in executables:
            executable = bin_dir / name
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
        monkeypatch.setenv("PATH", str(bin_dir))

    return install


def test_validate_shows_llm_providers_with_availability(
    valid_data: dict[str, object],
    base_dir: Path,
    write_config: Callable[..., Path],
    readable_resumes: None,
    fake_path: Callable[[list[str]], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_path(["claude"])
    write_config(copy.deepcopy(valid_data))

    result = run_validate(base_dir, monkeypatch)

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert any("claude" in line and "sonnet" in line and "disponível" in line for line in lines), result.output
    assert any("opencode" in line and "ollama/qwen3" in line and "não encontrado" in line for line in lines), result.output


def test_validate_marks_opencode_without_model_as_unusable(
    valid_data: dict[str, object],
    base_dir: Path,
    write_config: Callable[..., Path],
    readable_resumes: None,
    fake_path: Callable[[list[str]], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_path(["claude", "opencode"])
    data = copy.deepcopy(valid_data)
    data["llm"]["opencode"] = {}
    write_config(data)

    result = run_validate(base_dir, monkeypatch)

    assert result.exit_code == 0, result.output
    assert any("opencode" in line and "sem modelo" in line for line in result.output.splitlines()), result.output
