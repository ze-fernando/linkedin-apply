import zipfile
from pathlib import Path

import docx
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from autoapply.modules.config.models import Config, Curriculo
from autoapply.modules.resumes.models import DefaultResumeUnreadable, Resume

MINIMUM_TEXT_CHARACTERS = 300
UNREADABLE_FILE_ERRORS = (PdfReadError, PackageNotFoundError, zipfile.BadZipFile, KeyError)


def extract_table_lines(table: Table) -> list[str]:
    return [cell.text for row in table.rows for cell in row.cells]


def extract_docx_text(path: Path) -> str:
    lines = []
    for block in docx.Document(str(path)).iter_inner_content():
        lines.extend(extract_table_lines(block) if isinstance(block, Table) else [block.text])
    return "\n".join(lines)


def extract_pdf_text(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def extract_resume_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return extract_pdf_text(path)
    return extract_docx_text(path)


def count_visible_characters(text: str) -> int:
    return sum(not character.isspace() for character in text)


def detect_text_problem(text: str) -> str | None:
    visible_characters = count_visible_characters(text)
    if visible_characters < MINIMUM_TEXT_CHARACTERS:
        return (
            f"texto insuficiente ({visible_characters} caracteres, mínimo {MINIMUM_TEXT_CHARACTERS}): "
            "provável PDF escaneado"
        )
    return None


def read_text_and_problem(path: Path) -> tuple[str, str | None]:
    try:
        text = extract_resume_text(path)
    except UNREADABLE_FILE_ERRORS as error:
        return "", f"não foi possível ler o arquivo: {error}"
    return text, detect_text_problem(text)


def build_resume(curriculo: Curriculo) -> Resume:
    text, problem = read_text_and_problem(curriculo.arquivo)
    return Resume(
        name=curriculo.nome,
        path=curriculo.arquivo,
        is_default=curriculo.padrao,
        searches=curriculo.buscas,
        text=text,
        problem=problem,
    )


def ensure_default_is_readable(resumes: list[Resume]) -> None:
    for resume in resumes:
        if resume.is_default and resume.problem:
            raise DefaultResumeUnreadable(f"currículo padrão '{resume.name}' inválido: {resume.problem}")


def load_resumes(config: Config) -> list[Resume]:
    resumes = [build_resume(curriculo) for curriculo in config.curriculos]
    ensure_default_is_readable(resumes)
    return resumes
