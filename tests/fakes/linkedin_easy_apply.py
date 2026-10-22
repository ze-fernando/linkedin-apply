from dataclasses import dataclass, field
from html import escape
from pathlib import Path

PAGES_DIR = Path(__file__).parent.parent / "fixtures" / "pages"

APPLY_PAGE_SCRIPT = """
window.__log = {submitted: false, discarded: false, uploaded: null, followAtSubmit: null, values: {}, opened: false};
const steps = [...document.querySelectorAll("template.step")].map((template) => template.innerHTML);
const showSuccess = document.body.dataset.success === "true";
let current = 0;
const root = document.getElementById("modal-root");
const render = () => {
  root.innerHTML = `<div role="dialog" class="artdeco-modal jobs-easy-apply-modal">
    <button aria-label="Fechar" data-test-modal-close-btn=""></button>
    <div class="jobs-easy-apply-modal__content">${steps[current]}</div></div>`;
};
const modal = () => root.querySelector(".jobs-easy-apply-modal");
const showError = (container, message) => {
  const error = document.createElement("div");
  error.className = "artdeco-inline-feedback artdeco-inline-feedback--error";
  error.innerHTML = `<span class="artdeco-inline-feedback__message">${message}</span>`;
  container.appendChild(error);
};
const validateStep = () => {
  let valid = true;
  for (const container of modal().querySelectorAll(".fb-dash-form-element")) {
    const input = container.querySelector("input[type=text], textarea");
    const select = container.querySelector("select");
    const radios = [...container.querySelectorAll("input[type=radio]")];
    if (input && input.required && !input.value) { showError(container, "Enter a valid answer"); valid = false; }
    if (input && input.id.endsWith("-numeric") && input.value && !/^\\d{1,2}$/.test(input.value)) {
      showError(container, "Enter a whole number between 0 and 99"); valid = false;
    }
    if (select && select.required && select.selectedIndex === 0) { showError(container, "Make a selection"); valid = false; }
    if (radios.length && radios[0].getAttribute("aria-required") === "true" && !radios.some((radio) => radio.checked)) {
      showError(container, "Make a selection"); valid = false;
    }
  }
  return valid;
};
const recordValues = () => {
  for (const element of modal().querySelectorAll("input[type=text], textarea")) window.__log.values[element.id] = element.value;
  for (const element of modal().querySelectorAll("select")) window.__log.values[element.id] = element.options[element.selectedIndex].text.trim();
  for (const element of modal().querySelectorAll("input[type=radio]:checked")) {
    window.__log.values[element.name] = element.getAttribute("data-test-text-selectable-option__input");
  }
};
document.addEventListener("change", (event) => {
  if (event.target.type === "file") window.__log.uploaded = event.target.files[0].name;
});
document.addEventListener("click", (event) => {
  const target = event.target.closest("button");
  if (!target) return;
  if (target.classList.contains("jobs-apply-button")) { window.__log.opened = true; current = 0; render(); return; }
  if (target.matches("[data-easy-apply-next-button], [data-live-test-easy-apply-review-button]")) {
    if (!validateStep()) return;
    recordValues();
    current += 1;
    setTimeout(render, 50);
    return;
  }
  if (target.matches("[data-live-test-easy-apply-submit-button]")) {
    recordValues();
    window.__log.submitted = true;
    const follow = document.getElementById("follow-company-checkbox");
    window.__log.followAtSubmit = follow ? follow.checked : null;
    if (showSuccess) {
      setTimeout(() => {
        root.innerHTML = document.getElementById("success").innerHTML;
      }, 50);
    }
    return;
  }
  if (target.matches("[data-test-modal-close-btn]")) {
    const confirm = document.createElement("div");
    confirm.setAttribute("role", "alertdialog");
    confirm.innerHTML = `<h2>Salvar esta candidatura?</h2>
      <button data-control-name="discard_application_confirm_btn" data-test-dialog-secondary-btn="">Descartar</button>
      <button data-control-name="save_application_btn" data-test-dialog-primary-btn="">Salvar</button>`;
    document.body.appendChild(confirm);
    return;
  }
  if (target.matches("[data-control-name=discard_application_confirm_btn]")) {
    window.__log.discarded = true;
    root.innerHTML = "";
    target.closest("[role=alertdialog]").remove();
  }
});
"""

NEXT_BUTTON = '<button aria-label="Avançar para próxima etapa" data-easy-apply-next-button="" type="button">Avançar</button>'
REVIEW_BUTTON = '<button aria-label="Revise sua candidatura" data-live-test-easy-apply-review-button="" type="button">Revisar</button>'
SUBMIT_BUTTON = '<button aria-label="Enviar candidatura" data-live-test-easy-apply-submit-button="" type="button">Enviar candidatura</button>'
ELEMENT_ID = "single-line-text-form-component-formElement-urn-li-jobs-applyformcommon-easyApplyFormElement-9000-{}"
SELECT_ID = "text-entity-list-form-component-formElement-urn-li-jobs-applyformcommon-easyApplyFormElement-9000-{}"
RADIO_ID = "radio-button-form-component-formElement-urn-li-jobs-applyformcommon-easyApplyFormElement-9000-{}"
RESUME_INPUT_ID = "jobs-document-upload-file-input-upload-resume-urn:li:fsu_jobApplicationFileUploadFormElement:(9000,1,document)"


