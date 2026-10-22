from importlib.metadata import version

import typer

from autoapply.modules.applying.commands import apply, run, show_pending
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
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.command("validate", help="Valida o config.md e os currículos.")(validate)
app.command("login", help="Abre o navegador para você fazer login no LinkedIn.")(login)
app.command("session", help="Verifica se a sessão do LinkedIn está ativa.")(check_session_status)
app.command("collect", help="Coleta vagas Easy Apply do LinkedIn e grava no banco.")(collect)
app.command("search", help="Coleta, avalia e cria as pastas das melhores vagas em vagas/.")(search)
app.command("jobs", help="Mostra as vagas guardadas no banco.")(show_jobs)
app.command("apply", help="Aplica nas vagas do modo busca (vagas/).")(apply)
app.command("run", help="Coleta, avalia e aplica nas vagas com score suficiente (modo normal).")(run)
app.command("pending", help="Mostra as perguntas sem resposta que travaram candidaturas.")(show_pending)


TUTORIAL = """[bold]Passo a passo do LinkedIn Auto-Apply[/]

[bold]1. Instale[/]
   uv sync
   PLAYWRIGHT_BROWSERS_PATH=.playwright uv run playwright install chromium

[bold]2. Configure[/]
   cp config.example.md config.md
   Preencha o config.md com seus dados, buscas, salário, anos de experiência e respostas padrão.
   Coloque seus currículos em cv_base/ e marque um deles como padrao: true.

[bold]3. Confira a configuração[/]
   uv run autoapply validate

[bold]4. Faça login no LinkedIn (à mão; a senha nunca é salva)[/]
   uv run autoapply login

[bold]5. Simule antes de enviar (nada é enviado nem gravado)[/]
   uv run autoapply run --simulate
   Os currículos ajustados da simulação ficam em debug/simulacao-cv/.

[bold]6. Aplique de verdade[/]
   uv run autoapply run
   Cada envio pergunta "Enviar? \\[y/N]". Com --auto, envia sem perguntar.
   Use --skip-collect para aplicar só nas vagas já avaliadas.

[bold]7. Responda as perguntas que travaram vagas[/]
   uv run autoapply pending
   Responda na tabela de Respostas padrão do config.md; o próximo run tenta de novo.
   Ou rode com --interactive para responder na hora e salvar no config.md.

[bold]Modo busca (você escolhe o currículo de cada vaga)[/]
   uv run autoapply search     cria as pastas das melhores vagas em vagas/
   uv run autoapply apply --ready

Use -h em qualquer comando para ver as opções, por exemplo: uv run autoapply run -h"""


def show_tutorial(requested: bool) -> None:
    if requested:
        console.print(TUTORIAL)
        raise typer.Exit()


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
    show_tutorial_flag: bool = typer.Option(
        False,
        "--tutorial",
        callback=show_tutorial,
        is_eager=True,
        help="Mostra o passo a passo de uso e sai.",
    ),
) -> None:
    configure_logging(LOGS_DIR, verbose, console)
