import json
import sqlite3
from datetime import datetime

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
