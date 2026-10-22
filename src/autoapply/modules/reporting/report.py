import csv
import sqlite3
from datetime import datetime
from pathlib import Path

from autoapply.modules.applying.models import ApplyMode, AttemptOutcome
from autoapply.modules.jobs.models import JobStatus
from autoapply.modules.reporting.models import Report, ReportEntry
from autoapply.shared.paths import TAILORED_RESUMES_DIR

TOP_FAILURE_REASONS = 3
CSV_HEADER = ["Data", "Modo", "Resultado", "Empresa", "Cargo", "Score", "Currículo", "Arquivo do currículo", "Link"]
DATE_FORMAT = "%Y-%m-%d %H:%M"
PERIOD_FILTER = "(:since IS NULL OR {column} >= :since)"
LAST_ATTEMPTS_QUERY = f"""
SELECT a.job_id, a.attempted_at, a.mode, a.outcome, j.company, j.title, an.score, a.resume_file, j.url
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY attempted_at DESC, id DESC) AS position
  FROM application_attempts
  WHERE {PERIOD_FILTER.format(column="attempted_at")}
) AS a
JOIN jobs AS j ON j.id = a.job_id
LEFT JOIN analyses AS an ON an.job_id = a.job_id
WHERE a.position = 1
ORDER BY a.attempted_at DESC, a.id DESC
"""


def count_attempts(connection: sqlite3.Connection, since: str | None) -> dict[tuple[ApplyMode, AttemptOutcome], int]:
    rows = connection.execute(
        "SELECT mode, outcome, COUNT(*) FROM application_attempts "
        f"WHERE {PERIOD_FILTER.format(column='attempted_at')} GROUP BY mode, outcome",
        {"since": since},
    ).fetchall()
    return {(ApplyMode(mode), AttemptOutcome(outcome)): count for mode, outcome, count in rows}


def count_ignored(connection: sqlite3.Connection, since: str | None) -> int:
    row = connection.execute(
        f"SELECT COUNT(*) FROM jobs WHERE status = :status AND {PERIOD_FILTER.format(column='collected_at')}",
        {"since": since, "status": JobStatus.IGNORED},
    ).fetchone()
    return row[0]


def find_failure_reasons(connection: sqlite3.Connection, since: str | None) -> list[tuple[str, int]]:
    rows = connection.execute(
        "SELECT reason, COUNT(*) AS total FROM application_attempts "
        f"WHERE outcome = :outcome AND reason IS NOT NULL AND {PERIOD_FILTER.format(column='attempted_at')} "
        "GROUP BY reason ORDER BY total DESC, reason LIMIT :limit",
        {"since": since, "outcome": AttemptOutcome.FAILED, "limit": TOP_FAILURE_REASONS},
    ).fetchall()
    return [(reason, total) for reason, total in rows]


def calculate_completion_rate(counts: dict[tuple[ApplyMode, AttemptOutcome], int]) -> float | None:
    totals = {outcome: 0 for outcome in AttemptOutcome}
    for (_, outcome), count in counts.items():
        totals[outcome] += count
    finished = totals[AttemptOutcome.APPLIED] + totals[AttemptOutcome.FAILED] + totals[AttemptOutcome.PENDING]
    return totals[AttemptOutcome.APPLIED] / finished if finished else None


def is_tailored(resume_file: str | None) -> bool:
    return resume_file is not None and Path(resume_file).is_relative_to(TAILORED_RESUMES_DIR)


def list_last_attempts(connection: sqlite3.Connection, since: str | None) -> list[ReportEntry]:
    rows = connection.execute(LAST_ATTEMPTS_QUERY, {"since": since}).fetchall()
    return [
        ReportEntry(
            job_id=job_id,
            attempted_at=datetime.fromisoformat(attempted_at),
            mode=ApplyMode(mode),
            outcome=AttemptOutcome(outcome),
            company=company,
            title=title,
            score=score,
            resume_file=resume_file,
            tailored=is_tailored(resume_file),
            url=url,
        )
        for job_id, attempted_at, mode, outcome, company, title, score, resume_file, url in rows
    ]


def build_report(connection: sqlite3.Connection, since: datetime | None) -> Report:
    since_text = None if since is None else since.isoformat()
    counts = count_attempts(connection, since_text)
    return Report(
        counts=counts,
        ignored=count_ignored(connection, since_text),
        completion_rate=calculate_completion_rate(counts),
        failure_reasons=find_failure_reasons(connection, since_text),
        entries=list_last_attempts(connection, since_text),
    )


def describe_resume_kind(entry: ReportEntry) -> str:
    return "ajustado" if entry.tailored else "base"


def build_csv_row(entry: ReportEntry) -> list[str]:
    return [
        entry.attempted_at.strftime(DATE_FORMAT),
        entry.mode,
        entry.outcome,
        entry.company,
        entry.title,
        "" if entry.score is None else str(entry.score),
        describe_resume_kind(entry),
        entry.resume_file or "",
        entry.url,
    ]


def write_report_csv(entries: list[ReportEntry], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(CSV_HEADER)
        writer.writerows(build_csv_row(entry) for entry in entries)
    return path
