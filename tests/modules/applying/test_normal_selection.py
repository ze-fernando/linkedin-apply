import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from autoapply.modules.applying.selection import select_normal_candidates
from autoapply.modules.applying.store import save_job_folder
from autoapply.modules.config.loader import parse_config_data
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import insert_job, list_jobs
from autoapply.modules.matching.models import Analyzer, JobAnalysis
from autoapply.modules.matching.store import save_analysis


def add_job(
    connection: sqlite3.Connection,
    build_job: Callable[..., Job],
    job_id: str,
    status: JobStatus,
    score: int | None,
    resume_name: str = "Dados",
) -> None:
    insert_job(connection, build_job(id=job_id, status=status))
    if score is not None:
        save_analysis(
            connection,
            JobAnalysis(
                job_id=job_id,
                resume_name=resume_name,
                score=score,
                pre_score=50,
                summary="Resumo.",
                requirements=[],
                keywords=[],
                gap=[],
                analyzer=Analyzer.KEYWORDS,
                model=None,
                analyzed_at=datetime(2026, 10, 21, 16, 0),
            ),
        )


def test_select_normal_candidates_picks_jobs_without_folder_above_minimum_and_ignores_the_rest(
    connection: sqlite3.Connection,
    build_job: Callable[..., Job],
    valid_data: dict[str, object],
    base_dir: Path,
    tmp_path: Path,
) -> None:
    config = parse_config_data(valid_data, base_dir)
    add_job(connection, build_job, "media", JobStatus.EVALUATED, 70)
    add_job(connection, build_job, "alta", JobStatus.PENDING_QUESTION, 90)
    add_job(connection, build_job, "cv-sumiu", JobStatus.EVALUATED, 80, resume_name="Removido")
    add_job(connection, build_job, "baixa", JobStatus.EVALUATED, 69)
    add_job(connection, build_job, "pendente-baixa", JobStatus.PENDING_QUESTION, 50)
    add_job(connection, build_job, "com-pasta", JobStatus.EVALUATED, 99)
    save_job_folder(connection, "com-pasta", tmp_path / "vagas" / "com-pasta")
    add_job(connection, build_job, "aplicada", JobStatus.APPLIED, 95)
    add_job(connection, build_job, "falhou", JobStatus.FAILED, 95)
    add_job(connection, build_job, "coletada", JobStatus.COLLECTED, None)

    selection = select_normal_candidates(connection, config)

    assert [(candidate.job.id, candidate.score) for candidate in selection.candidates] == [
        ("alta", 90),
        ("cv-sumiu", 80),
        ("media", 70),
    ]
    resumes = {candidate.job.id: candidate.resume_file for candidate in selection.candidates}
    assert resumes["alta"] == base_dir / "cv_base" / "dados.pdf"
    assert resumes["cv-sumiu"] == base_dir / "cv_base" / "backend.docx"
    warnings = {candidate.job.id: candidate.warning for candidate in selection.candidates}
    assert warnings == {
        "alta": None,
        "cv-sumiu": "currículo 'Removido' não está no config.md; usado o padrão 'Back-end'",
        "media": None,
    }
    assert all(candidate.job_answers == {} for candidate in selection.candidates)
    assert [(job.id, reason) for job, reason in selection.ignored] == [("baixa", "score 69 abaixo do mínimo 70")]
    jobs = {job.id: job for job in list_jobs(connection)}
    assert (jobs["baixa"].status, jobs["baixa"].discard_reason) == (JobStatus.IGNORED, "score 69 abaixo do mínimo 70")
    assert jobs["pendente-baixa"].status == JobStatus.PENDING_QUESTION
    assert jobs["media"].status == JobStatus.EVALUATED
