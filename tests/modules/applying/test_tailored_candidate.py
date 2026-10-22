import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from autoapply.modules.applying.models import ApplicationCandidate
from autoapply.modules.jobs.models import Job
from autoapply.modules.jobs.store import insert_job
from autoapply.modules.tailoring.models import TailoredResume, TailoringResult, TailoringStatus
from autoapply.modules.tailoring.store import find_tailored_resume
from autoapply.modules.tailoring.tailor import prepare_tailored_candidate

NOW = datetime(2026, 10, 22, 10, 0)
MODEL = "opencode/deepseek-v4.1-flash-free"
PDF_NAME = "2026-10-22-empresa-teste-desenvolvedor-net-pleno.pdf"


def build_candidate(
    connection: sqlite3.Connection, build_job: Callable[..., Job], resume_file: str = "cv_base/dotnet.docx"
) -> ApplicationCandidate:
    job = build_job()
    insert_job(connection, job)
    return ApplicationCandidate(job=job, resume_file=Path(resume_file), job_answers={}, score=80)


def build_tailor(
    status: TailoringStatus, calls: list[Path]
) -> Callable[[ApplicationCandidate, Path], TailoringResult]:
    def tailor(candidate: ApplicationCandidate, pdf_path: Path) -> TailoringResult:
        calls.append(pdf_path)
        if status == TailoringStatus.USED:
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(b"%PDF")
            return TailoringResult(status=status, pdf_path=pdf_path, reason=None, provider="opencode", model=MODEL)
        return TailoringResult(
            status=status, pdf_path=None, reason="resumo cita número que não está no currículo: 5",
            provider="opencode", model=MODEL,
        )

    return tailor


def test_prepare_tailored_candidate_sends_the_adjusted_pdf_and_reuses_it_when_the_job_comes_back(
    connection: sqlite3.Connection, build_job: Callable[..., Job], tmp_path: Path
) -> None:
    candidate = build_candidate(connection, build_job)
    calls = []
    tailor = build_tailor(TailoringStatus.USED, calls)
    pdf_dir = tmp_path / "curriculos-enviados"

    prepared = prepare_tailored_candidate(connection, candidate, False, tailor, NOW, pdf_dir)
    again = prepare_tailored_candidate(connection, candidate, False, tailor, NOW, pdf_dir)

    assert (prepared.resume_file, prepared.warning, prepared.tailoring) == (
        pdf_dir / PDF_NAME,
        "cv ajustado",
        TailoringStatus.USED,
    )
    assert again == prepared
    assert calls == [pdf_dir / PDF_NAME]
    assert find_tailored_resume(connection, candidate.job.id) == TailoredResume(
        job_id=candidate.job.id,
        base_resume=Path("cv_base/dotnet.docx"),
        pdf_path=pdf_dir / PDF_NAME,
        status=TailoringStatus.USED,
        reason=None,
        provider="opencode",
        model=MODEL,
        created_at=NOW,
    )


def test_prepare_tailored_candidate_keeps_the_base_resume_when_the_adjustment_is_discarded(
    connection: sqlite3.Connection, build_job: Callable[..., Job], tmp_path: Path
) -> None:
    candidate = build_candidate(connection, build_job)
    calls = []
    tailor = build_tailor(TailoringStatus.DISCARDED, calls)

    prepared = prepare_tailored_candidate(connection, candidate, False, tailor, NOW, tmp_path)
    prepare_tailored_candidate(connection, candidate, False, tailor, NOW, tmp_path)

    assert (prepared.resume_file, prepared.warning, prepared.tailoring) == (
        Path("cv_base/dotnet.docx"),
        "ajuste descartado: resumo cita número que não está no currículo: 5",
        TailoringStatus.DISCARDED,
    )
    assert len(calls) == 2
    saved = find_tailored_resume(connection, candidate.job.id)
    assert saved is not None
    assert (saved.status, saved.pdf_path, saved.reason) == (
        TailoringStatus.DISCARDED,
        None,
        "resumo cita número que não está no currículo: 5",
    )


def test_prepare_tailored_candidate_in_simulation_writes_nothing_to_the_database(
    connection: sqlite3.Connection, build_job: Callable[..., Job], tmp_path: Path
) -> None:
    candidate = build_candidate(connection, build_job)
    calls = []
    simulation_dir = tmp_path / "debug" / "simulacao-cv"

    prepared = prepare_tailored_candidate(
        connection, candidate, True, build_tailor(TailoringStatus.USED, calls), NOW, simulation_dir
    )

    assert prepared.resume_file == simulation_dir / PDF_NAME
    assert find_tailored_resume(connection, candidate.job.id) is None


def test_prepare_tailored_candidate_adds_the_job_id_when_the_pdf_name_already_exists(
    connection: sqlite3.Connection, build_job: Callable[..., Job], tmp_path: Path
) -> None:
    candidate = build_candidate(connection, build_job)
    (tmp_path / PDF_NAME).write_bytes(b"%PDF")

    prepared = prepare_tailored_candidate(
        connection, candidate, False, build_tailor(TailoringStatus.USED, []), NOW, tmp_path
    )

    assert prepared.resume_file == tmp_path / "2026-10-22-empresa-teste-desenvolvedor-net-pleno-4481248162.pdf"


def test_prepare_tailored_candidate_does_not_adjust_a_pdf_base_resume(
    connection: sqlite3.Connection, build_job: Callable[..., Job], tmp_path: Path
) -> None:
    candidate = build_candidate(connection, build_job, "cv_base/dotnet.pdf")
    calls = []

    prepared = prepare_tailored_candidate(
        connection, candidate, False, build_tailor(TailoringStatus.USED, calls), NOW, tmp_path
    )

    assert prepared == candidate
    assert calls == []
