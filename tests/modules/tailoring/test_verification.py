import dataclasses
from pathlib import Path

import pytest

from autoapply.modules.tailoring.models import ResumeDocument
from autoapply.modules.tailoring.resume_structure import read_resume_document
from autoapply.modules.tailoring.verification import find_new_information
from tests.fakes.resume_docx import build_resume_docx

VOCABULARY = ["Python", "FastAPI", "PostgreSQL", "Django", "React", "Kubernetes", "Go"]


@pytest.fixture
def base_document(tmp_path: Path) -> ResumeDocument:
    return read_resume_document(build_resume_docx(tmp_path / "cv.docx"))


def test_find_new_information_accepts_a_summary_built_only_from_the_base_resume(
    base_document: ResumeDocument,
) -> None:
    summary = (
        "Desenvolvedora Pleno, 3 anos em Python, FastAPI e PostgreSQL. "
        "Na Empresa Alfa reduzi 2 horas por dia; usei Django e React."
    )

    assert find_new_information(base_document, dataclasses.replace(base_document, summary=summary), VOCABULARY) is None


@pytest.mark.parametrize(
    ("summary", "reason"),
    [
        ("   ", "resumo vazio"),
        ("Python " * 30, "resumo com 209 caracteres passa do dobro do original (82)"),
        ("Desenvolvedora com Python e kubernetes.", "resumo cita tecnologia que não está no currículo: Kubernetes"),
        ("Desenvolvedora com 5 anos de experiência.", "resumo cita número que não está no currículo: 5"),
        ("Reduzi 40% do tempo de deploy.", "resumo cita número que não está no currículo: 40"),
        ("Desenvolvedora certificada pela Oracle em APIs.", "resumo cita nome que não está no currículo: Oracle"),
        ("Atuei como Tech Lead na Empresa Alfa.", "resumo cita nome que não está no currículo: Tech"),
    ],
    ids=["vazio", "longo", "tecnologia", "anos", "porcentagem", "certificacao", "cargo"],
)
def test_find_new_information_returns_the_reason_when_the_summary_brings_something_new(
    base_document: ResumeDocument, summary: str, reason: str
) -> None:
    tailored = dataclasses.replace(base_document, summary=summary)

    assert find_new_information(base_document, tailored, VOCABULARY) == reason


def test_find_new_information_ignores_capitalized_words_at_the_start_of_a_sentence(
    base_document: ResumeDocument,
) -> None:
    summary = "Atuo com Python. Construo APIs REST! Reduzi tempo manual com automação."

    assert find_new_information(base_document, dataclasses.replace(base_document, summary=summary), VOCABULARY) is None
