import copy
import sqlite3
from collections.abc import Callable, Iterator
from datetime import date, datetime
from pathlib import Path

import pytest

from autoapply.modules.applying.store import find_job_folder
from autoapply.modules.config.loader import parse_config_data
from autoapply.modules.config.models import Config
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import insert_job, list_jobs
from autoapply.modules.matching.models import Analyzer, JobAnalysis
from autoapply.modules.matching.store import save_analysis
from autoapply.modules.search_mode.folders import create_job_folders
from autoapply.shared.database import open_database

TODAY = date(2026, 10, 21)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = open_database(tmp_path / "autoapply.db")
    yield connection
    connection.close()


@pytest.fixture
def config(valid_data: dict[str, object], base_dir: Path) -> Config:
    data = copy.deepcopy(valid_data)
    data["regras"]["modo_busca_quantidade"] = 2
    return parse_config_data(data, base_dir)


@pytest.fixture
def store_evaluated_job(connection: sqlite3.Connection, build_job: Callable[..., Job]) -> Callable[[str, int], None]:
    def store(job_id: str, score: int) -> None:
        insert_job(connection, build_job(id=job_id, company=f"Empresa {job_id}", status=JobStatus.EVALUATED))
        save_analysis(
            connection,
            JobAnalysis(
                job_id=job_id,
                resume_name="Back-end",
                score=score,
                pre_score=score,
                summary="Resumo.",
                requirements=["C#"],
                keywords=["C#"],
                gap=[],
                analyzer=Analyzer.CLAUDE,
                model="sonnet",
                analyzed_at=datetime(2026, 10, 21, 16, 0, 0),
            ),
        )

    return store


def test_create_job_folders_writes_top_scores_and_never_repeats_them(
    connection: sqlite3.Connection,
    config: Config,
    store_evaluated_job: Callable[[str, int], None],
    build_job: Callable[..., Job],
    tmp_path: Path,
) -> None:
    vagas_dir = tmp_path / "vagas"
    store_evaluated_job("media", 50)
    store_evaluated_job("alta", 90)
    store_evaluated_job("boa", 70)
    insert_job(connection, build_job(id="cortada", status=JobStatus.IGNORED))

    first = create_job_folders(connection, config, vagas_dir, TODAY)

    assert [folder.name for folder in first] == [
        "2026-10-21-empresa-alta-desenvolvedor-net-pleno",
        "2026-10-21-empresa-boa-desenvolvedor-net-pleno",
    ]
    assert (first[0] / "vaga.md").read_text(encoding="utf-8").startswith("# Desenvolvedor .NET Pleno — Empresa alta\n")
    assert {job.id for job in list_jobs(connection, JobStatus.AWAITING_RESUME)} == {"alta", "boa"}

    second = create_job_folders(connection, config, vagas_dir, TODAY)

    assert [folder.name for folder in second] == ["2026-10-21-empresa-media-desenvolvedor-net-pleno"]
    assert {job.id for job in list_jobs(connection, JobStatus.AWAITING_RESUME)} == {"alta", "boa", "media"}
    assert sorted(path.name for path in vagas_dir.iterdir()) == sorted(folder.name for folder in first + second)


def test_create_job_folders_records_folder_and_writes_answers_template(
    connection: sqlite3.Connection, config: Config, store_evaluated_job: Callable[[str, int], None], tmp_path: Path
) -> None:
    store_evaluated_job("alta", 90)

    [folder] = create_job_folders(connection, config, tmp_path / "vagas", TODAY)

    assert find_job_folder(connection, "alta") == folder
    assert find_job_folder(connection, "outra") is None
    assert (folder / "respostas.md").read_text(encoding="utf-8") == (
        "# Respostas desta vaga\n"
        "\n"
        "Respostas usadas só nesta vaga, com prioridade sobre o `config.md`.\n"
        "Linhas especiais: `pretensão salarial` (valor da pretensão) e\n"
        "`mensagem` (texto livre no lugar da resposta genérica).\n"
        "\n"
        "| Pergunta | Resposta |\n"
        "| -------- | -------- |\n"
    )
