from collections.abc import Callable

from autoapply.modules.jobs.models import JobCard, JobDetail
from autoapply.modules.jobs.parsing import parse_job_cards, parse_job_detail


def test_parse_job_cards_reads_rendered_cards_once(read_page: Callable[[str], str]) -> None:
    cards = parse_job_cards(read_page("search_list.html"))

    assert cards == [
        JobCard(id="1001", title="Desenvolvedor .NET Pleno", company="Empresa Alfa", location="São Paulo, São Paulo, Brasil (Remoto)"),
        JobCard(id="1002", title="Desenvolvedor C# Sênior", company="Empresa Beta", location="Brasil (Remoto)"),
    ]


def test_parse_job_detail_reads_panel_fields_and_description_lines(read_page: Callable[[str], str]) -> None:
    detail = parse_job_detail(read_page("job_panel.html"))

    assert detail == JobDetail(
        title="Desenvolvedor .NET Pleno",
        company="Empresa Alfa",
        location="São Paulo, São Paulo, Brasil",
        posted="há 5 dias",
        workplace="Remoto · Tempo integral",
        description=(
            "Sobre a vaga\n"
            "Buscamos pessoa desenvolvedora .NET.\n"
            "Requisitos:\n"
            "C# e ASP.NET Core\n"
            "SQL Server\n"
            "Benefícios\n"
            "Home office"
        ),
        has_easy_apply=True,
    )


def test_parse_job_detail_keeps_inline_formatting_on_the_same_line() -> None:
    html = '<div id="job-details"><p>Experiência com <strong>C#</strong> e <em>Azure</em>.</p><p>Remoto</p></div>'

    assert parse_job_detail(html).description == "Experiência com C# e Azure.\nRemoto"


def test_parse_job_detail_without_easy_apply_button_text(read_page: Callable[[str], str]) -> None:
    html = read_page("job_panel.html").replace("  Candidatura simplificada ", "Candidatar-se")

    assert parse_job_detail(html).has_easy_apply is False
