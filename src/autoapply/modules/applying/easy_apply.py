import logging
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from autoapply.modules.applying.answering import decide_with_answer, resolve_field
from autoapply.modules.applying.form_parsing import (
    ACTION_SELECTORS,
    FOLLOW_COMPANY_SELECTOR,
    RESUME_UPLOAD_SELECTOR,
    parse_form_step,
)
from autoapply.modules.applying.models import (
    AnswerContext,
    AnswerSource,
    ApplicationOutcome,
    ApplicationResult,
    DecisionAction,
    FieldDecision,
    FieldKind,
    FormField,
    FormStep,
    StepAction,
)
from autoapply.modules.jobs.collector import ensure_page_is_usable
from autoapply.modules.jobs.models import Job
from autoapply.modules.session.browser import save_debug_dump
from autoapply.shared.text import normalize_text

SEARCH_JOB_URL = "https://www.linkedin.com/jobs/search/?currentJobId={job_id}"
PANEL_READY_SELECTOR = '.job-details-jobs-unified-top-card__job-title a[href*="/jobs/view/{job_id}/"]'
APPLY_BUTTON_SELECTOR = "button.jobs-apply-button"
EASY_APPLY_LABEL = "candidatura simplificada"
APPLIED_FEEDBACK_SELECTOR = ".jobs-s-apply .artdeco-inline-feedback--success"
APPLIED_FEEDBACK_PATTERN = re.compile(r"candidatura enviada|candidatou-se|applied|solicitud enviada", re.IGNORECASE)
MODAL_SELECTOR = ".jobs-easy-apply-modal"
CLOSE_SELECTOR = f"{MODAL_SELECTOR} button[data-test-modal-close-btn]"
DISCARD_SELECTOR = 'button[data-control-name="discard_application_confirm_btn"]'
RADIO_OPTION_SELECTOR = '[id="{group_id}"] input[data-test-text-selectable-option__input="{option}"]'
SUCCESS_PATTERN = (
    r"candidatura .{0,150}foi enviada|candidatura enviada|application .{0,150}was sent|solicitud .{0,150}enviada"
)
MAX_STEPS = 12
SUGGESTION_SELECTOR = '[role="listbox"] [role="option"]'
SUGGESTION_POLL_MS = 250
TYPING_DELAY_MS = 50
TEXT_KINDS = {FieldKind.TEXT, FieldKind.NUMBER, FieldKind.PHONE, FieldKind.FREE_TEXT}
SELECT_KINDS = {FieldKind.SELECT, FieldKind.PHONE_COUNTRY}
ANSWERED_ACTIONS = {DecisionAction.FILL, DecisionAction.KEEP}
SYNC_FORM_STATE_SCRIPT = """
(modal) => {
  for (const element of modal.querySelectorAll("input, textarea, select")) {
    if (element.type === "radio" || element.type === "checkbox") {
      if (element.checked) element.setAttribute("data-autoapply-checked", "true");
      else element.removeAttribute("data-autoapply-checked");
    } else if (element.tagName === "SELECT") {
      const selected = element.options[element.selectedIndex];
      element.setAttribute("data-autoapply-value", selected ? selected.text : "");
    } else if (element.type !== "file") {
      element.setAttribute("data-autoapply-value", element.value);
    }
  }
  return modal.outerHTML;
}
"""
MODAL_CHANGED_SCRIPT = """
([selector, before]) => {
  const modal = document.querySelector(selector);
  return !modal || modal.innerHTML !== before;
}
"""
DIALOGS_HTML_SCRIPT = """
() => [...document.querySelectorAll("[role=dialog]")].map((dialog) => dialog.outerHTML).join("\\n")
"""
SUCCESS_SCRIPT = f"""
() => [...document.querySelectorAll("[role=dialog]")].some((dialog) => /{SUCCESS_PATTERN}/i.test(dialog.innerText))
"""

logger = logging.getLogger("autoapply.applying")


def result(
    outcome: ApplicationOutcome, reason: str | None = None, pending_fields: list[FormField] | None = None
) -> ApplicationResult:
    return ApplicationResult(outcome=outcome, reason=reason, pending_fields=pending_fields or [])


def element_selector(element_id: str) -> str:
    return f'[id="{element_id}"]'


def read_current_step(page: Page) -> FormStep:
    return parse_form_step(page.locator(MODAL_SELECTOR).first.evaluate(SYNC_FORM_STATE_SCRIPT))


