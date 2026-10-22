from datetime import datetime, timedelta
from pathlib import Path

import typer
from rich.markup import escape
from rich.table import Table

from autoapply.modules.applying.models import ApplyMode, AttemptOutcome
from autoapply.modules.reporting.models import Report, ReportEntry
from autoapply.modules.reporting.report import DATE_FORMAT, build_report, describe_resume_kind, write_report_csv
from autoapply.shared.console import console
from autoapply.shared.database import open_database
from autoapply.shared.paths import DATABASE_FILE

DEFAULT_DAYS = 7
OUTCOME_COLUMNS = {
    AttemptOutcome.APPLIED: "Aplicadas",
    AttemptOutcome.ALREADY_APPLIED: "Já aplicadas",
    AttemptOutcome.PENDING: "Pendentes",
    AttemptOutcome.FAILED: "Falhas",
}
OUTCOME_LABELS = {
    AttemptOutcome.APPLIED: "[green]aplicada[/]",
    AttemptOutcome.ALREADY_APPLIED: "[cyan]já aplicada[/]",
    AttemptOutcome.PENDING: "[yellow]pendente[/]",
    AttemptOutcome.FAILED: "[red]falhou[/]",
}


def describe_period(days: int) -> str:
    return "todo o histórico" if days == 0 else f"últimos {days} dias"


def build_summary_table(report: Report, days: int) -> Table:
    table = Table(title=f"Candidaturas · {describe_period(days)}")
    table.add_column("Modo")
    for label in OUTCOME_COLUMNS.values():
        table.add_column(label, justify="right")
    for mode in ApplyMode:
        table.add_row(mode, *(str(report.counts.get((mode, outcome), 0)) for outcome in OUTCOME_COLUMNS))
    totals = [str(sum(report.counts.get((mode, outcome), 0) for mode in ApplyMode)) for outcome in OUTCOME_COLUMNS]
    table.add_row("[bold]total[/]", *totals)
    return table


def describe_completion(report: Report) -> str:
    if report.completion_rate is None:
        return "Taxa de conclusão: sem candidaturas concluídas, pendentes ou com falha."
    applied = sum(count for (_, outcome), count in report.counts.items() if outcome == AttemptOutcome.APPLIED)
    finished = sum(
        count
        for (_, outcome), count in report.counts.items()
        if outcome in {AttemptOutcome.APPLIED, AttemptOutcome.FAILED, AttemptOutcome.PENDING}
    )
    return f"Taxa de conclusão: {report.completion_rate:.0%} ({applied} de {finished})"


def build_entries_table(entries: list[ReportEntry]) -> Table:
    table = Table(title=f"Última tentativa de cada vaga ({len(entries)})")
    for column in ["Data", "Modo", "Resultado", "Empresa", "Cargo", "Score", "Currículo", "Link"]:
        table.add_column(column)
    for entry in entries:
        table.add_row(
            entry.attempted_at.strftime(DATE_FORMAT),
            entry.mode,
            OUTCOME_LABELS[entry.outcome],
            escape(entry.company),
            escape(entry.title),
            "-" if entry.score is None else str(entry.score),
            describe_resume_kind(entry),
            entry.url,
        )
    return table


def show_report(
    days: int = typer.Option(DEFAULT_DAYS, "--days", min=0, help="Período em dias; 0 mostra todo o histórico."),
    csv_path: Path | None = typer.Option(None, "--csv", help="Grava a lista em CSV (separador ';', abre no Excel)."),
) -> None:
    since = None if days == 0 else datetime.now() - timedelta(days=days)
    with open_database(DATABASE_FILE) as connection:
        report = build_report(connection, since)
    console.print(build_summary_table(report, days))
    console.print(f"Vagas ignoradas: {report.ignored}")
    console.print(describe_completion(report))
    if report.failure_reasons:
        console.print("Motivos de falha mais comuns:")
        for reason, count in report.failure_reasons:
            console.print(f"  • {count}× {escape(reason)}")
    if not report.entries:
        console.print("Nenhuma candidatura no período.")
        return
    console.print(build_entries_table(report.entries))
    if csv_path is not None:
        write_report_csv(report.entries, csv_path)
        console.print(f"[green]✔ Lista gravada em {csv_path}.[/]")
