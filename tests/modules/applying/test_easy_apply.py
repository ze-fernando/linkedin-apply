import copy
import dataclasses
from collections.abc import Callable
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, Page

from autoapply.modules.applying.easy_apply import apply_to_job
from autoapply.modules.applying.models import AnswerContext, ApplicationOutcome, ApplicationResult
from autoapply.modules.config.loader import parse_config_data
from autoapply.modules.jobs.models import Job
from tests.fakes.linkedin_easy_apply import (
    ELEMENT_ID,
    REVIEW_BUTTON,
    SELECT_ID,
    SUBMIT_BUTTON,
    FakeApplication,
    FakeStep,
    build_apply_page,
    follow_company,
    radio_field,
    resume_upload,
    select_field,
    text_field,
    typeahead_field,
)

JOB_ID = "9000"


@pytest.fixture
def context(valid_data: dict[str, object], base_dir: Path) -> AnswerContext:
    data = copy.deepcopy(valid_data)
    data["respostas"] = {"aceita pj": "Sim"}
    return AnswerContext(config=parse_config_data(data, base_dir), job_answers={}, job_title="Desenvolvedor Python Pleno")


@pytest.fixture
def resume_file(tmp_path: Path) -> Path:
    path = tmp_path / "cv.pdf"
    path.write_bytes(b"%PDF-1.4 falso")
    return path


@pytest.fixture
def run_application(
    browser_context: BrowserContext,
    serve_pages: Callable[[dict[str, str]], None],
    build_job: Callable[..., Job],
    context: AnswerContext,
    resume_file: Path,
    tmp_path: Path,
) -> Callable[..., tuple[ApplicationResult, dict[str, object], Page]]:
    def run(
        application: FakeApplication,
        simulate: bool = False,
        confirm_submit: Callable[[Job, list[tuple[str, str]]], bool] = lambda job, answers: True,
    ) -> tuple[ApplicationResult, dict[str, object], Page]:
        serve_pages({"/jobs/search/": build_apply_page(application)})
        page = browser_context.pages[0]
        result = apply_to_job(
            page,
            build_job(id=JOB_ID, title=application.title),
            resume_file,
            context,
            simulate=simulate,
            confirm_submit=confirm_submit,
            wait=lambda: None,
            debug_dir=tmp_path / "debug",
            timeout_ms=2000,
        )
        return result, page.evaluate("window.__log"), page

    return run


def full_application() -> FakeApplication:
    return FakeApplication(
        job_id=JOB_ID,
        steps=[
            FakeStep(
                "Informações de contato",
                text_field("phoneNumber-nationalNumber", "Número de celular")
                + select_field("email-multipleChoice", "E-mail", ["maria.teste@example.com"], "maria.teste@example.com"),
            ),
            FakeStep("Currículo", resume_upload()),
            FakeStep(
                "Perguntas adicionais",
                text_field("python-numeric", "How many years of work experience do you have with Python?")
                + radio_field("pj", "Aceita PJ?", ["Sim", "Não"])
                + select_field("english", "Nível de inglês", ["Basic", "Professional"], "Professional"),
                REVIEW_BUTTON,
            ),
            FakeStep("Revise sua candidatura", follow_company(), SUBMIT_BUTTON),
        ],
    )


def test_apply_to_job_fills_every_step_uploads_resume_unfollows_and_submits(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]],
) -> None:
    result, log, _ = run_application(full_application())

    assert result == ApplicationResult(outcome=ApplicationOutcome.APPLIED, reason=None, pending_fields=[])
    assert (log["submitted"], log["discarded"], log["uploaded"], log["followAtSubmit"]) == (True, False, "cv.pdf", False)
    assert log["values"] == {
        ELEMENT_ID.format("phoneNumber-nationalNumber"): "11912345678",
        SELECT_ID.format("email-multipleChoice"): "maria.teste@example.com",
        ELEMENT_ID.format("python-numeric"): "3",
        "radio-pj": "Sim",
        SELECT_ID.format("english"): "Professional",
    }


def test_apply_to_job_saves_the_success_dialog_html_in_debug(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]], tmp_path: Path
) -> None:
    result, _, _ = run_application(full_application())

    [dialog_file] = list((tmp_path / "debug").glob(f"*-sucesso-{JOB_ID}/dialog.html"))
    assert result.outcome == ApplicationOutcome.APPLIED
    assert "Sua candidatura na Empresa Teste foi enviada" in dialog_file.read_text(encoding="utf-8")


@pytest.mark.parametrize("success_page", ["easy_apply_success.html", "easy_apply_success_next_action.html"])
def test_apply_to_job_recognizes_each_real_success_dialog(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]], success_page: str
) -> None:
    application = dataclasses.replace(full_application(), success_page=success_page)

    result, log, _ = run_application(application)

    assert (result.outcome, log["submitted"]) == (ApplicationOutcome.APPLIED, True)


def test_apply_to_job_declined_at_confirmation_shows_answers_never_submits_and_discards(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]],
) -> None:
    confirmations = []

    def decline(job: Job, answers: list[tuple[str, str]]) -> bool:
        confirmations.append((job.id, answers))
        return False

    result, log, page = run_application(full_application(), confirm_submit=decline)

    assert result == ApplicationResult(outcome=ApplicationOutcome.DECLINED, reason=None, pending_fields=[])
    assert (log["submitted"], log["discarded"]) == (False, True)
    assert page.locator(".jobs-easy-apply-modal").count() == 0
    assert confirmations == [
        (
            JOB_ID,
            [
                ("Número de celular", "11912345678"),
                ("E-mail", "maria.teste@example.com"),
                ("How many years of work experience do you have with Python?", "3"),
                ("Aceita PJ?", "Sim"),
                ("Nível de inglês", "Professional"),
            ],
        )
    ]


