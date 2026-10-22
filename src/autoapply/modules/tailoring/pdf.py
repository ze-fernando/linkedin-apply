from pathlib import Path

from playwright.sync_api import BrowserContext


def render_resume_pdf(context: BrowserContext, html: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    page = context.new_page()
    try:
        page.set_content(html, wait_until="load")
        page.pdf(path=str(path), prefer_css_page_size=True, print_background=True)
    finally:
        page.close()
    return path
