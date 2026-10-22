import dataclasses
from pathlib import Path

import pytest

from autoapply.modules.tailoring.models import Bullet, ResumeDocument, SkillLine, TailoringPlan
from autoapply.modules.tailoring.plan import apply_tailoring_plan
from autoapply.modules.tailoring.resume_structure import read_resume_document
from tests.fakes.resume_docx import build_resume_docx

VALID_PLAN = TailoringPlan(
    summary="Desenvolvedora back-end Python com 3 anos de experiência em APIs REST.",
    bullet_orders=[[1, 0], [0]],
    skill_line_order=[1, 0],
    skill_item_orders=[[2, 0, 1], [1, 2, 0]],
)


@pytest.fixture
def base_document(tmp_path: Path) -> ResumeDocument:
    return read_resume_document(build_resume_docx(tmp_path / "cv.docx"))


def test_apply_tailoring_plan_replaces_the_summary_and_reorders_bullets_and_skills(
    base_document: ResumeDocument,
) -> None:
    tailored = apply_tailoring_plan(base_document, VALID_PLAN)

    assert tailored == dataclasses.replace(
        base_document,
        summary="Desenvolvedora back-end Python com 3 anos de experiência em APIs REST.",
        experiences=[
            dataclasses.replace(
                base_document.experiences[0],
                bullets=[
                    Bullet(lead="Automatizei relatórios", text=" com Python, reduzindo 2 horas por dia."),
                    Bullet(lead="Desenvolvo APIs", text=" em FastAPI com PostgreSQL."),
                ],
            ),
            base_document.experiences[1],
        ],
        skill_lines=[
            SkillLine(label="Automação & IA", items=["LLMs (Claude, OpenAI)", "Selenium", "n8n"]),
            SkillLine(label="Linguagens", items=["JavaScript", "Python", "SQL"]),
        ],
    )


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"bullet_orders": [[0, 0], [0]]}, "ordem dos bullets da experiência 0 não é permutação: [0, 0]"),
        ({"bullet_orders": [[1], [0]]}, "ordem dos bullets da experiência 0 não é permutação: [1]"),
        ({"bullet_orders": [[1, 0], [1]]}, "ordem dos bullets da experiência 1 não é permutação: [1]"),
        ({"bullet_orders": [[1, 0]]}, "ordem dos bullets tem 1 experiências, o currículo tem 2"),
        ({"skill_line_order": [0, 2]}, "ordem das competências não é permutação: [0, 2]"),
        ({"skill_item_orders": [[2, 0, 1]]}, "ordem dos itens tem 1 linhas, o currículo tem 2"),
        ({"skill_item_orders": [[2, 0, 1], [0, 1, 3]]}, "ordem dos itens da linha 1 não é permutação: [0, 1, 3]"),
    ],
    ids=["repetido", "faltando", "fora_da_faixa", "experiencia_faltando", "linhas", "linha_faltando", "itens"],
)
def test_apply_tailoring_plan_returns_the_reason_when_an_order_is_not_an_exact_permutation(
    base_document: ResumeDocument, changes: dict[str, object], reason: str
) -> None:
    assert apply_tailoring_plan(base_document, dataclasses.replace(VALID_PLAN, **changes)) == reason
