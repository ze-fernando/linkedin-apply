import copy
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext

from autoapply.modules.config.models import Busca
from autoapply.modules.jobs.collector import collect_jobs
from autoapply.modules.jobs.models import JobStatus, TermSummary
from autoapply.modules.jobs.store import list_jobs
from autoapply.modules.session.models import CheckpointDetected, SessionExpired
from autoapply.shared.database import open_database
from tests.fakes.linkedin_jobs import FakeJob


@pytest.fixture
def busca(valid_data: dict[str, object]) -> Busca:
    data = copy.deepcopy(valid_data["busca"])
    data["palavras_bloqueadas"] = ["presencial"]
    return Busca.model_validate(data)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with open_database(tmp_path / "autoapply.db") as database:
        yield database


def run_collection(
    browser_context: BrowserContext, busca: Busca, connection: sqlite3.Connection, tmp_path: Path, terms: list[str]
) -> list[TermSummary]:
    return collect_jobs(
        browser_context, busca, terms, connection, wait=lambda: None,
        debug_dir=tmp_path / "debug",
        panel_timeout_ms=2000,
        list_settle_ms=2500,
    )


def test_collect_jobs_stores_good_job_and_ignores_blocked_title(
    browser_context: BrowserContext,
    serve_search_page: Callable[..., None],
    busca: Busca,
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    serve_search_page([FakeJob("1001", "Desenvolvedor .NET Pleno"), FakeJob("1002", "Desenvolvedor C# Sênior")])

    summaries = run_collection(browser_context, busca, connection, tmp_path, ["Desenvolvedor .NET"])

    assert summaries == [TermSummary(term="Desenvolvedor .NET", found=2, new=2, ignored=1)]
    collected, ignored = list_jobs(connection)
    assert (collected.id, collected.status, collected.description) == (
        "1001",
        JobStatus.COLLECTED,
        "Vaga para C# e ASP.NET Core.",
    )
    assert (collected.title, collected.company, collected.search_term) == (
        "Desenvolvedor .NET Pleno",
        "Empresa Alfa",
        "Desenvolvedor .NET",
    )
    assert collected.url == "https://www.linkedin.com/jobs/view/1001/"
    assert (ignored.id, ignored.status, ignored.discard_reason) == ("1002", JobStatus.IGNORED, "título contém 'Sênior'")


def test_collect_jobs_ignores_job_without_easy_apply(
    browser_context: BrowserContext,
    serve_search_page: Callable[..., None],
    busca: Busca,
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    serve_search_page([FakeJob("1001", "Desenvolvedor .NET"), FakeJob("1002", "Desenvolvedor C#", easy_apply=False)])

    summaries = run_collection(browser_context, busca, connection, tmp_path, ["Desenvolvedor .NET"])

    assert summaries[0].ignored == 1
    [ignored] = list_jobs(connection, status=JobStatus.IGNORED)
    assert (ignored.id, ignored.discard_reason) == ("1002", "sem Candidatura simplificada")


def test_collect_jobs_ignores_job_with_blocked_word_in_description(
    browser_context: BrowserContext,
    serve_search_page: Callable[..., None],
    busca: Busca,
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    serve_search_page([FakeJob("1001", "Desenvolvedor .NET", description="Trabalho presencial em Recife.")])

    run_collection(browser_context, busca, connection, tmp_path, ["Desenvolvedor .NET"])

    [ignored] = list_jobs(connection)
    assert (ignored.status, ignored.discard_reason) == (JobStatus.IGNORED, "descrição contém 'presencial'")
    assert ignored.description == "Trabalho presencial em Recife."


def test_collect_jobs_second_run_skips_known_jobs(
    browser_context: BrowserContext,
    serve_search_page: Callable[..., None],
    busca: Busca,
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    serve_search_page([FakeJob("1001", "Desenvolvedor .NET"), FakeJob("1002", "Desenvolvedor C# Sênior")])
    run_collection(browser_context, busca, connection, tmp_path, ["Desenvolvedor .NET"])
    waits = []

    summaries = collect_jobs(
        browser_context,
        busca,
        ["Desenvolvedor .NET"],
        connection,
        wait=lambda: waits.append(True),
        debug_dir=tmp_path / "debug",
        panel_timeout_ms=2000,
        list_settle_ms=2500,
    )

    assert summaries == [TermSummary(term="Desenvolvedor .NET", found=2, new=0, ignored=0)]
    assert waits == []
    assert [job.id for job in list_jobs(connection)] == ["1001", "1002"]


def test_collect_jobs_scrolls_list_to_render_every_card(
    browser_context: BrowserContext,
    serve_search_page: Callable[..., None],
    busca: Busca,
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    jobs = [FakeJob(str(1000 + number), f"Desenvolvedor .NET {number}") for number in range(8)]
    serve_search_page(jobs, rendered_cards=2)

    summaries = run_collection(browser_context, busca, connection, tmp_path, ["Desenvolvedor .NET"])

    assert summaries[0].found == 8
    assert [job.id for job in list_jobs(connection, status=JobStatus.COLLECTED)] == [job.id for job in jobs]


@pytest.mark.parametrize(
    ("page_name", "expected_error"), [("feed_captcha.html", CheckpointDetected), ("login_form.html", SessionExpired)]
)
def test_collect_jobs_stops_when_search_shows_checkpoint_or_login(
    page_name: str,
    expected_error: type[Exception],
    browser_context: BrowserContext,
    serve_pages: Callable[[dict[str, str]], None],
    read_page: Callable[[str], str],
    busca: Busca,
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    serve_pages({"/jobs/search/": read_page(page_name)})

    with pytest.raises(expected_error):
        run_collection(browser_context, busca, connection, tmp_path, ["Desenvolvedor .NET", "Desenvolvedor C#"])

    assert list_jobs(connection) == []


def test_collect_jobs_dumps_panel_that_never_loads_and_continues(
    browser_context: BrowserContext,
    serve_search_page: Callable[..., None],
    busca: Busca,
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    serve_search_page([FakeJob("1001", "Desenvolvedor .NET", panel_loads=False), FakeJob("1002", "Desenvolvedor C#")])

    summaries = run_collection(browser_context, busca, connection, tmp_path, ["Desenvolvedor .NET"])

    assert [job.id for job in list_jobs(connection)] == ["1002"]
    assert summaries[0].new == 1
    [dump_dir] = (tmp_path / "debug").iterdir()
    assert dump_dir.name.endswith("-vaga-nao-abriu-1001")
    assert (dump_dir / "screenshot.png").is_file()
    assert (dump_dir / "page.html").is_file()


def test_collect_jobs_waits_before_each_opened_job_and_between_terms(
    browser_context: BrowserContext,
    serve_search_page: Callable[..., None],
    busca: Busca,
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    serve_search_page([FakeJob("1001", "Desenvolvedor .NET"), FakeJob("1002", "Desenvolvedor C#")])
    waits = []

    collect_jobs(
        browser_context,
        busca,
        ["Desenvolvedor .NET", "Desenvolvedor C#"],
        connection,
        wait=lambda: waits.append(True),
        debug_dir=tmp_path / "debug",
        panel_timeout_ms=2000,
        list_settle_ms=2500,
    )

    assert len(waits) == 3


def test_collect_jobs_waits_for_list_items_added_after_page_load(
    browser_context: BrowserContext,
    serve_search_page: Callable[..., None],
    busca: Busca,
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    jobs = [FakeJob(str(1000 + number), f"Desenvolvedor .NET {number}") for number in range(6)]
    serve_search_page(jobs, rendered_cards=2, initial_items=2)

    summaries = run_collection(browser_context, busca, connection, tmp_path, ["Desenvolvedor .NET"])

    assert summaries[0].found == 6
