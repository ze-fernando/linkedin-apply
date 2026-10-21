from pathlib import Path

from autoapply.shared.database import open_database


def test_open_database_creates_missing_folder_and_can_be_reopened(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "autoapply.db"

    open_database(database_path).close()
    open_database(database_path).close()

    assert database_path.is_file()
