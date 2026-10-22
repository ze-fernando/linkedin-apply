from collections.abc import Callable
from pathlib import Path

from typer.testing import CliRunner

from autoapply.main import app
from autoapply.modules.jobs.models import Job
from autoapply.shared.database import open_database
from autoapply.shared.paths import DATABASE_FILE
from tests.modules.reporting.test_report import CITY_FAILURE, fill_history


def test_report_shows_summary_rate_reasons_and_list_and_exports_csv(build_job: Callable[..., Job]) -> None:
    with open_database(DATABASE_FILE) as connection:
        fill_history(connection, build_job)

    result = CliRunner().invoke(app, ["report", "--days", "0", "--csv", "saida.csv"], env={"COLUMNS": "250"})

    assert result.exit_code == 0
    for expected in [
        "todo o histórico",
        "Vagas ignoradas: 2",
        "Taxa de conclusão: 22% (2 de 9)",
        f"2× {CITY_FAILURE}",
        "Empresa e",
        "ajustado",
        "https://www.linkedin.com/jobs/view/e/",
        "saida.csv",
    ]:
        assert expected in result.output
    assert len(Path("saida.csv").read_text(encoding="utf-8-sig").splitlines()) == 9


def test_report_without_attempts_says_so() -> None:
    result = CliRunner().invoke(app, ["report"], env={"COLUMNS": "250"})

    assert result.exit_code == 0
    assert "últimos 7 dias" in result.output
    assert "Nenhuma candidatura no período." in result.output
