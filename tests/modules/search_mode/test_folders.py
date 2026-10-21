from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from autoapply.modules.jobs.models import Job
from autoapply.modules.matching.models import Analyzer, JobAnalysis
from autoapply.modules.search_mode.folders import build_folder_name, render_job_markdown

TODAY = date(2026, 10, 21)


def test_build_folder_name_uses_date_company_and_title_as_slug(build_job: Callable[..., Job], tmp_path: Path) -> None:
    job = build_job(company="Empresa Ágil S/A", title="Desenvolvedor .NET Pleno (Remoto)")

    assert build_folder_name(job, TODAY, tmp_path) == "2026-10-21-empresa-agil-s-a-desenvolvedor-net-pleno-remoto"


def test_build_folder_name_is_cut_to_sixty_characters(build_job: Callable[..., Job], tmp_path: Path) -> None:
    job = build_job(company="Empresa Teste", title="Desenvolvedor Back-end Sênior de Integrações Financeiras")

    assert build_folder_name(job, TODAY, tmp_path) == "2026-10-21-empresa-teste-desenvolvedor-back-end-senior-de-in"


def test_build_folder_name_appends_job_id_when_folder_already_exists(
    build_job: Callable[..., Job], tmp_path: Path
) -> None:
    job = build_job(id="4481248162", company="Empresa Teste", title="Desenvolvedor Back-end Sênior de Integrações Financeiras")
    (tmp_path / "2026-10-21-empresa-teste-desenvolvedor-back-end-senior-de-in").mkdir()

    assert build_folder_name(job, TODAY, tmp_path) == "2026-10-21-empresa-teste-desenvolvedor-back-end-s-4481248162"


def build_analysis(**overrides: object) -> JobAnalysis:
    fields = {
        "job_id": "4481248162",
        "resume_name": "Back-end",
        "score": 82,
        "pre_score": 60,
        "summary": "Boa aderência em C#.",
        "requirements": ["C#", "Azure"],
        "keywords": ["C#"],
        "gap": ["Azure"],
        "analyzer": Analyzer.CLAUDE,
        "model": "sonnet",
        "analyzed_at": datetime(2026, 10, 21, 16, 0, 0),
    }
    return JobAnalysis(**{**fields, **overrides})


def test_render_job_markdown_shows_llm_analysis_and_full_description(build_job: Callable[..., Job]) -> None:
    markdown = render_job_markdown(build_job(), build_analysis(), "cv_base/backend.docx", 70)

    assert markdown == (
        "# Desenvolvedor .NET Pleno — Empresa Teste\n"
        "\n"
        "- **Link:** https://www.linkedin.com/jobs/view/4481248162/\n"
        "- **Local:** Brasil (Remoto) · Remoto · Tempo integral · há 1 dia\n"
        "- **Score:** 82/100 · **Currículo sugerido:** Back-end (`cv_base/backend.docx`)\n"
        "- **Análise:** claude (sonnet)\n"
        "\n"
        "## Resumo\n"
        "\n"
        "Boa aderência em C#.\n"
        "\n"
        "## Requisitos\n"
        "\n"
        "- C#\n"
        "- Azure\n"
        "\n"
        "## Palavras-chave\n"
        "\n"
        "- C#\n"
        "\n"
        "## Gap (a vaga pede e o currículo não mostra)\n"
        "\n"
        "- Azure\n"
        "\n"
        "## Descrição completa\n"
        "\n"
        "Vaga para C# e ASP.NET Core.\n"
        "\n"
        "---\n"
        "Salve o currículo adaptado nesta pasta como `cv.docx` ou `cv.pdf`.\n"
    )


def test_render_job_markdown_warns_about_simplified_analysis_and_low_score(build_job: Callable[..., Job]) -> None:
    analysis = build_analysis(score=40, analyzer=Analyzer.KEYWORDS, model=None, gap=[])

    markdown = render_job_markdown(build_job(workplace=None, posted=None), analysis, "cv_base/backend.docx", 70)

    assert "- **Local:** Brasil (Remoto)\n" in markdown
    assert "- **Análise:** palavras-chave\n" in markdown
    assert "> **Aviso:** análise simplificada por palavras-chave (sem LLM)." in markdown
    assert "> **Aviso:** score 40 abaixo do mínimo configurado (70)." in markdown
    assert "## Gap (a vaga pede e o currículo não mostra)\n\n- (nenhum)\n" in markdown
