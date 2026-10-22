from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import BrowserContext
from pypdf import PdfReader

from autoapply.modules.tailoring.pdf import render_resume_pdf
from autoapply.modules.tailoring.resume_structure import read_resume_document
from autoapply.modules.tailoring.template import render_resume_html
from tests.fakes.resume_docx import build_resume_docx


def test_render_resume_pdf_writes_a_pdf_with_extractable_text(
    browser_context: BrowserContext, serve_pages: Callable[[dict[str, str]], None], tmp_path: Path
) -> None:
    serve_pages({})
    html = render_resume_html(read_resume_document(build_resume_docx(tmp_path / "cv.docx")))

    path = render_resume_pdf(browser_context, html, tmp_path / "saida" / "cv.pdf")

    text = " ".join((page.extract_text() or "") for page in PdfReader(path).pages).casefold()
    assert path == tmp_path / "saida" / "cv.pdf"
    for expected in ["Maria Teste da Silva", "Experiência Profissional", "Desenvolvo APIs", "FastAPI", "Selenium"]:
        assert expected.casefold() in text
