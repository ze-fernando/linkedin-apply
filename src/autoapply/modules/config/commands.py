from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from autoapply.modules.config.loader import load_config
from autoapply.modules.config.models import Config, ConfigError, ConfigIssue, Llm, ProvedorLlm
from autoapply.modules.matching.providers import find_available_providers, find_provider_model
from autoapply.modules.resumes.loader import count_visible_characters, load_resumes
from autoapply.modules.resumes.models import DefaultResumeUnreadable, Resume
from autoapply.shared.console import console
from autoapply.shared.paths import CONFIG_FILE


INVALID_CONFIG_EXIT_CODE = 2


def build_issues_table(issues: list[ConfigIssue]) -> Table:
    table = Table(title=f"[red]✖ config.md inválido ({len(issues)} erros)[/]", title_justify="left")
    for column in ["Linha", "Campo", "Problema"]:
        table.add_column(column, overflow="fold")
    for issue in issues:
        table.add_row("" if issue.line is None else str(issue.line), issue.field, issue.problem)
    return table


def build_profile_panel(config: Config) -> Panel:
    lines = [
        f"[bold]Nome:[/] {config.perfil.nome}",
        f"[bold]Contato:[/] {config.perfil.email}  |  {config.perfil.telefone}",
        f"[bold]Níveis:[/] {', '.join(config.busca.niveis)}",
        f"[bold]Contrato:[/] {', '.join(config.contrato.aceita)}",
        f"[bold]Regras:[/] score mínimo {config.regras.score_minimo}  ·  limite {config.regras.limite_diario}/dia",
    ]
    return Panel("\n".join(lines), title="Perfil", expand=False)


def describe_provider_status(provider: ProvedorLlm, model: str | None, available: list[ProvedorLlm]) -> str:
    if model is None:
        return "[yellow]sem modelo[/]"
    if provider in available:
        return "[green]disponível[/]"
    return "[yellow]não encontrado[/]"


def build_llm_table(llm: Llm) -> Table:
    available = find_available_providers(llm)
    table = Table(title="LLM")
    for column in ["Ordem", "Provedor", "Modelo", "Status"]:
        table.add_column(column)
    for position, provider in enumerate(llm.provedores, start=1):
        model = find_provider_model(llm, provider)
        table.add_row(str(position), provider, model or "", describe_provider_status(provider, model, available))
    return table


def build_resumes_table(resumes: list[Resume]) -> Table:
    table = Table(title="Currículos")
    for column in ["Nome", "Arquivo", "Padrão", "Caracteres", "Status"]:
        table.add_column(column)
    for resume in resumes:
        table.add_row(
            resume.name,
            resume.path.name,
            "sim" if resume.is_default else "",
            str(count_visible_characters(resume.text)),
            "[green]ok[/]" if resume.problem is None else f"[yellow]{resume.problem}[/]",
        )
    return table


def describe_ignored_resumes(resumes: list[Resume]) -> str | None:
    ignored_count = sum(resume.problem is not None for resume in resumes)
    if ignored_count == 0:
        return None
    if ignored_count == 1:
        return "[yellow]⚠ 1 currículo ignorado[/]"
    return f"[yellow]⚠ {ignored_count} currículos ignorados[/]"


def validate(
    config_path: Path = typer.Option(CONFIG_FILE, "--config", help="Caminho do config.md."),
) -> None:
    if not config_path.is_file():
        console.print(f"[red]✖ config.md não encontrado: {config_path}[/]")
        raise typer.Exit(INVALID_CONFIG_EXIT_CODE)
    try:
        config = load_config(config_path)
    except ConfigError as error:
        console.print(build_issues_table(error.issues))
        raise typer.Exit(INVALID_CONFIG_EXIT_CODE) from error
    try:
        resumes = load_resumes(config)
    except DefaultResumeUnreadable as error:
        console.print(f"[red]✖ {error}[/]")
        raise typer.Exit(INVALID_CONFIG_EXIT_CODE) from error
    console.print(build_profile_panel(config))
    console.print(build_resumes_table(resumes))
    console.print(build_llm_table(config.llm))
    ignored_warning = describe_ignored_resumes(resumes)
    if ignored_warning:
        console.print(ignored_warning)
    console.print(f"{len(config.respostas)} respostas padrão  ·  resposta genérica: ok")
    console.print("[green]✔ config.md válido[/]")
