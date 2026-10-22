import sqlite3
from datetime import datetime
from pathlib import Path

from autoapply.modules.tailoring.models import TailoredResume, TailoringStatus

TAILORED_RESUME_COLUMNS = ["job_id", "base_resume", "pdf_path", "status", "reason", "provider", "model", "created_at"]


def save_tailored_resume(connection: sqlite3.Connection, tailored: TailoredResume) -> None:
    connection.execute(
        f"INSERT OR REPLACE INTO tailored_resumes ({', '.join(TAILORED_RESUME_COLUMNS)}) "
        f"VALUES ({', '.join('?' for _ in TAILORED_RESUME_COLUMNS)})",
        [
            tailored.job_id,
            str(tailored.base_resume),
            None if tailored.pdf_path is None else str(tailored.pdf_path),
            tailored.status,
            tailored.reason,
            tailored.provider,
            tailored.model,
            tailored.created_at.isoformat(),
        ],
    )


def find_tailored_resume(connection: sqlite3.Connection, job_id: str) -> TailoredResume | None:
    row = connection.execute(
        f"SELECT {', '.join(TAILORED_RESUME_COLUMNS)} FROM tailored_resumes WHERE job_id = ?", [job_id]
    ).fetchone()
    if row is None:
        return None
    job_id, base_resume, pdf_path, status, reason, provider, model, created_at = row
    return TailoredResume(
        job_id=job_id,
        base_resume=Path(base_resume),
        pdf_path=None if pdf_path is None else Path(pdf_path),
        status=TailoringStatus(status),
        reason=reason,
        provider=provider,
        model=model,
        created_at=datetime.fromisoformat(created_at),
    )
