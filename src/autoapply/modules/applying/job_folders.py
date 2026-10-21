import re
import sqlite3
from pathlib import Path

from autoapply.modules.applying.models import FolderResume
from autoapply.modules.applying.store import find_job_folder, save_job_folder
from autoapply.modules.jobs.store import find_known_ids
from autoapply.modules.resumes.loader import read_text_and_problem

JOB_LINK_PATTERN = re.compile(r"\*\*Link:\*\*\s+\S*/jobs/view/(\d+)")
JOB_MARKDOWN_FILE = "vaga.md"
FOLDER_RESUME_NAMES = ["cv.docx", "cv.pdf"]
MAX_RESUME_BYTES = 2 * 1024 * 1024


def read_folder_job_id(folder: Path) -> str | None:
    markdown = folder / JOB_MARKDOWN_FILE
    if not markdown.is_file():
        return None
    match = JOB_LINK_PATTERN.search(markdown.read_text(encoding="utf-8"))
    return None if match is None else match.group(1)


def migrate_job_folders(connection: sqlite3.Connection, vagas_dir: Path) -> list[Path]:
    if not vagas_dir.is_dir():
        return []
    candidates = {}
    for folder in sorted(path for path in vagas_dir.iterdir() if path.is_dir()):
        job_id = read_folder_job_id(folder)
        if job_id is not None and find_job_folder(connection, job_id) is None:
            candidates[job_id] = folder
    known = find_known_ids(connection, list(candidates))
    migrated = {job_id: folder for job_id, folder in candidates.items() if job_id in known}
    for job_id, folder in migrated.items():
        save_job_folder(connection, job_id, folder)
    return list(migrated.values())


def find_folder_resumes(folder: Path) -> list[Path]:
    return [folder / name for name in FOLDER_RESUME_NAMES if (folder / name).is_file()]


def check_folder_resume(folder: Path) -> FolderResume:
    found = find_folder_resumes(folder)
    if not found:
        return FolderResume(path=None, problem="sem cv.docx ou cv.pdf na pasta")
    if len(found) > 1:
        return FolderResume(path=None, problem="há cv.docx e cv.pdf na pasta; deixe só um")
    path = found[0]
    if path.stat().st_size > MAX_RESUME_BYTES:
        return FolderResume(path=path, problem=f"{path.name} tem mais de 2 MB")
    _, problem = read_text_and_problem(path)
    return FolderResume(path=path, problem=problem)
