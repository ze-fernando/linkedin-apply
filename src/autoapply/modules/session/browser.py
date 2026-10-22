import os
import time
from datetime import datetime
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import BrowserContext, Error, Page, sync_playwright

from autoapply.modules.session.detection import detect_page_state
from autoapply.modules.session.models import (
    CheckpointDetected,
    LoginTimeout,
    PageState,
    SessionExpired,
    UnknownPageState,
)
from autoapply.shared.paths import BROWSERS_DIR

FEED_URL = "https://www.linkedin.com/feed/"
LOCALE = "pt-BR"
TIMEZONE = "America/Bahia"
VIEWPORT = {"width": 1366, "height": 900}
VISIBLE_BROWSER_ARGS = ["--ozone-platform-hint=auto"]
STATE_PRIORITY = (PageState.LOGGED_IN, PageState.CHECKPOINT, PageState.LOGGED_OUT)
SESSION_ERRORS = {
    PageState.LOGGED_OUT: SessionExpired,
    PageState.CHECKPOINT: CheckpointDetected,
    PageState.UNKNOWN: UnknownPageState,
}


@contextmanager
def open_browser_context(headless: bool, profile_dir: Path) -> Iterator[BrowserContext]:
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BROWSERS_DIR.resolve()))
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            profile_dir,
            headless=headless,
            locale=LOCALE,
            timezone_id=TIMEZONE,
            viewport=VIEWPORT,
            args=[] if headless else VISIBLE_BROWSER_ARGS,
        )
        try:
            yield context
        finally:
            context.close()


def read_page_state(page: Page) -> PageState:
    return detect_page_state(page.url, page.content())


def read_page_state_while_navigating(page: Page) -> PageState:
    try:
        return read_page_state(page)
    except Error:
        return PageState.UNKNOWN


def read_context_state(context: BrowserContext) -> PageState:
    states = [read_page_state_while_navigating(page) for page in context.pages]
    return next((state for state in STATE_PRIORITY if state in states), PageState.UNKNOWN)


def open_feed(context: BrowserContext) -> Page:
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(FEED_URL, wait_until="domcontentloaded")
    return page


def check_session(context: BrowserContext) -> PageState:
    return read_page_state(open_feed(context))


def wait_for_login(
    context: BrowserContext, timeout_seconds: float, poll_seconds: float, on_checkpoint: Callable[[], None]
) -> PageState:
    deadline = time.monotonic() + timeout_seconds
    previous_state = None
    state = read_context_state(context)
    while state != PageState.LOGGED_IN and time.monotonic() < deadline:
        if state == PageState.CHECKPOINT and previous_state != PageState.CHECKPOINT:
            on_checkpoint()
        previous_state = state
        context.pages[0].wait_for_timeout(poll_seconds * 1000)
        state = read_context_state(context)
    if state != PageState.LOGGED_IN:
        raise LoginTimeout
    return state


def ensure_session(context: BrowserContext) -> Page:
    page = open_feed(context)
    state = read_page_state(page)
    if state in SESSION_ERRORS:
        raise SESSION_ERRORS[state](page.url)
    return page


def save_debug_dump(page: Page, label: str, debug_dir: Path) -> Path:
    dump_dir = debug_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{label}"
    dump_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=dump_dir / "screenshot.png", full_page=True)
    (dump_dir / "page.html").write_text(page.content(), encoding="utf-8")
    return dump_dir