def text_field(suffix: str, label: str, value: str = "", required: bool = True) -> str:
    element_id = ELEMENT_ID.format(suffix)
    required_attribute = ' required=""' if required else ""
    return f"""
    <div class="fb-dash-form-element" data-test-form-element="">
      <div data-test-single-line-text-form-component="">
        <label for="{element_id}">{escape(label)}</label>
        <input id="{element_id}" type="text" value="{escape(value)}"{required_attribute}>
      </div>
    </div>"""


def select_field(suffix: str, label: str, options: list[str], selected: str | None = None) -> str:
    element_id = SELECT_ID.format(suffix)
    option_tags = "".join(
        f'<option{" selected" if option == selected else ""}>{escape(option)}</option>' for option in options
    )
    return f"""
    <div class="fb-dash-form-element" data-test-form-element="">
      <div data-test-text-entity-list-form-component="">
        <label for="{element_id}"><span>{escape(label)}</span></label>
        <select id="{element_id}" aria-required="true" required=""><option>Select an option</option>{option_tags}</select>
      </div>
    </div>"""


def radio_field(suffix: str, label: str, options: list[str], checked: str | None = None) -> str:
    group_id = RADIO_ID.format(suffix)
    name = f"radio-{suffix}"
    choices = "".join(
        f"""<div data-test-text-selectable-option="{index}">
          <input data-test-text-selectable-option__input="{escape(option)}" id="{name}-{index}" name="{name}"
            aria-required="true" type="radio"{" checked" if option == checked else ""}>
          <label for="{name}-{index}">{escape(option)}</label></div>"""
        for index, option in enumerate(options)
    )
    return f"""
    <div class="fb-dash-form-element" data-test-form-element="">
      <fieldset data-test-form-builder-radio-button-form-component="true" id="{group_id}">
        <legend><span data-test-form-builder-radio-button-form-component__title=""><span>{escape(label)}</span></span>
          <span data-test-form-builder-radio-button-form-component__required="">Obrigatório</span></legend>
        {choices}
      </fieldset>
    </div>"""


def typeahead_field(suffix: str, label: str) -> str:
    element_id = f"single-typeahead-entity-form-component-{suffix}"
    return f"""
    <div class="fb-dash-form-element" data-test-form-element="">
      <label for="{element_id}">{escape(label)}</label>
      <input id="{element_id}" role="combobox" aria-required="true" type="text">
    </div>"""


def resume_upload() -> str:
    return f"""
    <label for="{RESUME_INPUT_ID}">Carregue o currículo</label>
    <input id="{RESUME_INPUT_ID}" name="file" type="file">"""


def follow_company() -> str:
    return """
    <input id="follow-company-checkbox" type="checkbox" checked>
    <label for="follow-company-checkbox">Siga a empresa Empresa Teste</label>"""


@dataclass(frozen=True)
class FakeStep:
    title: str
    body: str
    button: str = NEXT_BUTTON


@dataclass(frozen=True)
class FakeApplication:
    job_id: str
    title: str = "Desenvolvedor Python Pleno"
    steps: list[FakeStep] = field(default_factory=list)
    easy_apply: bool = True
    shows_success: bool = True
    already_applied: bool = False
    success_page: str = "easy_apply_success.html"


def render_step(step: FakeStep) -> str:
    return f"""<template class="step"><h3>{escape(step.title)}</h3>{step.body}
      <footer role="presentation">{step.button}</footer></template>"""


APPLIED_FEEDBACK = (PAGES_DIR / "job_already_applied.html").read_text(encoding="utf-8")


def build_apply_control(application: FakeApplication) -> str:
    if application.already_applied:
        return APPLIED_FEEDBACK
    apply_label = "Candidatura simplificada" if application.easy_apply else "Candidatar-se"
    return f'<button class="jobs-apply-button" type="button"><span>{apply_label}</span></button>'


def build_apply_page(application: FakeApplication) -> str:
    return f"""<!doctype html>
    <html><body data-success="{str(application.shows_success).lower()}">
      <div class="job-details-jobs-unified-top-card__job-title">
        <h1><a href="/jobs/view/{application.job_id}/">{escape(application.title)}</a></h1>
      </div>
      {build_apply_control(application)}
      <div id="modal-root"></div>
      {"".join(render_step(step) for step in application.steps)}
      <template id="success">{(PAGES_DIR / application.success_page).read_text(encoding="utf-8")}</template>
      <script>{APPLY_PAGE_SCRIPT}</script>
    </body></html>"""
