from collections.abc import Callable
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext
from pypdf import PdfReader

from autoapply.modules.jobs.models import Job
from autoapply.modules.matching.models import ProviderAnswer
from autoapply.modules.tailoring.models import TailoringPlan, TailoringResult, TailoringStatus
from autoapply.modules.tailoring.pdf import render_resume_pdf
from autoapply.modules.tailoring.tailor import tailor_resume
from tests.fakes.resume_docx import build_resume_docx
from tests.modules.tailoring.test_tailoring_prompt import ANALYSIS

VOCABULARY = ["Python", "FastAPI", "PostgreSQL", "Django", "React", "Kubernetes"]
MODEL = "opencode/deepseek-v4.1-flash-free"


def build_plan(summary: str) -> TailoringPlan:
    return TailoringPlan(
        summary=summary,
        bullet_orders=[[1, 0], [0]],
        skill_line_order=[1, 0],
        skill_item_orders=[[0, 1, 2], [2, 1, 0]],
    )


def fail_render(html: str, path: Path) -> Path:
    raise AssertionError("não deveria gerar PDF")


def test_tailor_resume_renders_the_adjusted_pdf_when_the_plan_passes_the_checks(
    browser_context: BrowserContext,
    serve_pages: Callable[[dict[str, str]], None],
    build_job: Callable[..., Job],
    tmp_path: Path,
) -> None:
    serve_pages({})
    prompts = []
    plan = build_plan("Desenvolvedora Python focada em automação de relatórios e APIs com FastAPI.")

    def ask(prompt: str) -> ProviderAnswer[TailoringPlan]:
        prompts.append(prompt)
        return ProviderAnswer(provider="opencode", model=MODEL, value=plan)

    def render(html: str, path: Path) -> Path:
        return render_resume_pdf(browser_context, html, path)

    pdf_path = tmp_path / "curriculos-enviados" / "2026-10-22-empresa-teste-dev.pdf"

    result = tailor_resume(
        build_resume_docx(tmp_path / "cv.docx"), build_job(), ANALYSIS, VOCABULARY, ask, render, pdf_path
    )

    assert result == TailoringResult(
        status=TailoringStatus.USED, pdf_path=pdf_path, reason=None, provider="opencode", model=MODEL
    )
    text = " ".join((page.extract_text() or "") for page in PdfReader(pdf_path).pages).casefold()
    assert "focada em automação de relatórios" in text
    assert text.index("automatizei relatórios") < text.index("desenvolvo apis")
    assert len(prompts) == 1 and "Maria Teste da Silva" not in prompts[0]


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (
            ProviderAnswer(provider="opencode", model=MODEL, value=build_plan("Desenvolvedora Python e Kubernetes.")),
            TailoringResult(
                status=TailoringStatus.DISCARDED,
                pdf_path=None,
                reason="resumo cita tecnologia que não está no currículo: Kubernetes",
                provider="opencode",
                model=MODEL,
            ),
        ),
        (
            ProviderAnswer(
                provider="opencode",
                model=MODEL,
                value=TailoringPlan(
                    summary="Desenvolvedora Python.",
                    bullet_orders=[[0, 0], [0]],
                    skill_line_order=[1, 0],
                    skill_item_orders=[[0, 1, 2], [2, 1, 0]],
                ),
            ),
            TailoringResult(
                status=TailoringStatus.DISCARDED,
                pdf_path=None,
                reason="ordem dos bullets da experiência 0 não é permutação: [0, 0]",
                provider="opencode",
                model=MODEL,
            ),
        ),
        (
            None,
            TailoringResult(
                status=TailoringStatus.DISCARDED,
                pdf_path=None,
                reason="nenhum provedor de LLM respondeu",
                provider=None,
                model=None,
            ),
        ),
    ],
    ids=["tecnologia_nova", "ordem_invalida", "sem_provedor"],
)
def test_tailor_resume_falls_back_to_the_base_resume_with_the_reason(
    build_job: Callable[..., Job],
    tmp_path: Path,
    answer: ProviderAnswer[TailoringPlan] | None,
    expected: TailoringResult,
) -> None:
    result = tailor_resume(
        build_resume_docx(tmp_path / "cv.docx"),
        build_job(),
        ANALYSIS,
        VOCABULARY,
        lambda prompt: answer,
        fail_render,
        tmp_path / "cv.pdf",
    )

    assert result == expected
