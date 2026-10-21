from importlib.metadata import version

import typer

app = typer.Typer(
    name="autoapply",
    help="Candidatura automática a vagas Easy Apply do LinkedIn.",
    no_args_is_help=True,
)


def show_version(requested: bool) -> None:
    if requested:
        typer.echo(version("autoapply"))
        raise typer.Exit()


@app.callback()
def run_cli(
    show_version_flag: bool = typer.Option(
        False,
        "--version",
        callback=show_version,
        is_eager=True,
        help="Mostra a versão e sai.",
    ),
) -> None:
    pass
