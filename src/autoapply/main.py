from importlib.metadata import version

import typer

from autoapply.modules.applying.commands import apply, run, show_pending
from autoapply.modules.config.commands import validate
from autoapply.modules.jobs.commands import collect, show_jobs
from autoapply.modules.search_mode.commands import search
from autoapply.modules.session.commands import check_session_status, login
from autoapply.shared.console import configure_logging, console
from autoapply.shared.paths import LOGS_DIR

ROOT_EXAMPLES = [
    ("autoapply run", "coleta, avalia e aplica; cada envio pergunta Enviar? \\[y/N]"),
    ("autoapply run --simulate", "percorre tudo sem enviar nem gravar"),
    ("autoapply run --auto", "envia sem perguntar"),
    ("autoapply run --auto --interactive", "envia sozinho e pergunta só o que não souber responder"),
    ("autoapply run --skip-collect --auto", "aplica só nas vagas já avaliadas, sem coletar"),
    ("autoapply run --skip-collect --simulate", "testa as vagas já avaliadas sem enviar"),
    ("autoapply apply <job> --auto --interactive", "aplica numa vaga do modo busca (ID ou pasta)"),
    ("autoapply apply --ready --auto", "aplica em todas as pastas com currículo"),
    ("autoapply collect --visible", "só coleta, com o navegador aberto na tela"),
    ("autoapply search --visible", "modo busca: coleta, avalia e cria as pastas em vagas/"),
    ("autoapply jobs --status avaliada", "lista as vagas de um status"),
    ("autoapply pending", "perguntas sem resposta que travaram vagas"),
    ("autoapply <comando> -h", "todas as opções de um comando"),
]
RUN_EXAMPLES = [
    ("autoapply run --simulate", "percorre tudo sem enviar nem gravar"),
    ("autoapply run --auto", "envia sem perguntar"),
    ("autoapply run --auto --interactive", "envia sozinho e pergunta só o que não souber responder"),
    ("autoapply run --skip-collect --auto", "aplica só nas vagas já avaliadas, sem coletar"),
    ("autoapply run --skip-collect --simulate --visible", "testa as vagas já avaliadas vendo o navegador"),
]
APPLY_EXAMPLES = [
    ("autoapply apply <job> --simulate", "percorre a candidatura de uma vaga sem enviar"),
    ("autoapply apply <job> --auto", "aplica numa vaga sem perguntar"),
    ("autoapply apply --ready --auto --interactive", "aplica nas pastas com currículo e pergunta o que faltar"),
]


def format_examples(examples: list[tuple[str, str]]) -> str:
    width = max(len(command) for command, _ in examples) + 2
    lines = [f"{command.ljust(width)}{description}" for command, description in examples]
    return "\n".join(["[bold]Exemplos[/]", *lines])


app = typer.Typer(
    name="autoapply",
    help="Candidatura automática a vagas Easy Apply do LinkedIn.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog=format_examples(ROOT_EXAMPLES),
)
app.command("validate", help="Valida o config.md e os currículos.")(validate)
app.command("login", help="Abre o navegador para você fazer login no LinkedIn.")(login)
app.command("session", help="Verifica se a sessão do LinkedIn está ativa.")(check_session_status)
app.command("collect", help="Coleta vagas Easy Apply do LinkedIn e grava no banco.")(collect)
app.command("search", help="Coleta, avalia e cria as pastas das melhores vagas em vagas/.")(search)
app.command("jobs", help="Mostra as vagas guardadas no banco.")(show_jobs)
app.command("apply", help="Aplica nas vagas do modo busca (vagas/).", epilog=format_examples(APPLY_EXAMPLES))(apply)
app.command(
    "run",
    help="Coleta, avalia e aplica nas vagas com score suficiente (modo normal).",
    epilog=format_examples(RUN_EXAMPLES),
)(run)
app.command("pending", help="Mostra as perguntas sem resposta que travaram candidaturas.")(show_pending)


TUTORIAL = """[bold]Passo a passo do LinkedIn Auto-Apply[/]

[bold]1. Instale e faça login (um comando só)[/]
   make
   Pergunta antes de começar, instala o uv, as dependências e o Chromium,
   cria o config.md e a pasta cv_base/ e abre o navegador para você logar no LinkedIn.
   A senha nunca é salva.

[bold]2. Preencha a configuração[/]
   Preencha o config.md com seus dados, buscas, salário, anos de experiência e respostas padrão.
   Coloque seus currículos em cv_base/ e marque um deles como padrao: true.

[bold]3. Confira a configuração[/]
   uv run autoapply validate

[bold]4. Simule antes de enviar (nada é enviado nem gravado)[/]
   uv run autoapply run --simulate
   Os currículos ajustados da simulação ficam em debug/simulacao-cv/.

[bold]5. Aplique de verdade[/]
   uv run autoapply run
   Cada envio pergunta "Enviar? \\[y/N]". Com --auto, envia sem perguntar.
   Use --skip-collect para aplicar só nas vagas já avaliadas.

[bold]6. Responda as perguntas que travaram vagas[/]
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
