import sqlite3
from datetime import date, datetime
from pathlib import Path

import typer
from rich.table import Table

from autoapply.modules.applying.easy_apply import apply_to_job
from autoapply.modules.applying.job_answers import load_job_answers
from autoapply.modules.applying.job_folders import check_folder_resume, migrate_job_folders
from autoapply.modules.applying.models import (
    AnswerContext,
    ApplicationCandidate,
    ApplicationOutcome,
    ApplicationResult,
    ApplyMode,
    FolderJob,
    RunEntry,
    RunSummary,
)
from autoapply.modules.applying.runner import run_applications
from autoapply.modules.applying.selection import find_job_for_argument, select_ready_jobs
from autoapply.modules.applying.store import count_applied_on
from autoapply.modules.config.commands import load_valid_config
from autoapply.modules.config.models import Config, ConfigError
from autoapply.modules.jobs.models import Job
from autoapply.modules.session.commands import logged_in_browser
from autoapply.shared.console import console
from autoapply.shared.database import open_database
from autoapply.shared.pacing import pause_between_actions, pause_between_applications
from autoapply.shared.paths import CONFIG_FILE, DATABASE_FILE, DEBUG_DIR, VAGAS_DIR

USAGE_EXIT_CODE = 2
OUTCOME_LABELS = {
    ApplicationOutcome.APPLIED: "[green]✔ Aplicada[/]",
    ApplicationOutcome.ALREADY_APPLIED: "[cyan]✔ Já aplicada[/]",
    ApplicationOutcome.PENDING: "[yellow]? Pendente[/]",
    ApplicationOutcome.FAILED: "[red]✖ Falhou[/]",
    ApplicationOutcome.SIMULATED: "[blue]◌ Simulada[/]",
}
SKIPPED_LABEL = "[dim]⏭ Pulada[/]"


def describe_job(job: Job, score: int | None) -> str:
    score_text = "score -" if score is None else f"score {score}"
    return f"{job.company} · {job.title} · {score_text}"


def describe_result(result: ApplicationResult) -> str:
    if result.outcome == ApplicationOutcome.PENDING:
        questions = "; ".join(field.label for field in result.pending_fields)
        return f"{len(result.pending_fields)} pergunta(s): {questions}"
    return result.reason or ""


def format_entry_line(entry: RunEntry) -> str:
    candidate = entry.candidate
    parts = [
        OUTCOME_LABELS[entry.result.outcome],
        describe_job(candidate.job, candidate.score),
        str(candidate.resume_file),
    ]
    detail = describe_result(entry.result)
    return " · ".join(parts + [detail] if detail else parts)


def format_skipped_line(folder_job: FolderJob, problem: str) -> str:
    return f"{SKIPPED_LABEL} · {describe_job(folder_job.job, folder_job.score)} · {problem}"


def describe_answers_error(error: ConfigError) -> str:
    issues = "; ".join(f"linha {issue.line}: {issue.problem}" for issue in error.issues)
    return f"respostas.md inválido ({issues})"


def build_candidate(folder_job: FolderJob) -> ApplicationCandidate | str:
    resume = check_folder_resume(folder_job.folder)
    if resume.problem is not None or resume.path is None:
        return resume.problem or "sem currículo"
    try:
        job_answers = load_job_answers(folder_job.folder)
    except ConfigError as error:
        return describe_answers_error(error)
    return ApplicationCandidate(
        job=folder_job.job, resume_file=resume.path, job_answers=job_answers, score=folder_job.score
    )


def prepare_candidates(folder_jobs: list[FolderJob]) -> list[ApplicationCandidate]:
    candidates = []
    for folder_job in folder_jobs:
        candidate = build_candidate(folder_job)
        if isinstance(candidate, str):
            console.print(format_skipped_line(folder_job, candidate))
        else:
            candidates.append(candidate)
    return candidates


def select_folder_jobs(connection: sqlite3.Connection, argument: str | None, ready: bool) -> list[FolderJob]:
    if (argument is None) == (not ready):
        console.print("[red]✖ Informe uma vaga (ID ou pasta) ou use --prontas.[/]")
        raise typer.Exit(USAGE_EXIT_CODE)
    if ready:
        return select_ready_jobs(connection)
    folder_job = find_job_for_argument(connection, argument)
    if folder_job is None:
        console.print(f"[red]✖ Vaga não encontrada em {VAGAS_DIR}/: {argument}[/]")
        raise typer.Exit(USAGE_EXIT_CODE)
    return [folder_job]


