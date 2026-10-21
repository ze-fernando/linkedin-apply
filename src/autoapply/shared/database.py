import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
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

CREATE TABLE IF NOT EXISTS analyses (
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


def open_database(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.executescript(SCHEMA)
    return connection
