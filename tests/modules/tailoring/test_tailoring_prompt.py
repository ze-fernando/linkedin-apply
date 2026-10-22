import dataclasses
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from autoapply.modules.jobs.models import Job
from autoapply.modules.matching.models import Analyzer, JobAnalysis
from autoapply.modules.tailoring.prompt import build_tailoring_prompt
from autoapply.modules.tailoring.resume_structure import read_resume_document
from tests.fakes.resume_docx import build_resume_docx

ANALYSIS = JobAnalysis(
    job_id="4481248162",
    resume_name="Back-end",
    score=80,
    pre_score=70,
    summary="Boa aderência.",
    requirements=["Python", "Kubernetes"],
    keywords=["Python"],
    gap=["Kubernetes"],
    analyzer=Analyzer.OPENCODE,
    model="opencode/deepseek-v4.1-flash-free",
    analyzed_at=datetime(2026, 10, 22, 9, 0),
)


def test_build_tailoring_prompt_numbers_what_can_be_reordered_and_leaves_out_the_header(
    tmp_path: Path, build_job: Callable[..., Job]
) -> None:
    base = read_resume_document(build_resume_docx(tmp_path / "cv.docx"))
    document = dataclasses.replace(
        base, summary=f"{base.summary} Contato: maria.teste@example.com ou (11) 91234-5678."
    )
    job = build_job(title="Desenvolvedora Python", description="Vaga para Python e Kubernetes.")

    prompt = build_tailoring_prompt(document, job, ANALYSIS)

    for expected in [
        "Desenvolvedora Python",
        "Vaga para Python e Kubernetes.",
        "Requisitos: Python, Kubernetes",
        "Gap: Kubernetes",
        "Desenvolvedora back-end com foco em Python e APIs REST, com 3 anos de experiência.",
        "Contato: [email] ou [telefone].",
        "Experiência 0 (2 bullets): Desenvolvedora Pleno (Jan 2025 – Atual)",
        "[0] Desenvolvo APIs em FastAPI com PostgreSQL.",
        "[1] Automatizei relatórios com Python, reduzindo 2 horas por dia.",
        "Experiência 1 (1 bullets): Desenvolvedora Júnior (Mar 2023 – Dez 2024)",
        "Linha 1: Automação & IA: [0] n8n | [1] LLMs (Claude, OpenAI) | [2] Selenium",
    ]:
        assert expected in prompt
    for header in ["Maria Teste da Silva", "maria.teste@example.com", "91234-5678", "linkedin.com", "github.com"]:
        assert header not in prompt
