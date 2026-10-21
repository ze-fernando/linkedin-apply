from datetime import date
from pathlib import Path

import typer
from rich.table import Table

from autoapply.modules.config.commands import load_valid_config, load_valid_resumes
from autoapply.modules.config.models import Config, ProvedorLlm
from autoapply.modules.jobs.commands import run_collection
from autoapply.modules.matching.evaluation import evaluate_jobs
from autoapply.modules.matching.models import EvaluationSummary
from autoapply.modules.matching.providers import find_available_providers
from autoapply.modules.search_mode.folders import create_job_folders
from autoapply.shared.console import console
from autoapply.shared.database import open_database
from autoapply.shared.paths import CONFIG_FILE, DATABASE_FILE, VAGAS_DIR


def describe_providers(providers: list[ProvedorLlm]) -> str:
    if not providers:
        return "[yellow]⚠ Nenhum provedor de LLM disponível: todas as vagas terão análise simplificada.[/]"
    return f"Provedores de LLM: {', '.join(providers)}."


def describe_evaluation(summary: EvaluationSummary) -> str:
    message = f"Avaliadas {summary.llm + summary.keywords} vaga(s): {summary.llm} por LLM, {summary.keywords} por palavras-chave."
    if summary.keywords:
        message += f"\n[yellow]⚠ {summary.keywords} vaga(s) com análise simplificada (sem LLM).[/]"
    return message


def build_folders_table(folders: list[Path]) -> Table:
    table = Table(title=f"Pastas criadas em {VAGAS_DIR}/ ({len(folders)})")
    table.add_column("Pasta")
    for folder in folders:
        table.add_row(folder.name)
    return table


def describe_shortfall(config: Config, created: int) -> str | None:
    wanted = config.regras.modo_busca_quantidade
    if created >= wanted:
        return None
    return f"[yellow]⚠ Só {created} de {wanted} vaga(s) avaliada(s) disponíveis para o modo busca.[/]"


def search(
    visible: bool = typer.Option(False, "--visivel", help="Abre o navegador visível."),
    config_path: Path = typer.Option(CONFIG_FILE, "--config", help="Caminho do config.md."),
) -> None:
    config = load_valid_config(config_path)
    resumes = load_valid_resumes(config)
    providers = find_available_providers(config.llm)
    with open_database(DATABASE_FILE) as connection:
        run_collection(config, visible, connection)
        console.print(describe_providers(providers))
        with console.status("Avaliando vagas..."):
            summary = evaluate_jobs(connection, config, resumes, providers)
        console.print(describe_evaluation(summary))
        folders = create_job_folders(connection, config, VAGAS_DIR, date.today())
    console.print(build_folders_table(folders))
    shortfall = describe_shortfall(config, len(folders))
    if shortfall:
        console.print(shortfall)
