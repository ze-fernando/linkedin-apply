import json
import sqlite3
from datetime import datetime

from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import JOB_COLUMNS, build_job_from_row
from autoapply.modules.matching.models import Analyzer, JobAnalysis

ANALYSIS_COLUMNS = (
    "job_id",
    "resume_name",
    "score",
    "pre_score",
    "summary",
    "requirements",
    "keywords",
    "gap",
    "analyzer",
    "model",
    "analyzed_at",
)
LIST_COLUMNS = ("requirements", "keywords", "gap")


def save_analysis(connection: sqlite3.Connection, analysis: JobAnalysis) -> None:
    fields = {column: getattr(analysis, column) for column in ANALYSIS_COLUMNS}
    for column in LIST_COLUMNS:
        fields[column] = json.dumps(fields[column], ensure_ascii=False)
    fields["analyzed_at"] = analysis.analyzed_at.isoformat()
    placeholders = ", ".join("?" for _ in ANALYSIS_COLUMNS)
    connection.execute(
        f"INSERT OR REPLACE INTO analyses ({', '.join(ANALYSIS_COLUMNS)}) VALUES ({placeholders})",
        list(fields.values()),
    )


def build_analysis_from_row(row: tuple[object, ...]) -> JobAnalysis:
    fields = dict(zip(ANALYSIS_COLUMNS, row))
    for column in LIST_COLUMNS:
        fields[column] = json.loads(fields[column])
    fields["analyzer"] = Analyzer(fields["analyzer"])
    fields["analyzed_at"] = datetime.fromisoformat(fields["analyzed_at"])
    return JobAnalysis(**fields)


def find_analysis(connection: sqlite3.Connection, job_id: str) -> JobAnalysis | None:
    row = connection.execute(
        f"SELECT {', '.join(ANALYSIS_COLUMNS)} FROM analyses WHERE job_id = ?", [job_id]
    ).fetchone()
    return None if row is None else build_analysis_from_row(row)


def list_jobs_by_score(
    connection: sqlite3.Connection, status: JobStatus | None = None
) -> list[tuple[Job, JobAnalysis | None]]:
    job_columns = ", ".join(f"jobs.{column}" for column in JOB_COLUMNS)
    analysis_columns = ", ".join(f"analyses.{column}" for column in ANALYSIS_COLUMNS)
    rows = connection.execute(
        f"SELECT {job_columns}, {analysis_columns} FROM jobs LEFT JOIN analyses ON analyses.job_id = jobs.id "
        "WHERE ? IS NULL OR jobs.status = ? "
        "ORDER BY analyses.score IS NULL, analyses.score DESC, analyses.pre_score DESC, jobs.collected_at, jobs.id",
        [status, status],
    ).fetchall()
    split = len(JOB_COLUMNS)
    return [
        (build_job_from_row(row[:split]), None if row[split] is None else build_analysis_from_row(row[split:]))
        for row in rows
    ]
