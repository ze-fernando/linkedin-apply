import logging
import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from playwright.sync_api import BrowserContext, Page
from playwright.sync_api import Error as PlaywrightError

from autoapply.modules.config.models import Busca
from autoapply.modules.jobs.filters import find_card_block_reason, find_description_block_reason
from autoapply.modules.jobs.models import Job, JobCard, JobDetail, JobStatus, TermSummary
from autoapply.modules.jobs.parsing import parse_job_cards, parse_job_detail
from autoapply.modules.jobs.search_url import build_search_url
from autoapply.modules.jobs.store import find_known_ids, insert_job
from autoapply.modules.session.browser import read_page_state, save_debug_dump
from autoapply.modules.session.models import CheckpointDetected, PageState, SessionExpired

JOB_VIEW_URL = "https://www.linkedin.com/jobs/view/{job_id}/"
LIST_ITEM_BY_ID_SELECTOR = 'li[data-occludable-job-id="{job_id}"]'
CARD_CLICK_SELECTOR = "[data-job-id]"
PANEL_READY_SELECTOR = '.job-details-jobs-unified-top-card__job-title a[href*="/jobs/view/{job_id}/"]'
NO_EASY_APPLY_REASON = "sem Candidatura simplificada"
LIST_ITEM_SELECTOR = "li[data-occludable-job-id]"
CARD_RENDER_TIMEOUT_MS = 3000
CARD_READ_ATTEMPTS = 3
LIST_GROWTH_POLL_MS = 500
CARD_TITLE_SELECTOR = ".artdeco-entity-lockup__title"
INTERRUPTING_STATES = {PageState.CHECKPOINT: CheckpointDetected, PageState.LOGGED_OUT: SessionExpired}

logger = logging.getLogger("autoapply.jobs")


def build_job(
    card: JobCard, term: str, status: JobStatus, detail: JobDetail | None, discard_reason: str | None
) -> Job:
    return Job(
        id=card.id,
        title=detail.title if detail and detail.title else card.title,
        company=detail.company if detail and detail.company else card.company,
        location=card.location,
        workplace=detail.workplace if detail else None,
        posted=detail.posted if detail else None,
        description=detail.description if detail else None,
        url=JOB_VIEW_URL.format(job_id=card.id),
        search_term=term,
        status=status,
        discard_reason=discard_reason,
        collected_at=datetime.now(),
    )


def ensure_page_is_usable(page: Page) -> None:
    state = read_page_state(page)
    if state in INTERRUPTING_STATES:
        raise INTERRUPTING_STATES[state](page.url)


def read_card_when_visible(page: Page, index: int) -> list[JobCard]:
    for _ in range(CARD_READ_ATTEMPTS):
        item = page.locator(LIST_ITEM_SELECTOR).nth(index)
        try:
            item.scroll_into_view_if_needed(timeout=CARD_RENDER_TIMEOUT_MS)
            item.locator(CARD_TITLE_SELECTOR).wait_for(timeout=CARD_RENDER_TIMEOUT_MS)
            return parse_job_cards(item.inner_html(timeout=CARD_RENDER_TIMEOUT_MS))
        except PlaywrightError:
            continue
    logger.warning("card %d da lista não pôde ser lido", index)
    return []


def render_all_cards(page: Page, list_settle_ms: int) -> list[JobCard]:
    cards = {}
    read_items = 0
    quiet_ms = 0
    while quiet_ms < list_settle_ms:
        item_count = page.locator(LIST_ITEM_SELECTOR).count()
        if item_count > read_items:
            for index in range(read_items, item_count):
                for card in read_card_when_visible(page, index):
                    cards.setdefault(card.id, card)
            read_items = item_count
            quiet_ms = 0
        page.wait_for_timeout(LIST_GROWTH_POLL_MS)
        quiet_ms += LIST_GROWTH_POLL_MS
    return list(cards.values())


def open_job_detail(page: Page, card: JobCard, panel_timeout_ms: int) -> JobDetail:
    item = page.locator(LIST_ITEM_BY_ID_SELECTOR.format(job_id=card.id))
    item.scroll_into_view_if_needed()
    item.locator(CARD_CLICK_SELECTOR).click(timeout=CARD_RENDER_TIMEOUT_MS)
    page.wait_for_selector(PANEL_READY_SELECTOR.format(job_id=card.id), timeout=panel_timeout_ms)
    return parse_job_detail(page.content())


def build_new_job(
    page: Page,
    card: JobCard,
    busca: Busca,
    term: str,
    wait: Callable[[], None],
    debug_dir: Path,
    panel_timeout_ms: int,
) -> Job | None:
    block_reason = find_card_block_reason(card, busca)
    if block_reason is not None:
        return build_job(card, term, JobStatus.IGNORED, None, block_reason)
    wait()
    try:
        detail = open_job_detail(page, card, panel_timeout_ms)
    except PlaywrightError:
        dump_dir = save_debug_dump(page, read_page_state(page), debug_dir)
        logger.warning("vaga %s não abriu; dump em %s", card.id, dump_dir)
        return None
    detail_reason = (
        find_description_block_reason(detail.description, busca) if detail.has_easy_apply else NO_EASY_APPLY_REASON
    )
    status = JobStatus.COLLECTED if detail_reason is None else JobStatus.IGNORED
    return build_job(card, term, status, detail, detail_reason)


def collect_term(
    page: Page,
    busca: Busca,
    term: str,
    connection: sqlite3.Connection,
    wait: Callable[[], None],
    debug_dir: Path,
    panel_timeout_ms: int,
    list_settle_ms: int,
) -> TermSummary:
    page.goto(build_search_url(term, busca), wait_until="domcontentloaded")
    ensure_page_is_usable(page)
    cards = render_all_cards(page, list_settle_ms)
    known_ids = find_known_ids(connection, [card.id for card in cards])
    stored_jobs = []
    for card in cards:
        if card.id in known_ids:
            continue
        job = build_new_job(page, card, busca, term, wait, debug_dir, panel_timeout_ms)
        if job is not None:
            insert_job(connection, job)
            stored_jobs.append(job)
    ignored = sum(job.status == JobStatus.IGNORED for job in stored_jobs)
    logger.info(
        "termo '%s': %d encontradas, %d novas, %d ignoradas",
        term,
        len(cards),
        len(stored_jobs),
        ignored,
        extra={"event": "jobs.term_collected", "term": term},
    )
    return TermSummary(term=term, found=len(cards), new=len(stored_jobs), ignored=ignored)


def collect_jobs(
    context: BrowserContext,
    busca: Busca,
    terms: list[str],
    connection: sqlite3.Connection,
    wait: Callable[[], None],
    debug_dir: Path,
    panel_timeout_ms: int = 15000,
    list_settle_ms: int = 6000,
) -> list[TermSummary]:
    page = context.pages[0]
    summaries = []
    for position, term in enumerate(terms):
        if position > 0:
            wait()
        summaries.append(collect_term(page, busca, term, connection, wait, debug_dir, panel_timeout_ms, list_settle_ms))
    return summaries
