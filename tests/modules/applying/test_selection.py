import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from autoapply.modules.applying.selection import find_job_for_argument, select_ready_jobs
from autoapply.modules.applying.store import save_job_folder
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import insert_job
from autoapply.modules.matching.models import Analyzer, JobAnalysis
from autoapply.modules.matching.store import save_analysis


def build_analysis(job_id: str, score: int) -> JobAnalysis:
    return JobAnalysis(
        job_id=job_id,
        resume_name="Back-end",
        score=score,
        pre_score=50,
        summary="Resumo.",
        requirements=[],
        keywords=[],
        gap=[],
        analyzer=Analyzer.KEYWORDS,
        model=None,
        analyzed_at=datetime(2026, 10, 21, 16, 0),
    )


def add_folder_job(
    connection: sqlite3.Connection,
    build_job: Callable[..., Job],
    vagas_dir: Path,
    job_id: str,
    status: JobStatus,
    score: int,
    resume_name: str | None = "cv.pdf",
) -> Path:
    insert_job(connection, build_job(id=job_id, status=status))
    save_analysis(connection, build_analysis(job_id, score))
    folder = vagas_dir / f"2026-10-21-empresa-{job_id}"
    folder.mkdir(parents=True)
    if resume_name:
        (folder / resume_name).write_bytes(b"cv")
    save_job_folder(connection, job_id, folder)
    return folder


def test_find_job_for_argument_accepts_id_folder_name_or_folder_path(
    connection: sqlite3.Connection, build_job: Callable[..., Job], tmp_path: Path
) -> None:
    vagas_dir = tmp_path / "vagas"
    folder = add_folder_job(connection, build_job, vagas_dir, "111", JobStatus.AWAITING_RESUME, 80)
    insert_job(connection, build_job(id="222", status=JobStatus.EVALUATED))

    by_id = find_job_for_argument(connection, "111")
    assert (by_id.job.id, by_id.folder, by_id.score) == ("111", folder, 80)
    assert find_job_for_argument(connection, folder.name).job.id == "111"
    assert find_job_for_argument(connection, f"vagas/{folder.name}/").job.id == "111"
    assert find_job_for_argument(connection, "222") is None
    assert find_job_for_argument(connection, "999") is None


def test_select_ready_jobs_keeps_folders_with_resume_waiting_or_pending_ordered_by_score(
    connection: sqlite3.Connection, build_job: Callable[..., Job], tmp_path: Path
) -> None:
    vagas_dir = tmp_path / "vagas"
    add_folder_job(connection, build_job, vagas_dir, "baixa", JobStatus.AWAITING_RESUME, 60)
    add_folder_job(connection, build_job, vagas_dir, "alta", JobStatus.PENDING_QUESTION, 90, "cv.docx")
    add_folder_job(connection, build_job, vagas_dir, "sem-cv", JobStatus.AWAITING_RESUME, 95, None)
    add_folder_job(connection, build_job, vagas_dir, "outro-arquivo", JobStatus.AWAITING_RESUME, 94, "curriculo.pdf")
    add_folder_job(connection, build_job, vagas_dir, "aplicada", JobStatus.APPLIED, 99)
    add_folder_job(connection, build_job, vagas_dir, "falhou", JobStatus.FAILED, 98)

    assert [ready.job.id for ready in select_ready_jobs(connection)] == ["alta", "baixa"]
