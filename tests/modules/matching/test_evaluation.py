import copy
import json
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from autoapply.modules.config.loader import parse_config_data
from autoapply.modules.config.models import Config
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import insert_job, list_jobs
from autoapply.modules.matching.evaluation import evaluate_jobs
from autoapply.modules.matching.models import Analyzer, EvaluationSummary
from autoapply.modules.matching.store import find_analysis
from autoapply.modules.resumes.models import Resume
from autoapply.shared.database import open_database

RESUMES = [
    Resume(name="Back-end", path=Path("backend.docx"), is_default=True, searches=[], text="Python, Django e SQL.", problem=None),
    Resume(name="Dados", path=Path("dados.pdf"), is_default=False, searches=[], text="SQL e Power BI.", problem=None),
]
LLM_ANSWER = {
    "curriculo": "Dados",
    "score": 77,
    "resumo": "Boa aderência em SQL.",
    "requisitos": ["SQL"],
    "palavras_chave": ["SQL"],
    "gap": ["Python"],
}


def claude_output(structured_output: object) -> str:
    return json.dumps({"type": "result", "is_error": False, "structured_output": structured_output})


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = open_database(tmp_path / "autoapply.db")
    yield connection
    connection.close()


@pytest.fixture
def build_config(valid_data: dict[str, object], base_dir: Path) -> Callable[[int], Config]:
    def build(max_llm_jobs: int) -> Config:
        data = copy.deepcopy(valid_data)
        data["regras"]["analise_llm_max_vagas"] = max_llm_jobs
        return parse_config_data(data, base_dir)

    return build


@pytest.fixture
def store_jobs(connection: sqlite3.Connection, build_job: Callable[..., Job]) -> Callable[..., None]:
    def store(*jobs: tuple[str, str, JobStatus]) -> None:
        for job_id, description, status in jobs:
            insert_job(connection, build_job(id=job_id, description=description, status=status))

    return store


def test_evaluate_jobs_sends_best_pre_scores_to_llm_and_the_rest_to_keywords(
    connection: sqlite3.Connection,
    build_config: Callable[[int], Config],
    store_jobs: Callable[..., None],
    install_fake_cli: Callable[..., None],
) -> None:
    install_fake_cli("claude", claude_output(LLM_ANSWER))
    store_jobs(("fraca", "Java e Python.", JobStatus.COLLECTED), ("forte", "Python e SQL.", JobStatus.COLLECTED))

    summary = evaluate_jobs(connection, build_config(1), RESUMES, ["claude"])

    assert summary == EvaluationSummary(llm=1, keywords=1)
    strong = find_analysis(connection, "forte")
    assert (strong.analyzer, strong.model, strong.resume_name, strong.score, strong.pre_score) == (
        Analyzer.CLAUDE,
        "sonnet",
        "Dados",
        77,
        50,
    )
    assert (strong.summary, strong.requirements, strong.keywords, strong.gap) == (
        "Boa aderência em SQL.",
        ["SQL"],
        ["SQL"],
        ["Python"],
    )
    weak = find_analysis(connection, "fraca")
    assert (weak.analyzer, weak.model, weak.resume_name, weak.score) == (Analyzer.KEYWORDS, None, "Back-end", 50)
    assert {job.id for job in list_jobs(connection, JobStatus.EVALUATED)} == {"fraca", "forte"}


def test_evaluate_jobs_falls_back_to_keywords_when_llm_fails(
    connection: sqlite3.Connection,
    build_config: Callable[[int], Config],
    store_jobs: Callable[..., None],
    install_fake_cli: Callable[..., None],
) -> None:
    install_fake_cli("claude", "falhou", exit_code=1)
    store_jobs(("forte", "Python e SQL.", JobStatus.COLLECTED))

    summary = evaluate_jobs(connection, build_config(30), RESUMES, ["claude"])

    assert summary == EvaluationSummary(llm=0, keywords=1)
    analysis = find_analysis(connection, "forte")
    assert (analysis.analyzer, analysis.resume_name, analysis.score) == (Analyzer.KEYWORDS, "Back-end", 100)
    assert [job.id for job in list_jobs(connection, JobStatus.EVALUATED)] == ["forte"]


def test_evaluate_jobs_never_reanalyzes_and_skips_ignored_jobs(
    connection: sqlite3.Connection,
    build_config: Callable[[int], Config],
    store_jobs: Callable[..., None],
    install_fake_cli: Callable[..., None],
    fake_cli_dir: Path,
) -> None:
    install_fake_cli("claude", claude_output(LLM_ANSWER))
    store_jobs(("forte", "Python e SQL.", JobStatus.COLLECTED), ("cortada", "Python.", JobStatus.IGNORED))
    evaluate_jobs(connection, build_config(30), RESUMES, ["claude"])
    first_analysis = find_analysis(connection, "forte")

    summary = evaluate_jobs(connection, build_config(30), RESUMES, ["claude"])

    assert summary == EvaluationSummary(llm=0, keywords=0)
    assert find_analysis(connection, "forte") == first_analysis
    assert find_analysis(connection, "cortada") is None
    assert len((fake_cli_dir / "claude.calls").read_text(encoding="utf-8").splitlines()) == 1
    assert [job.id for job in list_jobs(connection, JobStatus.IGNORED)] == ["cortada"]


def test_evaluate_jobs_uses_keywords_for_everything_without_providers(
    connection: sqlite3.Connection, build_config: Callable[[int], Config], store_jobs: Callable[..., None]
) -> None:
    store_jobs(("forte", "Python e SQL.", JobStatus.COLLECTED), ("fraca", "Java e Python.", JobStatus.COLLECTED))

    summary = evaluate_jobs(connection, build_config(30), RESUMES, [])

    assert summary == EvaluationSummary(llm=0, keywords=2)
    assert {find_analysis(connection, job_id).analyzer for job_id in ("forte", "fraca")} == {Analyzer.KEYWORDS}