def test_apply_to_job_simulation_reaches_review_never_submits_and_discards(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]],
) -> None:
    result, log, page = run_application(full_application(), simulate=True)

    assert result == ApplicationResult(outcome=ApplicationOutcome.SIMULATED, reason=None, pending_fields=[])
    assert (log["submitted"], log["discarded"], log["uploaded"]) == (False, True, "cv.pdf")
    assert page.locator(".jobs-easy-apply-modal").count() == 0


def test_apply_to_job_with_unanswered_required_fields_discards_and_returns_them_as_pending(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]],
) -> None:
    application = FakeApplication(
        job_id=JOB_ID,
        steps=[
            FakeStep(
                "Perguntas adicionais",
                text_field("aws-numeric", "How many years of work experience do you have with AWS?")
                + radio_field("cnh", "Possui CNH?", ["Sim", "Não"])
                + radio_field("pj", "Aceita PJ?", ["Sim", "Não"]),
                REVIEW_BUTTON,
            ),
            FakeStep("Revise sua candidatura", follow_company(), SUBMIT_BUTTON),
        ],
    )

    result, log, _ = run_application(application)

    assert result.outcome == ApplicationOutcome.PENDING
    assert [(field.label, field.options) for field in result.pending_fields] == [
        ("How many years of work experience do you have with AWS?", []),
        ("Possui CNH?", ["Sim", "Não"]),
    ]
    assert (log["submitted"], log["discarded"]) == (False, True)


def test_apply_to_job_with_unknown_required_field_fails_with_dump_and_discards(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]], tmp_path: Path
) -> None:
    application = FakeApplication(
        job_id=JOB_ID,
        steps=[
            FakeStep("Perguntas adicionais", typeahead_field("cidade", "Cidade"), REVIEW_BUTTON),
            FakeStep("Revise sua candidatura", follow_company(), SUBMIT_BUTTON),
        ],
    )

    result, log, _ = run_application(application)

    assert (result.outcome, result.reason) == (ApplicationOutcome.FAILED, "tipo de campo não suportado: 'Cidade'")
    assert (log["submitted"], log["discarded"]) == (False, True)
    assert len(list((tmp_path / "debug").glob("*/page.html"))) == 1


def test_apply_to_job_with_validation_error_after_advancing_fails_with_error_text(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]], tmp_path: Path
) -> None:
    application = FakeApplication(
        job_id=JOB_ID,
        steps=[
            FakeStep(
                "Perguntas adicionais",
                text_field("aws-numeric", "How many years of work experience do you have with AWS?", value="abc"),
                REVIEW_BUTTON,
            ),
            FakeStep("Revise sua candidatura", follow_company(), SUBMIT_BUTTON),
        ],
    )

    result, log, _ = run_application(application)

    assert (result.outcome, result.reason) == (
        ApplicationOutcome.FAILED,
        "erro de validação: Enter a whole number between 0 and 99",
    )
    assert (log["submitted"], log["discarded"]) == (False, True)
    assert len(list((tmp_path / "debug").glob("*/page.html"))) == 1


def test_apply_to_job_without_easy_apply_button_fails_without_opening(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]],
) -> None:
    result, log, _ = run_application(FakeApplication(job_id=JOB_ID, easy_apply=False))

    assert (result.outcome, result.reason) == (ApplicationOutcome.FAILED, "sem botão Candidatura simplificada")
    assert log["opened"] is False


def test_apply_to_job_already_applied_on_linkedin_returns_already_applied_without_opening(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]],
) -> None:
    result, log, _ = run_application(FakeApplication(job_id=JOB_ID, already_applied=True))

    assert (result.outcome, result.reason) == (
        ApplicationOutcome.ALREADY_APPLIED,
        "o LinkedIn já mostra candidatura enviada",
    )
    assert log["opened"] is False


def test_apply_to_job_without_success_confirmation_fails_with_dump_and_keeps_modal(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]], tmp_path: Path
) -> None:
    application = FakeApplication(
        job_id=JOB_ID,
        steps=[FakeStep("Revise sua candidatura", follow_company(), SUBMIT_BUTTON)],
        shows_success=False,
    )

    result, log, _ = run_application(application)

    assert (result.outcome, result.reason) == (
        ApplicationOutcome.FAILED,
        "sem confirmação de envio; confira à mão no LinkedIn",
    )
    assert (log["submitted"], log["discarded"]) == (True, False)
    assert len(list((tmp_path / "debug").glob("*/page.html"))) == 1


def test_apply_to_job_step_without_action_button_fails_and_discards(
    run_application: Callable[..., tuple[ApplicationResult, dict[str, object], Page]],
) -> None:
    application = FakeApplication(job_id=JOB_ID, steps=[FakeStep("Etapa estranha", "", button="")])

    result, log, _ = run_application(application)

    assert (result.outcome, result.reason) == (ApplicationOutcome.FAILED, "etapa sem botão de avançar ou enviar")
    assert (log["submitted"], log["discarded"]) == (False, True)
