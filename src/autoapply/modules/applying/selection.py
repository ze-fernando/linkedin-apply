import sqlite3
from pathlib import Path

from autoapply.modules.applying.job_folders import find_folder_resumes
from autoapply.modules.applying.models import ApplicationCandidate, FolderJob, NormalSelection
from autoapply.modules.applying.store import list_job_folders
from autoapply.modules.config.models import Config
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import ignore_job
from autoapply.modules.matching.models import JobAnalysis
from autoapply.modules.matching.store import list_jobs_by_score

READY_STATUSES = {JobStatus.AWAITING_RESUME, JobStatus.PENDING_QUESTION}
NORMAL_STATUSES = {JobStatus.EVALUATED, JobStatus.PENDING_QUESTION}


def list_folder_jobs(connection: sqlite3.Connection) -> list[FolderJob]:
    folders = list_job_folders(connection)
    return [
        FolderJob(job=job, folder=folders[job.id], score=None if analysis is None else analysis.score)
        for job, analysis in list_jobs_by_score(connection)
        if job.id in folders
    ]


def find_job_for_argument(connection: sqlite3.Connection, argument: str) -> FolderJob | None:
    folder_name = Path(argument).name
    return next(
        (
            folder_job
            for folder_job in list_folder_jobs(connection)
            if argument == folder_job.job.id or folder_name == folder_job.folder.name
        ),
        None,
    )


def select_ready_jobs(connection: sqlite3.Connection) -> list[FolderJob]:
    return [
        folder_job
        for folder_job in list_folder_jobs(connection)
        if folder_job.job.status in READY_STATUSES and find_folder_resumes(folder_job.folder)
    ]


def build_normal_candidate(config: Config, job: Job, analysis: JobAnalysis) -> ApplicationCandidate:
    resumes = {curriculo.nome: curriculo for curriculo in config.curriculos}
    chosen = resumes.get(analysis.resume_name)
    warning = None
    if chosen is None:
        chosen = next(curriculo for curriculo in config.curriculos if curriculo.padrao)
        warning = f"currículo '{analysis.resume_name}' não está no config.md; usado o padrão '{chosen.nome}'"
    return ApplicationCandidate(
        job=job, resume_file=chosen.arquivo, job_answers={}, score=analysis.score, warning=warning
    )


def select_normal_candidates(connection: sqlite3.Connection, config: Config) -> NormalSelection:
    folders = list_job_folders(connection)
    minimum = config.regras.score_minimo
    candidates = []
    ignored = []
    for job, analysis in list_jobs_by_score(connection):
        if job.id in folders or job.status not in NORMAL_STATUSES or analysis is None:
            continue
        if analysis.score >= minimum:
            candidates.append(build_normal_candidate(config, job, analysis))
        elif job.status == JobStatus.EVALUATED:
            reason = f"score {analysis.score} abaixo do mínimo {minimum}"
            ignore_job(connection, job.id, reason)
            ignored.append((job, reason))
    return NormalSelection(candidates=candidates, ignored=ignored)
