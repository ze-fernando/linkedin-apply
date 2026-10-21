from collections.abc import Callable
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext

from autoapply.modules.session.browser import check_session, ensure_session, save_debug_dump, wait_for_login
from autoapply.modules.session.models import (
    CheckpointDetected,
    LoginTimeout,
    PageState,
    SessionExpired,
    UnknownPageState,
)

LOGIN_URL = "https://www.linkedin.com/login"


def redirect_after(html: str, path: str, delay_ms: int = 300) -> str:
    return html.replace(
        "</body>", f"<script>setTimeout(() => location.assign(\"{path}\"), {delay_ms})</script></body>"
    )


def open_tab_after(html: str, path: str) -> str:
    return html.replace("</body>", f"<script>setTimeout(() => window.open(\"{path}\"), 300)</script></body>")


def test_check_session_on_logged_in_feed_is_logged_in(
    browser_context: BrowserContext, serve_pages: Callable[..., None], read_page: Callable[[str], str]
) -> None:
    serve_pages({"/feed/": read_page("feed.html")})

    assert check_session(browser_context) == PageState.LOGGED_IN


def test_check_session_on_feed_showing_login_form_is_logged_out(
    browser_context: BrowserContext, serve_pages: Callable[..., None], read_page: Callable[[str], str]
) -> None:
    serve_pages({"/feed/": read_page("login_form.html")})

    assert check_session(browser_context) == PageState.LOGGED_OUT


def test_wait_for_login_returns_logged_in_after_user_logs_in(
    browser_context: BrowserContext, serve_pages: Callable[..., None], read_page: Callable[[str], str]
) -> None:
    serve_pages({"/login": redirect_after(read_page("login_form.html"), "/feed/"), "/feed/": read_page("feed.html")})
    browser_context.pages[0].goto(LOGIN_URL)

    state = wait_for_login(browser_context, timeout_seconds=5, poll_seconds=0.2, on_checkpoint=lambda: None)

    assert state == PageState.LOGGED_IN


def test_wait_for_login_detects_login_finished_in_another_tab(
    browser_context: BrowserContext, serve_pages: Callable[..., None], read_page: Callable[[str], str]
) -> None:
    serve_pages({"/login": open_tab_after(read_page("login_form.html"), "/feed/"), "/feed/": read_page("feed.html")})
    browser_context.pages[0].goto(LOGIN_URL)

    state = wait_for_login(browser_context, timeout_seconds=3, poll_seconds=0.2, on_checkpoint=lambda: None)

    assert state == PageState.LOGGED_IN


def test_wait_for_login_notifies_checkpoint_once_and_waits_for_login(
    browser_context: BrowserContext, serve_pages: Callable[..., None], read_page: Callable[[str], str]
) -> None:
    serve_pages(
        {
            "/login": redirect_after(read_page("login_form.html"), "/checkpoint/challenge/AgG1x"),
            "/checkpoint/challenge/AgG1x": redirect_after(read_page("blank.html"), "/feed/", delay_ms=1000),
            "/feed/": read_page("feed.html"),
        }
    )
    browser_context.pages[0].goto(LOGIN_URL)
    checkpoint_notices = []

    state = wait_for_login(
        browser_context, timeout_seconds=5, poll_seconds=0.2, on_checkpoint=lambda: checkpoint_notices.append(True)
    )

    assert state == PageState.LOGGED_IN
    assert len(checkpoint_notices) == 1


def test_wait_for_login_raises_timeout_when_user_never_logs_in(
    browser_context: BrowserContext, serve_pages: Callable[..., None], read_page: Callable[[str], str]
) -> None:
    serve_pages({"/login": read_page("login_form.html")})
    browser_context.pages[0].goto(LOGIN_URL)

    with pytest.raises(LoginTimeout):
        wait_for_login(browser_context, timeout_seconds=1, poll_seconds=0.2, on_checkpoint=lambda: None)


def test_ensure_session_returns_feed_page_when_logged_in(
    browser_context: BrowserContext, serve_pages: Callable[..., None], read_page: Callable[[str], str]
) -> None:
    serve_pages({"/feed/": read_page("feed.html")})

    page = ensure_session(browser_context)

    assert page.url == "https://www.linkedin.com/feed/"


@pytest.mark.parametrize(
    ("page_name", "expected_error"),
    [
        ("login_form.html", SessionExpired),
        ("feed_captcha.html", CheckpointDetected),
        ("blank.html", UnknownPageState),
    ],
)
def test_ensure_session_raises_when_session_is_not_usable(
    page_name: str,
    expected_error: type[Exception],
    browser_context: BrowserContext,
    serve_pages: Callable[..., None],
    read_page: Callable[[str], str],
) -> None:
    serve_pages({"/feed/": read_page(page_name)})

    with pytest.raises(expected_error):
        ensure_session(browser_context)


def test_save_debug_dump_writes_screenshot_and_html_in_state_folder(
    tmp_path: Path,
    browser_context: BrowserContext,
    serve_pages: Callable[..., None],
    read_page: Callable[[str], str],
) -> None:
    serve_pages({"/feed/": read_page("feed_captcha.html")})
    page = browser_context.pages[0]
    page.goto("https://www.linkedin.com/feed/")

    dump_dir = save_debug_dump(page, PageState.CHECKPOINT, tmp_path / "debug")

    assert dump_dir.parent == tmp_path / "debug"
    assert dump_dir.name.endswith("-CHECKPOINT")
    assert (dump_dir / "screenshot.png").read_bytes().startswith(b"\x89PNG")
    assert "captcha-internal" in (dump_dir / "page.html").read_text(encoding="utf-8")
