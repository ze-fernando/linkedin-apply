from importlib.metadata import version

import typer

from autoapply.modules.applying.commands import apply, run
from autoapply.modules.config.commands import validate
from autoapply.modules.jobs.commands import collect, show_jobs
from autoapply.modules.search_mode.commands import search
from autoapply.modules.session.commands import check_session_status, login
from autoapply.shared.console import configure_logging, console
from autoapply.shared.paths import LOGS_DIR

app = typer.Typer(
    name="autoapply",
    help="Candidatura automática a vagas Easy Apply do LinkedIn.",
    no_args_is_help=True,
)
app.command("validar", help="Valida o config.md e os currículos.")(validate)
app.command("login", help="Abre o navegador para você fazer login no LinkedIn.")(login)
app.command("sessao", help="Verifica se a sessão do LinkedIn está ativa.")(check_session_status)
app.command("coletar", help="Coleta vagas Easy Apply do LinkedIn e grava no banco.")(collect)
app.command("buscar", help="Coleta, avalia e cria as pastas das melhores vagas em vagas/.")(search)
app.command("vagas", help="Mostra as vagas guardadas no banco.")(show_jobs)
app.command("aplicar", help="Aplica nas vagas do modo busca (vagas/).")(apply)
app.command("rodar", help="Coleta, avalia e aplica nas vagas com score suficiente (modo normal).")(run)


def show_version(requested: bool) -> None:
    if requested:
        typer.echo(version("autoapply"))
        raise typer.Exit()


@app.callback()
def run_cli(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mostra mensagens de depuração."),
    show_version_flag: bool = typer.Option(
        False,
        "--version",
        callback=show_version,
        is_eager=True,
        help="Mostra a versão e sai.",
    ),
) -> None:
    configure_logging(LOGS_DIR, verbose, console)
