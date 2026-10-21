from pathlib import Path

import typer
from rich.table import Table

from autoapply.modules.config.commands import load_valid_config
from autoapply.modules.jobs.collector import collect_jobs
from autoapply.modules.jobs.models import TermSummary
from autoapply.modules.jobs.search_url import collect_search_terms
from autoapply.modules.session.commands import logged_in_browser
from autoapply.shared.console import console
from autoapply.shared.database import open_database
from autoapply.shared.pacing import pause_between_actions
from autoapply.shared.paths import CONFIG_FILE, DATABASE_FILE, DEBUG_DIR


def build_summary_table(summaries: list[TermSummary]) -> Table:
    table = Table(title="Coleta")
    for column in ["Termo", "Encontradas", "Novas", "Ignoradas"]:
        table.add_column(column)
    for summary in summaries:
        table.add_row(summary.term, str(summary.found), str(summary.new), str(summary.ignored))
    table.add_row(
        "[bold]Total[/]",
        str(sum(summary.found for summary in summaries)),
        str(sum(summary.new for summary in summaries)),
        str(sum(summary.ignored for summary in summaries)),
    )
    return table


def collect(
    visible: bool = typer.Option(False, "--visivel", help="Abre o navegador visível."),
    config_path: Path = typer.Option(CONFIG_FILE, "--config", help="Caminho do config.md."),
) -> None:
    config = load_valid_config(config_path)
    terms = collect_search_terms(config)
    console.print(f"Coletando vagas para {len(terms)} termo(s) de busca.")
    with open_database(DATABASE_FILE) as connection, logged_in_browser(visible) as context:
        with console.status("Coletando vagas..."):
            summaries = collect_jobs(context, config.busca, terms, connection, pause_between_actions, DEBUG_DIR)
    console.print(build_summary_table(summaries))
