from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import BrowserContext


@contextmanager
def open_pdf_context(context: BrowserContext) -> Iterator[BrowserContext]:
    if context.browser is None:
        raise RuntimeError("navegador sem BrowserType para gerar o PDF")
    browser = context.browser.browser_type.launch(headless=True)
    try:
        yield browser.new_context()
    finally:
        browser.close()


def render_resume_pdf(context: BrowserContext, html: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    page = context.new_page()
    try:
        page.set_content(html, wait_until="load")
        page.pdf(path=str(path), prefer_css_page_size=True, print_background=True)
    finally:
        page.close()
    return path
