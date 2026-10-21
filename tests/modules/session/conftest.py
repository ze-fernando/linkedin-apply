from collections.abc import Callable, Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import BrowserContext, Request, Route

from autoapply.modules.session.browser import open_browser_context

PAGES_DIR = Path(__file__).parents[2] / "fixtures" / "pages"


@pytest.fixture
def read_page() -> Callable[[str], str]:
    def read(name: str) -> str:
        return (PAGES_DIR / name).read_text(encoding="utf-8")

    return read


@pytest.fixture
def browser_context(tmp_path: Path) -> Iterator[BrowserContext]:
    with open_browser_context(headless=True, profile_dir=tmp_path / "profile") as context:
        yield context


@pytest.fixture
def serve_pages(browser_context: BrowserContext) -> Iterator[Callable[[dict[str, str]], None]]:
    requested_urls = []
    routed_urls = []

    def serve(pages: dict[str, str]) -> None:
        def handle(route: Route) -> None:
            routed_urls.append(route.request.url)
            path = urlparse(route.request.url).path
            route.fulfill(status=200, content_type="text/html", body=pages.get(path, "<html></html>"))

        browser_context.route("**/*", handle)

    def record(request: Request) -> None:
        requested_urls.append(request.url)

    browser_context.on("request", record)
    yield serve
    assert set(requested_urls) <= set(routed_urls), "requisição escapou da rota e foi para a rede"
