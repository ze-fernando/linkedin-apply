from collections.abc import Callable
from pathlib import Path

from autoapply.modules.resumes.loader import extract_resume_text


def test_extract_resume_text_reads_docx_paragraphs_and_tables_in_order(
    build_docx: Callable[..., Path],
) -> None:
    path = build_docx(
        "cv.docx",
        paragraphs=["Maria Teste", "Desenvolvedora Python"],
        table_rows=[["Linguagens", "Python, SQL"], ["Bancos", "PostgreSQL"]],
    )

    text = extract_resume_text(path)

    assert text.splitlines() == [
        "Maria Teste",
        "Desenvolvedora Python",
        "Linguagens",
        "Python, SQL",
        "Bancos",
        "PostgreSQL",
    ]


def test_extract_resume_text_reads_pdf_text(build_text_pdf: Callable[[str, list[str]], Path]) -> None:
    path = build_text_pdf("cv.pdf", ["Maria Teste", "Desenvolvedora Python (Django)"])

    text = extract_resume_text(path)

    assert "Maria Teste" in text
    assert "Desenvolvedora Python (Django)" in text
