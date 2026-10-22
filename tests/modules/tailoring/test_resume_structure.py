from pathlib import Path

import pytest

from autoapply.modules.tailoring.models import (
    Bullet,
    EducationEntry,
    ExperienceEntry,
    ResumeDocument,
    ResumeStructureError,
    SkillLine,
    TextRun,
)
from autoapply.modules.tailoring.resume_structure import read_resume_document
from tests.fakes.resume_docx import build_resume_docx


def test_read_resume_document_reads_every_section_of_the_base_layout(tmp_path: Path) -> None:
    document = read_resume_document(build_resume_docx(tmp_path / "cv.docx"))

    assert document == ResumeDocument(
        name="Maria Teste da Silva",
        headline="Desenvolvedora Back-end Python  •  APIs REST  •  Automação",
        contact_lines=[
            "São Paulo – SP (remoto)  |  (11) 91234-5678  |  maria.teste@example.com",
            "linkedin.com/in/maria-teste  |  github.com/maria-teste",
        ],
        summary="Desenvolvedora back-end com foco em Python e APIs REST, com 3 anos de experiência.",
        experiences=[
            ExperienceEntry(
                title="Desenvolvedora Pleno",
                period="Jan 2025 – Atual",
                company="Empresa Alfa",
                company_detail="  •  fintech",
                bullets=[
                    Bullet(lead="Desenvolvo APIs", text=" em FastAPI com PostgreSQL."),
                    Bullet(lead="Automatizei relatórios", text=" com Python, reduzindo 2 horas por dia."),
                ],
            ),
            ExperienceEntry(
                title="Desenvolvedora Júnior",
                period="Mar 2023 – Dez 2024",
                company="Empresa Beta",
                company_detail="  •  software house",
                bullets=[Bullet(lead="Mantive sistemas", text=" em Django e React.")],
            ),
        ],
        education=[
            EducationEntry(
                course="Bacharelado em Ciência da Computação",
                period="Conclusão prevista: Dez 2027",
                institution="Universidade Teste  —  em andamento",
            )
        ],
        skill_lines=[
            SkillLine(label="Linguagens", items=["Python", "SQL", "JavaScript"]),
            SkillLine(label="Automação & IA", items=["n8n", "LLMs (Claude, OpenAI)", "Selenium"]),
        ],
        languages=[
            TextRun(text="Português: ", bold=True),
            TextRun(text="nativo   •   ", bold=False),
            TextRun(text="Inglês: ", bold=True),
            TextRun(text="intermediário", bold=False),
        ],
    )


def test_read_resume_document_rejects_an_unknown_section(tmp_path: Path) -> None:
    path = build_resume_docx(tmp_path / "cv.docx", extra_sections=["Certificações"])

    with pytest.raises(ResumeStructureError, match="seção desconhecida: 'Certificações'"):
        read_resume_document(path)


def test_read_resume_document_rejects_an_experience_without_period(tmp_path: Path) -> None:
    path = build_resume_docx(tmp_path / "cv.docx", period_separator=" ")

    with pytest.raises(ResumeStructureError, match="experiência sem período: 'Desenvolvedora Pleno Jan 2025 – Atual'"):
        read_resume_document(path)
