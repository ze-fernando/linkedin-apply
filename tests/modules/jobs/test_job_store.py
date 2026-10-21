from collections.abc import Callable
from pathlib import Path

from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import find_known_ids, insert_job, list_jobs, update_job_status
from autoapply.shared.database import open_database


def test_inserted_job_is_listed_with_all_fields_after_reopening(
    tmp_path: Path, build_job: Callable[..., Job]
) -> None:
    database_path = tmp_path / "autoapply.db"
    job = build_job()
    with open_database(database_path) as connection:
        insert_job(connection, job)

    with open_database(database_path) as connection:
        assert list_jobs(connection) == [job]


def test_inserting_known_job_id_keeps_original_and_returns_false(
    tmp_path: Path, build_job: Callable[..., Job]
) -> None:
    original = build_job()
    with open_database(tmp_path / "autoapply.db") as connection:
        first_insert = insert_job(connection, original)
        second_insert = insert_job(connection, build_job(title="Título alterado"))

        assert (first_insert, second_insert) == (True, False)
        assert list_jobs(connection) == [original]


def test_find_known_ids_returns_only_ids_already_stored(tmp_path: Path, build_job: Callable[..., Job]) -> None:
    with open_database(tmp_path / "autoapply.db") as connection:
        insert_job(connection, build_job(id="111"))
        insert_job(connection, build_job(id="222"))

        assert find_known_ids(connection, ["222", "333", "111"]) == {"111", "222"}
        assert find_known_ids(connection, []) == set()


def test_update_job_status_changes_which_jobs_are_listed_by_status(
    tmp_path: Path, build_job: Callable[..., Job]
) -> None:
    with open_database(tmp_path / "autoapply.db") as connection:
        insert_job(connection, build_job(id="111"))
        insert_job(connection, build_job(id="222"))

        update_job_status(connection, "222", JobStatus.AWAITING_RESUME)

        assert [job.id for job in list_jobs(connection, status=JobStatus.COLLECTED)] == ["111"]
        assert [job.id for job in list_jobs(connection, status=JobStatus.AWAITING_RESUME)] == ["222"]
        assert [job.id for job in list_jobs(connection)] == ["111", "222"]


def test_inserted_job_survives_connection_closed_without_commit(
    tmp_path: Path, build_job: Callable[..., Job]
) -> None:
    database_path = tmp_path / "autoapply.db"
    connection = open_database(database_path)
    insert_job(connection, build_job())
    connection.close()

    with open_database(database_path) as reopened:
        assert [job.id for job in list_jobs(reopened)] == ["4481248162"]
