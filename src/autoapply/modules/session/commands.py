import logging
from collections.abc import Iterator
from contextlib import contextmanager

import typer
from playwright.sync_api import BrowserContext
from rich.panel import Panel

from autoapply.modules.session.browser import (
    ensure_session,
    open_browser_context,
    open_feed,
    read_page_state,
    save_debug_dump,
    wait_for_login,
)
from autoapply.modules.session.models import (
    CheckpointDetected,
    LoginTimeout,
    PageState,
    SessionExpired,
    UnknownPageState,
)
from autoapply.shared.console import console
from autoapply.shared.paths import BROWSER_PROFILE_DIR, DEBUG_DIR

LOGIN_URL = "https://www.linkedin.com/login"
LOGIN_TIMEOUT_SECONDS = 300
LOGIN_POLL_SECONDS = 2
SESSION_EXPIRED_EXIT_CODE = 1
LOGIN_TIMEOUT_EXIT_CODE = 1
UNEXPECTED_PAGE_EXIT_CODE = 3

logger = logging.getLogger("autoapply.session")


def notify_checkpoint() -> None:
    logger.info("verificação de segurança detectada durante o login")
    console.print(Panel("Resolva a verificação na janela do navegador.", title="Verificação", border_style="yellow"))


def login() -> None:
    console.print(f"Abrindo o navegador em {LOGIN_URL}. Faça o login na janela (até {LOGIN_TIMEOUT_SECONDS // 60} min).")
    with open_browser_context(headless=False, profile_dir=BROWSER_PROFILE_DIR) as context:
        context.pages[0].goto(LOGIN_URL, wait_until="domcontentloaded")
        try:
            wait_for_login(context, LOGIN_TIMEOUT_SECONDS, LOGIN_POLL_SECONDS, notify_checkpoint)
        except LoginTimeout:
            logger.error("login não concluído no tempo limite")
            console.print(f"[red]✖ Login não concluído em {LOGIN_TIMEOUT_SECONDS // 60} min.[/]")
            raise typer.Exit(LOGIN_TIMEOUT_EXIT_CODE)
    logger.info("sessão salva", extra={"event": "session.saved"})
    console.print(Panel(f"Sessão salva em {BROWSER_PROFILE_DIR}.", title="✔ Login", border_style="green"))


def check_session_status(
    visible: bool = typer.Option(False, "--visivel", help="Abre o navegador visível."),
) -> None:
    with open_browser_context(headless=not visible, profile_dir=BROWSER_PROFILE_DIR) as context:
        page = open_feed(context)
        state = read_page_state(page)
        logger.info("estado da sessão: %s", state, extra={"event": "session.checked", "state": state})
        if state == PageState.LOGGED_IN:
            console.print("[green]✔ Sessão ativa.[/]")
            return
        if state == PageState.LOGGED_OUT:
            console.print("[red]✖ Sessão expirada, rode `autoapply login`.[/]")
            raise typer.Exit(SESSION_EXPIRED_EXIT_CODE)
        dump_dir = save_debug_dump(page, state, DEBUG_DIR)
    console.print(f"[yellow]⚠ Página inesperada ({state}). Screenshot e HTML salvos em {dump_dir}.[/]")
    raise typer.Exit(UNEXPECTED_PAGE_EXIT_CODE)


@contextmanager
def logged_in_browser(visible: bool) -> Iterator[BrowserContext]:
    with open_browser_context(headless=not visible, profile_dir=BROWSER_PROFILE_DIR) as context:
        try:
            ensure_session(context)
            yield context
        except SessionExpired as error:
            logger.error("sessão expirada em %s", error)
            console.print("[red]✖ Sessão expirada, rode `autoapply login`.[/]")
            raise typer.Exit(SESSION_EXPIRED_EXIT_CODE) from error
        except (CheckpointDetected, UnknownPageState) as error:
            page = context.pages[0]
            state = read_page_state(page)
            dump_dir = save_debug_dump(page, state, DEBUG_DIR)
            logger.error("execução interrompida: %s em %s", state, error, extra={"event": "session.interrupted"})
            console.print(f"[yellow]⚠ Execução interrompida ({state}). Screenshot e HTML salvos em {dump_dir}.[/]")
            raise typer.Exit(UNEXPECTED_PAGE_EXIT_CODE) from error
