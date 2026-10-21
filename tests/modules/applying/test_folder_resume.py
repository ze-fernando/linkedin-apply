from collections.abc import Callable
from pathlib import Path

from autoapply.modules.applying.job_folders import check_folder_resume

READABLE_TEXT = ["Maria Teste, Desenvolvedora Python com experiência em APIs REST, SQL e testes automatizados."] * 5


def test_check_folder_resume_accepts_a_readable_docx_or_pdf(
    tmp_path: Path, build_docx: Callable[..., Path], build_text_pdf: Callable[[str, list[str]], Path]
) -> None:
    (tmp_path / "vaga-a").mkdir()
    (tmp_path / "vaga-b").mkdir()
    docx_file = build_docx("vaga-a/cv.docx", READABLE_TEXT)
    pdf_file = build_text_pdf("vaga-b/cv.pdf", READABLE_TEXT)

    assert check_folder_resume(tmp_path / "vaga-a").path == docx_file
    assert check_folder_resume(tmp_path / "vaga-a").problem is None
    assert check_folder_resume(tmp_path / "vaga-b").path == pdf_file
    assert check_folder_resume(tmp_path / "vaga-b").problem is None


def test_check_folder_resume_reports_each_problem(
    tmp_path: Path, build_docx: Callable[..., Path], build_blank_pdf: Callable[[str], Path]
) -> None:
    for name in ["sem-cv", "dois", "grande", "escaneado", "outro-formato"]:
        (tmp_path / name).mkdir()
    build_docx("dois/cv.docx", READABLE_TEXT)
    build_blank_pdf("dois/cv.pdf")
    (tmp_path / "grande" / "cv.pdf").write_bytes(b"0" * (2 * 1024 * 1024 + 1))
    build_blank_pdf("escaneado/cv.pdf")
    (tmp_path / "outro-formato" / "cv.odt").write_bytes(b"odt")

    assert check_folder_resume(tmp_path / "sem-cv").path is None
    assert check_folder_resume(tmp_path / "sem-cv").problem == "sem cv.docx ou cv.pdf na pasta"
    assert check_folder_resume(tmp_path / "outro-formato").problem == "sem cv.docx ou cv.pdf na pasta"
    assert check_folder_resume(tmp_path / "dois").problem == "há cv.docx e cv.pdf na pasta; deixe só um"
    assert check_folder_resume(tmp_path / "grande").problem == "cv.pdf tem mais de 2 MB"
    assert "texto insuficiente" in check_folder_resume(tmp_path / "escaneado").problem
