import sqlite3
from datetime import datetime

from autoapply.modules.jobs.models import Job, JobStatus

JOB_COLUMNS = (
    "id",
    "title",
    "company",
    "location",
    "workplace",
    "posted",
    "description",
    "url",
    "search_term",
    "status",
    "discard_reason",
    "collected_at",
)


def insert_job(connection: sqlite3.Connection, job: Job) -> bool:
    values = [getattr(job, column) for column in JOB_COLUMNS]
    values[JOB_COLUMNS.index("collected_at")] = job.collected_at.isoformat()
    placeholders = ", ".join("?" for _ in JOB_COLUMNS)
    cursor = connection.execute(
        f"INSERT OR IGNORE INTO jobs ({', '.join(JOB_COLUMNS)}) VALUES ({placeholders})", values
    )
    return cursor.rowcount == 1


def build_job_from_row(row: tuple[object, ...]) -> Job:
    fields = dict(zip(JOB_COLUMNS, row))
    fields["status"] = JobStatus(fields["status"])
    fields["collected_at"] = datetime.fromisoformat(fields["collected_at"])
    return Job(**fields)


def list_jobs(connection: sqlite3.Connection, status: JobStatus | None = None) -> list[Job]:
    query = f"SELECT {', '.join(JOB_COLUMNS)} FROM jobs WHERE ? IS NULL OR status = ? ORDER BY collected_at, id"
    rows = connection.execute(query, [status, status]).fetchall()
    return [build_job_from_row(row) for row in rows]


def find_known_ids(connection: sqlite3.Connection, job_ids: list[str]) -> set[str]:
    placeholders = ", ".join("?" for _ in job_ids)
    rows = connection.execute(f"SELECT id FROM jobs WHERE id IN ({placeholders})", job_ids).fetchall()
    return {row[0] for row in rows}


def update_job_status(connection: sqlite3.Connection, job_id: str, status: JobStatus) -> None:
    connection.execute("UPDATE jobs SET status = ? WHERE id = ?", [status, job_id])
