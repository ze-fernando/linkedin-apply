from collections.abc import Callable
from pathlib import Path

import pytest

from autoapply.modules.config.loader import parse_config_data
from autoapply.modules.config.models import Config
from autoapply.modules.resumes.loader import load_resumes
from autoapply.modules.resumes.models import DefaultResumeUnreadable

LONG_EXPERIENCE = [f"Experiência {number}: desenvolvimento de APIs REST com Python e PostgreSQL." for number in range(8)]


def build_config(valid_data: dict[str, object], base_dir: Path) -> Config:
    return parse_config_data(valid_data, base_dir)


def test_load_resumes_returns_readable_resumes_with_config_metadata(
    valid_data: dict[str, object],
    base_dir: Path,
    build_docx: Callable[..., Path],
    build_text_pdf: Callable[[str, list[str]], Path],
) -> None:
    build_docx("cv_base/backend.docx", paragraphs=["Maria Teste", *LONG_EXPERIENCE])
    build_text_pdf("cv_base/dados.pdf", ["Maria Teste", *LONG_EXPERIENCE])

    backend, dados = load_resumes(build_config(valid_data, base_dir))

    assert (backend.name, backend.path, backend.is_default, backend.searches) == (
        "Back-end",
        base_dir / "cv_base/backend.docx",
        True,
        ["Desenvolvedor Python"],
    )
    assert backend.text.startswith("Maria Teste\nExperiência 0")
    assert backend.problem is None
    assert (dados.name, dados.is_default, dados.problem) == ("Dados", False, None)
    assert "Experiência 7" in dados.text


def test_load_resumes_flags_resume_with_insufficient_text(
    valid_data: dict[str, object],
    base_dir: Path,
    build_docx: Callable[..., Path],
    build_blank_pdf: Callable[[str], Path],
) -> None:
    build_docx("cv_base/backend.docx", paragraphs=["Maria Teste", *LONG_EXPERIENCE])
    build_blank_pdf("cv_base/dados.pdf")

    backend, dados = load_resumes(build_config(valid_data, base_dir))

    assert backend.problem is None
    assert dados.problem == "texto insuficiente (0 caracteres, mínimo 300): provável PDF escaneado"


def test_load_resumes_counts_characters_without_whitespace(
    valid_data: dict[str, object],
    base_dir: Path,
    build_docx: Callable[..., Path],
) -> None:
    build_docx("cv_base/backend.docx", paragraphs=["Maria Teste", *LONG_EXPERIENCE])
    build_docx("cv_base/dados.docx", paragraphs=["x " * 299, "   "])
    valid_data["curriculos"][1]["arquivo"] = "cv_base/dados.docx"

    _, dados = load_resumes(build_config(valid_data, base_dir))

    assert dados.problem == "texto insuficiente (299 caracteres, mínimo 300): provável PDF escaneado"


@pytest.mark.parametrize("corrupted_name", ["cv_base/dados.pdf", "cv_base/dados.docx"])
def test_load_resumes_flags_corrupted_file_with_reason(
    valid_data: dict[str, object],
    base_dir: Path,
    build_docx: Callable[..., Path],
    corrupted_name: str,
) -> None:
    build_docx("cv_base/backend.docx", paragraphs=["Maria Teste", *LONG_EXPERIENCE])
    (base_dir / corrupted_name).write_bytes(b"isto nao e um arquivo valido")
    valid_data["curriculos"][1]["arquivo"] = corrupted_name

    _, dados = load_resumes(build_config(valid_data, base_dir))

    assert dados.text == ""
    assert dados.problem is not None
    assert dados.problem.startswith("não foi possível ler o arquivo: ")


def test_load_resumes_fails_when_default_resume_is_unreadable(
    valid_data: dict[str, object],
    base_dir: Path,
    build_blank_pdf: Callable[[str], Path],
    build_text_pdf: Callable[[str, list[str]], Path],
) -> None:
    build_blank_pdf("cv_base/scan.pdf")
    build_text_pdf("cv_base/dados.pdf", ["Maria Teste", *LONG_EXPERIENCE])
    valid_data["curriculos"][0]["arquivo"] = "cv_base/scan.pdf"

    with pytest.raises(DefaultResumeUnreadable) as raised:
        load_resumes(build_config(valid_data, base_dir))

    assert str(raised.value) == (
        "currículo padrão 'Back-end' inválido: texto insuficiente (0 caracteres, mínimo 300): provável PDF escaneado"
    )
