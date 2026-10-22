from collections.abc import Callable

from autoapply.modules.applying.form_parsing import parse_form_step
from autoapply.modules.applying.models import FieldKind, FormField, StepAction

NUMERIC_ID = "single-line-text-form-component-formElement-urn-li-jobs-applyformcommon-easyApplyFormElement-1000-{}-numeric"


def test_parse_form_step_reads_numeric_fields_with_label_requirement_and_current_value(
    read_page: Callable[[str], str],
) -> None:
    step = parse_form_step(read_page("easy_apply_numbers.html"))

    assert step.title == "Additional Questions"
    assert step.fields == [
        FormField(
            element_id=NUMERIC_ID.format(11),
            kind=FieldKind.NUMBER,
            label="How many years of work experience do you have with ASP.NET Core?",
            required=True,
            value=None,
            options=[],
        ),
        FormField(
            element_id=NUMERIC_ID.format(12),
            kind=FieldKind.NUMBER,
            label="How many years of work experience with REST APIs?",
            required=False,
            value="3",
            options=[],
        ),
    ]


CHOICE_ID = "text-entity-list-form-component-formElement-urn-li-jobs-applyformcommon-easyApplyFormElement-2000-{}-multipleChoice"
RADIO_ID = "radio-button-form-component-formElement-urn-li-jobs-applyformcommon-easyApplyFormElement-2000-{}-multipleChoice"


def test_parse_form_step_reads_selects_and_radios_without_placeholder(read_page: Callable[[str], str]) -> None:
    step = parse_form_step(read_page("easy_apply_choices.html"))

    assert step.title == "Perguntas adicionais"
    assert step.fields == [
        FormField(
            element_id=CHOICE_ID.format(21),
            kind=FieldKind.SELECT,
            label="What is your level of proficiency in English?",
            required=True,
            value="Professional",
            options=["None", "Conversational", "Professional", "Native or bilingual"],
        ),
        FormField(
            element_id=CHOICE_ID.format(22),
            kind=FieldKind.SELECT,
            label="¿Contás con disponibilidad para trabajar 6 meses?",
            required=True,
            value=None,
            options=["Yes", "No"],
        ),
        FormField(
            element_id=RADIO_ID.format(23),
            kind=FieldKind.RADIO,
            label="Você trabalharia remotamente?",
            required=True,
            value="Sim",
            options=["Sim", "Não"],
        ),
        FormField(
            element_id=RADIO_ID.format(24),
            kind=FieldKind.RADIO,
            label="Possui CNH?",
            required=False,
            value=None,
            options=["Sim", "Não"],
        ),
    ]


CONTACT_ID = "easyApplyFormElement-3000-{}"


def test_parse_form_step_tells_phone_and_country_apart_from_plain_text_and_select(
    read_page: Callable[[str], str],
) -> None:
    step = parse_form_step(read_page("easy_apply_contact.html"))

    assert [(field.kind, field.label, field.value) for field in step.fields] == [
        (FieldKind.TEXT, "First name", "Maria"),
        (FieldKind.PHONE_COUNTRY, "Phone country code", "Brazil (+55)"),
        (FieldKind.PHONE, "Mobile phone number", None),
        (FieldKind.SELECT, "Email address", "maria.teste@example.com"),
    ]
    assert step.fields[1].options == ["Brazil (+55)", "Argentina (+54)"]
    assert all(field.required for field in step.fields)
    assert step.fields[2].element_id.endswith(CONTACT_ID.format("32-phoneNumber-nationalNumber"))


def test_parse_form_step_marks_textarea_as_free_text_and_unsupported_fields_as_unknown(
    read_page: Callable[[str], str],
) -> None:
    step = parse_form_step(read_page("easy_apply_other_fields.html"))

    assert [(field.kind, field.label, field.required) for field in step.fields] == [
        (FieldKind.FREE_TEXT, "¿Por qué quieres trabajar con nosotros?", True),
        (FieldKind.LOCATION, "Cidade", True),
        (FieldKind.UNKNOWN, "Quais tecnologias você usa?", False),
        (FieldKind.UNKNOWN, "Carta de apresentação", True),
    ]


def test_parse_form_step_reads_the_city_autocomplete_as_location(read_page: Callable[[str], str]) -> None:
    step = parse_form_step(read_page("easy_apply_location.html"))

    [field] = step.fields
    assert (field.kind, field.label, field.required, field.value) == (
        FieldKind.LOCATION,
        "Location (city)",
        True,
        None,
    )
    assert field.element_id.endswith("easyApplyFormElement-5000-51-location-GEO-LOCATION")


def test_parse_form_step_detects_resume_upload_and_next_button(read_page: Callable[[str], str]) -> None:
    step = parse_form_step(read_page("easy_apply_resume.html"))

    assert (step.title, step.fields, step.has_resume_upload, step.has_follow_company) == ("Currículo", [], True, False)
    assert (step.action, step.errors) == (StepAction.NEXT, [])


def test_parse_form_step_detects_follow_company_and_submit_button_on_review(read_page: Callable[[str], str]) -> None:
    step = parse_form_step(read_page("easy_apply_review.html"))

    assert (step.title, step.fields, step.has_resume_upload, step.has_follow_company) == (
        "Revise sua candidatura",
        [],
        False,
        True,
    )
    assert step.action == StepAction.SUBMIT


def test_parse_form_step_reads_validation_errors_and_review_button(read_page: Callable[[str], str]) -> None:
    step = parse_form_step(read_page("easy_apply_errors.html"))

    assert step.errors == ["Enter a whole number between 0 and 99"]
    assert step.action == StepAction.REVIEW
    assert (step.has_resume_upload, step.has_follow_company) == (False, False)


def test_parse_form_step_without_footer_buttons_has_no_action(read_page: Callable[[str], str]) -> None:
    assert parse_form_step(read_page("easy_apply_numbers.html")).action is None
