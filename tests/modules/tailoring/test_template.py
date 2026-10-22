import dataclasses
from pathlib import Path

from autoapply.modules.tailoring.models import Bullet
from autoapply.modules.tailoring.resume_structure import read_resume_document
from autoapply.modules.tailoring.template import render_resume_html
from tests.fakes.resume_docx import build_resume_docx

SECTION_TITLES = ["Resumo Profissional", "Experiência Profissional", "Formação", "Competências Técnicas", "Idiomas"]


def test_render_resume_html_shows_every_section_in_document_order(tmp_path: Path) -> None:
    html = render_resume_html(read_resume_document(build_resume_docx(tmp_path / "cv.docx")))

    positions = [html.index(title) for title in SECTION_TITLES]
    assert positions == sorted(positions)
    for text in [
        "Maria Teste da Silva",
        "maria.teste@example.com",
        "Jan 2025 – Atual",
        "Empresa Alfa",
        "Universidade Teste",
        "LLMs (Claude, OpenAI)",
        "intermediário",
    ]:
        assert text in html
    assert html.index("Desenvolvo APIs") < html.index("Automatizei relatórios") < html.index("Mantive sistemas")
    assert html.index("Linguagens") < html.index("Automação &amp; IA")


def test_render_resume_html_escapes_text_and_loads_nothing_external(tmp_path: Path) -> None:
    document = read_resume_document(build_resume_docx(tmp_path / "cv.docx"))
    first = document.experiences[0]
    hostile = dataclasses.replace(first, bullets=[Bullet(lead="<b>Lead</b>", text=' <script>alert("x")</script>')])
    html = render_resume_html(dataclasses.replace(document, experiences=[hostile]))

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;b&gt;Lead&lt;/b&gt;" in html
    for external in ["src=", "<link", "@import", "url(", "http://", "https://"]:
        assert external not in html
