import sqlite3
from collections.abc import Callable
from pathlib import Path

from autoapply.modules.applying.job_folders import migrate_job_folders
from autoapply.modules.applying.store import find_job_folder, save_job_folder
from autoapply.modules.jobs.models import Job
from autoapply.modules.jobs.store import insert_job


def write_job_markdown(vagas_dir: Path, name: str, job_id: str) -> Path:
    folder = vagas_dir / name
    folder.mkdir(parents=True)
    (folder / "vaga.md").write_text(
        f"# Dev — Empresa\n\n- **Link:** https://www.linkedin.com/jobs/view/{job_id}/\n- **Local:** Brasil\n",
        encoding="utf-8",
    )
    return folder


def test_migrate_job_folders_registers_old_folders_by_the_link_in_vaga_md(
    connection: sqlite3.Connection, tmp_path: Path, build_job: Callable[..., Job]
) -> None:
    vagas_dir = tmp_path / "vagas"
    for job_id in ["111", "222", "333"]:
        insert_job(connection, build_job(id=job_id, url=f"https://www.linkedin.com/jobs/view/{job_id}/"))
    old = write_job_markdown(vagas_dir, "2026-10-21-empresa-a-dev", "111")
    registered = write_job_markdown(vagas_dir, "2026-10-21-empresa-b-dev", "222")
    save_job_folder(connection, "222", registered)
    unknown = write_job_markdown(vagas_dir, "2026-10-21-empresa-c-dev", "999")
    (vagas_dir / "sem-vaga-md").mkdir()

    migrated = migrate_job_folders(connection, vagas_dir)

    assert migrated == [old]
    assert find_job_folder(connection, "111") == old
    assert find_job_folder(connection, "222") == registered
    assert find_job_folder(connection, "999") is None
    assert unknown.exists()
    assert migrate_job_folders(connection, vagas_dir) == []


def test_migrate_job_folders_does_nothing_without_vagas_dir(connection: sqlite3.Connection, tmp_path: Path) -> None:
    assert migrate_job_folders(connection, tmp_path / "vagas") == []