def count_outcomes(entries: list[RunEntry]) -> dict[ApplicationOutcome, int]:
    counts = dict.fromkeys(OUTCOME_LABELS, 0)
    for entry in entries:
        counts[entry.result.outcome] += 1
    return counts


def describe_counters(entries: list[RunEntry], connection: sqlite3.Connection, config: Config, simulate: bool) -> str:
    counts = count_outcomes(entries)
    remaining = max(config.regras.limite_diario - count_applied_on(connection, date.today()), 0)
    limit_text = "limite não se aplica (simulação)" if simulate else f"restam {remaining} no limite de hoje"
    return (
        f"Aplicando... aplicadas {counts[ApplicationOutcome.APPLIED]} · pendentes {counts[ApplicationOutcome.PENDING]}"
        f" · falhas {counts[ApplicationOutcome.FAILED]} · {limit_text}"
    )


def build_run_table(summary: RunSummary) -> Table:
    table = Table(title="Resumo da execução")
    table.add_column("Resultado")
    table.add_column("Vagas", justify="right")
    for outcome, count in count_outcomes(summary.entries).items():
        if count:
            table.add_row(OUTCOME_LABELS[outcome], str(count))
    if summary.not_attempted:
        table.add_row("[dim]Não tentadas (limite do dia)[/]", str(summary.not_attempted))
    return table


def list_new_pending_questions(summary: RunSummary) -> list[str]:
    questions = {}
    for entry in summary.entries:
        for field in entry.result.pending_fields:
            questions.setdefault(field.label, field)
    return list(questions)


def show_run_summary(summary: RunSummary) -> None:
    console.print(build_run_table(summary))
    if summary.limit_reached:
        console.print(
            f"[yellow]⚠ Limite diário atingido; {summary.not_attempted} vaga(s) ficaram para outro dia.[/]"
        )
    questions = list_new_pending_questions(summary)
    if questions:
        console.print("[yellow]Perguntas pendentes (responda no respostas.md da pasta ou no config.md):[/]")
        for question in questions:
            console.print(f"  • {question}")


def apply(
    argument: str | None = typer.Argument(None, metavar="VAGA", help="ID da vaga ou nome da pasta em vagas/."),
    ready: bool = typer.Option(False, "--prontas", help="Aplica nas vagas com currículo na pasta."),
    simulate: bool = typer.Option(False, "--simular", help="Percorre o formulário sem enviar."),
    visible: bool = typer.Option(False, "--visivel", help="Abre o navegador visível."),
    config_path: Path = typer.Option(CONFIG_FILE, "--config", help="Caminho do config.md."),
) -> None:
    config = load_valid_config(config_path)
    with open_database(DATABASE_FILE) as connection:
        migrated = migrate_job_folders(connection, VAGAS_DIR)
        if migrated:
            console.print(f"Registradas {len(migrated)} pasta(s) antigas de {VAGAS_DIR}/.")
        candidates = prepare_candidates(select_folder_jobs(connection, argument, ready))
        if not candidates:
            console.print("Nenhuma vaga pronta para aplicar.")
            return
        if simulate:
            console.print("[blue]Modo simulação: nada é enviado nem gravado no banco.[/]")
        with logged_in_browser(visible) as context, console.status("Aplicando...") as status:
            page = context.pages[0]

            def apply_candidate(candidate: ApplicationCandidate) -> ApplicationResult:
                answer_context = AnswerContext(
                    config=config, job_answers=candidate.job_answers, job_title=candidate.job.title
                )
                return apply_to_job(
                    page,
                    candidate.job,
                    candidate.resume_file,
                    answer_context,
                    simulate,
                    pause_between_actions,
                    DEBUG_DIR,
                )

            entries = []

            def show(entry: RunEntry) -> None:
                entries.append(entry)
                console.print(format_entry_line(entry))
                status.update(describe_counters(entries, connection, config, simulate))

            summary = run_applications(
                connection,
                config,
                candidates,
                ApplyMode.SEARCH,
                simulate,
                apply_candidate,
                pause_between_applications,
                datetime.now,
                show,
            )
    show_run_summary(summary)
