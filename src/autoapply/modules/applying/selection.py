import sqlite3
from pathlib import Path

from autoapply.modules.applying.job_folders import find_folder_resumes
from autoapply.modules.applying.models import FolderJob
from autoapply.modules.applying.store import list_job_folders
from autoapply.modules.jobs.models import JobStatus
from autoapply.modules.matching.store import list_jobs_by_score

READY_STATUSES = {JobStatus.AWAITING_RESUME, JobStatus.PENDING_QUESTION}


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
