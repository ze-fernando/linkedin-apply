import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from autoapply.shared.database import open_database


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = open_database(tmp_path / "autoapply.db")
    yield connection
    connection.close()
