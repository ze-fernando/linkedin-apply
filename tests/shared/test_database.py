import sqlite3
from collections.abc import Callable
from pathlib import Path

from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import insert_job, list_jobs, update_job_status
from autoapply.shared.database import open_database

M2_SCHEMA = """
CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  company TEXT NOT NULL,
  location TEXT NOT NULL,
  workplace TEXT,
  posted TEXT,
  description TEXT,
  url TEXT NOT NULL,
  search_term TEXT NOT NULL,
  status TEXT NOT NULL,
  discard_reason TEXT,
  collected_at TEXT NOT NULL
);
CREATE TABLE analyses (
  job_id TEXT PRIMARY KEY REFERENCES jobs(id),
  resume_name TEXT NOT NULL,
  score INTEGER NOT NULL,
  pre_score INTEGER NOT NULL,
  summary TEXT NOT NULL,
  requirements TEXT NOT NULL,
  keywords TEXT NOT NULL,
  gap TEXT NOT NULL,
  analyzer TEXT NOT NULL,
  model TEXT,
  analyzed_at TEXT NOT NULL
);
"""


def test_open_database_creates_missing_folder_and_can_be_reopened(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "autoapply.db"

    open_database(database_path).close()
    open_database(database_path).close()

    assert database_path.is_file()


def test_open_database_upgrades_m2_database_keeping_jobs_and_new_statuses(
    tmp_path: Path, build_job: Callable[..., Job]
) -> None:
    database_path = tmp_path / "autoapply.db"
    old_connection = sqlite3.connect(database_path, autocommit=True)
    old_connection.executescript(M2_SCHEMA)
    old_connection.close()

    connection = open_database(database_path)
    insert_job(connection, build_job(id="antiga"))
    update_job_status(connection, "antiga", JobStatus.PENDING_QUESTION)

    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"jobs", "analyses", "job_folders", "application_attempts", "pending_questions"} <= tables
    assert [job.id for job in list_jobs(connection, JobStatus.PENDING_QUESTION)] == ["antiga"]
    assert [status.value for status in (JobStatus.APPLIED, JobStatus.FAILED)] == ["aplicada", "falhou"]
    connection.close()