def find_suggestion_index(texts: list[str], city: str) -> int | None:
    wanted = normalize_text(city).strip()
    return next(
        (index for index, text in enumerate(texts) if normalize_text(text.split(",")[0]).strip() == wanted), None
    )


def fill_location(page: Page, field: FormField, city: str, timeout_ms: int) -> str | None:
    element = page.locator(element_selector(field.element_id))
    element.fill("")
    element.press_sequentially(city, delay=TYPING_DELAY_MS)
    suggestions = page.locator(SUGGESTION_SELECTOR)
    for _ in range(max(timeout_ms // SUGGESTION_POLL_MS, 1)):
        page.wait_for_timeout(SUGGESTION_POLL_MS)
        index = find_suggestion_index(suggestions.all_inner_texts(), city)
        if index is not None:
            suggestions.nth(index).click()
            return None
    return f"cidade '{city}' fora das sugestões"


def fill_field(page: Page, field: FormField, value: str, timeout_ms: int) -> str | None:
    if field.kind == FieldKind.LOCATION:
        return fill_location(page, field, value, timeout_ms)
    if field.kind in TEXT_KINDS:
        page.locator(element_selector(field.element_id)).fill(value)
    elif field.kind in SELECT_KINDS:
        page.locator(element_selector(field.element_id)).select_option(label=value)
    elif field.kind == FieldKind.RADIO:
        option = page.locator(RADIO_OPTION_SELECTOR.format(group_id=field.element_id, option=value))
        page.locator(f'label[for="{option.get_attribute("id")}"]').click()


def log_decision(field: FormField, decision: FieldDecision) -> None:
    logger.debug(
        "campo '%s': %s → %s (%s)",
        field.label,
        decision.action,
        decision.value,
        decision.source or decision.reason,
        extra={"event": "applying.field_decided"},
    )


def fill_step(
    page: Page, decisions: list[tuple[FormField, FieldDecision]], timeout_ms: int
) -> list[tuple[FormField, str]]:
    problems = []
    for field, decision in decisions:
        if decision.action == DecisionAction.FILL and decision.value != field.value:
            problem = fill_field(page, field, decision.value, timeout_ms)
            if problem is not None:
                problems.append((field, problem))
    return problems


def prepare_step(page: Page, step: FormStep, resume_file: Path) -> None:
    if step.has_resume_upload:
        page.locator(RESUME_UPLOAD_SELECTOR).set_input_files(resume_file)
    if step.has_follow_company and page.locator(FOLLOW_COMPANY_SELECTOR).is_checked():
        page.locator(f'label[for="{FOLLOW_COMPANY_SELECTOR[1:]}"]').click()


def discard_application(page: Page, timeout_ms: int) -> None:
    try:
        page.locator(CLOSE_SELECTOR).first.click(timeout=timeout_ms)
        page.locator(DISCARD_SELECTOR).click(timeout=timeout_ms)
    except PlaywrightError as error:
        logger.warning("não foi possível descartar o rascunho: %s", error)


def fail(
    page: Page, job: Job, reason: str, debug_dir: Path, timeout_ms: int, discard: bool = True
) -> ApplicationResult:
    dump_dir = save_debug_dump(page, f"falha-{job.id}", debug_dir)
    logger.warning("candidatura falhou: %s; dump em %s", reason, dump_dir)
    if discard:
        discard_application(page, timeout_ms)
    return result(ApplicationOutcome.FAILED, reason)


def save_success_dialog(page: Page, job: Job, debug_dir: Path) -> None:
    dump_dir = debug_dir / f"{datetime.now():%Y%m%d-%H%M%S}-sucesso-{job.id}"
    dump_dir.mkdir(parents=True, exist_ok=True)
    (dump_dir / "dialog.html").write_text(page.evaluate(DIALOGS_HTML_SCRIPT), encoding="utf-8")


def submit_application(page: Page, job: Job, debug_dir: Path, timeout_ms: int) -> ApplicationResult:
    page.locator(ACTION_SELECTORS[StepAction.SUBMIT]).click(timeout=timeout_ms)
    try:
        page.wait_for_function(SUCCESS_SCRIPT, timeout=timeout_ms)
    except PlaywrightError:
        reason = "sem confirmação de envio; confira à mão no LinkedIn"
        return fail(page, job, reason, debug_dir, timeout_ms, discard=False)
    save_success_dialog(page, job, debug_dir)
    return result(ApplicationOutcome.APPLIED)


def advance(page: Page, action: StepAction, wait: Callable[[], None], timeout_ms: int) -> None:
    before = page.locator(MODAL_SELECTOR).first.inner_html()
    wait()
    page.locator(ACTION_SELECTORS[action]).click(timeout=timeout_ms)
    page.wait_for_function(MODAL_CHANGED_SCRIPT, arg=[MODAL_SELECTOR, before], timeout=timeout_ms)


def is_already_applied(page: Page) -> bool:
    feedback = page.locator(APPLIED_FEEDBACK_SELECTOR).first
    return feedback.count() > 0 and APPLIED_FEEDBACK_PATTERN.search(feedback.inner_text()) is not None


def open_application(page: Page, job: Job, timeout_ms: int) -> ApplicationResult | None:
    page.goto(SEARCH_JOB_URL.format(job_id=job.id), wait_until="domcontentloaded")
    ensure_page_is_usable(page)
    page.wait_for_selector(PANEL_READY_SELECTOR.format(job_id=job.id), timeout=timeout_ms)
    if is_already_applied(page):
        return result(ApplicationOutcome.ALREADY_APPLIED, "o LinkedIn já mostra candidatura enviada")
    apply_button = page.locator(APPLY_BUTTON_SELECTOR).first
    if apply_button.count() == 0 or EASY_APPLY_LABEL not in apply_button.inner_text().casefold():
        return result(ApplicationOutcome.FAILED, "sem botão Candidatura simplificada")
    apply_button.click(timeout=timeout_ms)
    page.wait_for_selector(MODAL_SELECTOR, timeout=timeout_ms)
    return None


def ask_until_valid(
    job: Job, field: FormField, decision: FieldDecision, ask_field: Callable[[Job, FormField], str | None]
) -> FieldDecision:
    while decision.action == DecisionAction.PENDING:
        answer = ask_field(job, field)
        if answer is None:
            return decision
        decision = decide_with_answer(field, answer, AnswerSource.USER)
    return decision


def list_answers(decisions: list[tuple[FormField, FieldDecision]]) -> list[tuple[str, str]]:
    return [
        (field.label, decision.value)
        for field, decision in decisions
        if decision.action in ANSWERED_ACTIONS and decision.value is not None
    ]


def apply_to_job(
    page: Page,
    job: Job,
    resume_file: Path,
    context: AnswerContext,
    simulate: bool,
    confirm_submit: Callable[[Job, list[tuple[str, str]]], bool],
    ask_field: Callable[[Job, FormField], str | None],
    wait: Callable[[], None],
    debug_dir: Path,
    timeout_ms: int = 15000,
) -> ApplicationResult:
    blocked = open_application(page, job, timeout_ms)
    if blocked is not None:
        return blocked
    answers = []
    for _ in range(MAX_STEPS):
        step = read_current_step(page)
        if step.errors:
            return fail(page, job, f"erro de validação: {'; '.join(step.errors)}", debug_dir, timeout_ms)
        decisions = [
            (field, ask_until_valid(job, field, resolve_field(field, context), ask_field)) for field in step.fields
        ]
        for field, decision in decisions:
            log_decision(field, decision)
        failure = next((decision for _, decision in decisions if decision.action == DecisionAction.FAIL), None)
        if failure is not None:
            return fail(page, job, failure.reason, debug_dir, timeout_ms)
        pending_fields = [field for field, decision in decisions if decision.action == DecisionAction.PENDING]
        if pending_fields:
            discard_application(page, timeout_ms)
            return result(ApplicationOutcome.PENDING, "perguntas sem resposta", pending_fields)
        unfilled = fill_step(page, decisions, timeout_ms)
        if unfilled:
            discard_application(page, timeout_ms)
            reason = "; ".join(problem for _, problem in unfilled)
            return result(ApplicationOutcome.PENDING, reason, [field for field, _ in unfilled])
        answers.extend(list_answers(decisions))
        prepare_step(page, step, resume_file)
        if step.action is None:
            return fail(page, job, "etapa sem botão de avançar ou enviar", debug_dir, timeout_ms)
        if step.action == StepAction.SUBMIT and simulate:
            discard_application(page, timeout_ms)
            return result(ApplicationOutcome.SIMULATED)
        if step.action == StepAction.SUBMIT and not confirm_submit(job, answers):
            discard_application(page, timeout_ms)
            return result(ApplicationOutcome.DECLINED)
        if step.action == StepAction.SUBMIT:
            return submit_application(page, job, debug_dir, timeout_ms)
        advance(page, step.action, wait, timeout_ms)
    return fail(page, job, "formulário com etapas demais", debug_dir, timeout_ms)
