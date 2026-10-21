import logging
import re
from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from autoapply.modules.applying.answering import resolve_field
from autoapply.modules.applying.form_parsing import (
    ACTION_SELECTORS,
    FOLLOW_COMPANY_SELECTOR,
    RESUME_UPLOAD_SELECTOR,
    parse_form_step,
)
from autoapply.modules.applying.models import (
    AnswerContext,
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
from autoapply.modules.session.browser import read_page_state, save_debug_dump

SEARCH_JOB_URL = "https://www.linkedin.com/jobs/search/?currentJobId={job_id}"
PANEL_READY_SELECTOR = '.job-details-jobs-unified-top-card__job-title a[href*="/jobs/view/{job_id}/"]'
APPLY_BUTTON_SELECTOR = "button.jobs-apply-button"
EASY_APPLY_LABEL = "candidatura simplificada"
MODAL_SELECTOR = ".jobs-easy-apply-modal"
CLOSE_SELECTOR = f"{MODAL_SELECTOR} button[data-test-modal-close-btn]"
DISCARD_SELECTOR = 'button[data-control-name="discard_application_confirm_btn"]'
RADIO_OPTION_SELECTOR = '[id="{group_id}"] input[data-test-text-selectable-option__input="{option}"]'
SUCCESS_PATTERN = r"candidatura foi enviada|application was sent|solicitud fue enviada"
MAX_STEPS = 12
TEXT_KINDS = {FieldKind.TEXT, FieldKind.NUMBER, FieldKind.PHONE, FieldKind.FREE_TEXT}
SELECT_KINDS = {FieldKind.SELECT, FieldKind.PHONE_COUNTRY}
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


def fill_field(page: Page, field: FormField, value: str) -> None:
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


def fill_step(page: Page, decisions: list[tuple[FormField, FieldDecision]]) -> None:
    for field, decision in decisions:
        if decision.action == DecisionAction.FILL and decision.value != field.value:
            fill_field(page, field, decision.value)


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


def fail(page: Page, reason: str, debug_dir: Path, timeout_ms: int, discard: bool = True) -> ApplicationResult:
    dump_dir = save_debug_dump(page, read_page_state(page), debug_dir)
    logger.warning("candidatura falhou: %s; dump em %s", reason, dump_dir)
    if discard:
        discard_application(page, timeout_ms)
    return result(ApplicationOutcome.FAILED, reason)


def submit_application(page: Page, debug_dir: Path, timeout_ms: int) -> ApplicationResult:
    page.locator(ACTION_SELECTORS[StepAction.SUBMIT]).click(timeout=timeout_ms)
    try:
        page.wait_for_function(SUCCESS_SCRIPT, timeout=timeout_ms)
    except PlaywrightError:
        reason = "sem confirmação de envio; confira à mão no LinkedIn"
        return fail(page, reason, debug_dir, timeout_ms, discard=False)
    return result(ApplicationOutcome.APPLIED)


def advance(page: Page, action: StepAction, wait: Callable[[], None], timeout_ms: int) -> None:
    before = page.locator(MODAL_SELECTOR).first.inner_html()
    wait()
    page.locator(ACTION_SELECTORS[action]).click(timeout=timeout_ms)
    page.wait_for_function(MODAL_CHANGED_SCRIPT, arg=[MODAL_SELECTOR, before], timeout=timeout_ms)


def open_application(page: Page, job: Job, timeout_ms: int) -> bool:
    page.goto(SEARCH_JOB_URL.format(job_id=job.id), wait_until="domcontentloaded")
    ensure_page_is_usable(page)
    page.wait_for_selector(PANEL_READY_SELECTOR.format(job_id=job.id), timeout=timeout_ms)
    apply_button = page.locator(APPLY_BUTTON_SELECTOR).first
    if apply_button.count() == 0 or EASY_APPLY_LABEL not in apply_button.inner_text().casefold():
        return False
    apply_button.click(timeout=timeout_ms)
    page.wait_for_selector(MODAL_SELECTOR, timeout=timeout_ms)
    return True


def apply_to_job(
    page: Page,
    job: Job,
    resume_file: Path,
    context: AnswerContext,
    simulate: bool,
    wait: Callable[[], None],
    debug_dir: Path,
    timeout_ms: int = 15000,
) -> ApplicationResult:
    if not open_application(page, job, timeout_ms):
        return result(ApplicationOutcome.FAILED, "sem botão Candidatura simplificada")
    for _ in range(MAX_STEPS):
        step = read_current_step(page)
        if step.errors:
            return fail(page, f"erro de validação: {'; '.join(step.errors)}", debug_dir, timeout_ms)
        decisions = [(field, resolve_field(field, context)) for field in step.fields]
        for field, decision in decisions:
            log_decision(field, decision)
        failure = next((decision for _, decision in decisions if decision.action == DecisionAction.FAIL), None)
        if failure is not None:
            return fail(page, failure.reason, debug_dir, timeout_ms)
        pending_fields = [field for field, decision in decisions if decision.action == DecisionAction.PENDING]
        if pending_fields:
            discard_application(page, timeout_ms)
            return result(ApplicationOutcome.PENDING, "perguntas sem resposta", pending_fields)
        fill_step(page, decisions)
        prepare_step(page, step, resume_file)
        if step.action is None:
            return fail(page, "etapa sem botão de avançar ou enviar", debug_dir, timeout_ms)
        if step.action == StepAction.SUBMIT and simulate:
            discard_application(page, timeout_ms)
            return result(ApplicationOutcome.SIMULATED)
        if step.action == StepAction.SUBMIT:
            return submit_application(page, debug_dir, timeout_ms)
        advance(page, step.action, wait, timeout_ms)
    return fail(page, "formulário com etapas demais", debug_dir, timeout_ms)
