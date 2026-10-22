import copy
from collections.abc import Callable
from pathlib import Path

import pytest

from autoapply.modules.applying.answering import resolve_field
from autoapply.modules.applying.models import (
    AnswerContext,
    AnswerSource,
    DecisionAction,
    FieldDecision,
    FieldKind,
    FormField,
)
from autoapply.modules.config.loader import parse_config_data


@pytest.fixture
def build_context(valid_data: dict[str, object], base_dir: Path) -> Callable[..., AnswerContext]:
    def build(
        job_answers: dict[str, str] | None = None,
        job_title: str = "Desenvolvedor Python Pleno",
        experience: dict[str, int] | None = None,
    ) -> AnswerContext:
        data = copy.deepcopy(valid_data)
        data["respostas"] = {"aceita pj": "Sim", "aceita trabalhar remotamente": "Sim"}
        if experience is not None:
            data["experiencia_anos"] = experience
        return AnswerContext(
            config=parse_config_data(data, base_dir),
            job_answers=job_answers or {},
            job_title=job_title,
        )

    return build


def build_field(
    kind: FieldKind, label: str, value: str | None = None, options: list[str] | None = None, required: bool = True
) -> FormField:
    return FormField(element_id="campo", kind=kind, label=label, required=required, value=value, options=options or [])


def test_resolve_field_prefers_job_answers_over_config(build_context: Callable[..., AnswerContext]) -> None:
    field = build_field(FieldKind.RADIO, "Aceita PJ?", value="Sim", options=["Sim", "Não"])

    assert resolve_field(field, build_context({"aceita pj": "Não"})) == FieldDecision(
        action=DecisionAction.FILL, value="Não", source=AnswerSource.JOB, reason=None
    )
    assert resolve_field(field, build_context()) == FieldDecision(
        action=DecisionAction.FILL, value="Sim", source=AnswerSource.CONFIG, reason=None
    )


def test_resolve_field_matches_yes_and_no_across_languages(build_context: Callable[..., AnswerContext]) -> None:
    field = build_field(FieldKind.SELECT, "Aceita trabalhar remotamente?", options=["Yes", "No"])

    assert resolve_field(field, build_context()) == FieldDecision(
        action=DecisionAction.FILL, value="Yes", source=AnswerSource.CONFIG, reason=None
    )


def keep_from_linkedin(value: str) -> FieldDecision:
    return FieldDecision(action=DecisionAction.KEEP, value=value, source=AnswerSource.LINKEDIN, reason=None)


def test_resolve_field_answers_experience_years_from_config(build_context: Callable[..., AnswerContext]) -> None:
    field = build_field(FieldKind.NUMBER, "How many years of work experience do you have with Python?")

    assert resolve_field(field, build_context()) == FieldDecision(
        action=DecisionAction.FILL, value="3", source=AnswerSource.RULE, reason=None
    )


def test_resolve_field_unknown_technology_keeps_prefilled_value_or_becomes_pending(
    build_context: Callable[..., AnswerContext],
) -> None:
    question = "How many years of work experience do you have with AWS?"

    assert resolve_field(build_field(FieldKind.NUMBER, question, value="2"), build_context()) == keep_from_linkedin("2")
    assert resolve_field(build_field(FieldKind.NUMBER, question), build_context()).action == DecisionAction.PENDING


def test_resolve_field_answers_salary_by_title_level_unless_job_overrides(
    build_context: Callable[..., AnswerContext],
) -> None:
    field = build_field(FieldKind.NUMBER, "Qual a sua pretensão salarial (PJ)?")

    assert resolve_field(field, build_context(job_title="Desenvolvedor Pleno")) == FieldDecision(
        action=DecisionAction.FILL, value="8000", source=AnswerSource.RULE, reason=None
    )
    assert resolve_field(field, build_context({"pretensao salarial": "7500"})) == FieldDecision(
        action=DecisionAction.FILL, value="7500", source=AnswerSource.JOB, reason=None
    )


def test_resolve_field_salary_in_foreign_currency_becomes_pending(build_context: Callable[..., AnswerContext]) -> None:
    field = build_field(FieldKind.NUMBER, "Cuál es tu pretendido mensual en usd?")

    assert resolve_field(field, build_context()).action == DecisionAction.PENDING


def test_resolve_field_rejects_non_numeric_answer_for_number_field(build_context: Callable[..., AnswerContext]) -> None:
    field = build_field(FieldKind.NUMBER, "Anos de casa")

    assert resolve_field(field, build_context({"anos de casa": "muitos"})).action == DecisionAction.PENDING
    assert resolve_field(field, build_context({"anos de casa": "2,5"})) == FieldDecision(
        action=DecisionAction.FILL, value="2,5", source=AnswerSource.JOB, reason=None
    )


def test_resolve_field_keeps_linkedin_prefilled_answer_without_stored_answer(
    build_context: Callable[..., AnswerContext],
) -> None:
    field = build_field(FieldKind.RADIO, "Possui CNH?", value="Sim", options=["Sim", "Não"])

    assert resolve_field(field, build_context()) == keep_from_linkedin("Sim")


def from_profile(value: str) -> FieldDecision:
    return FieldDecision(action=DecisionAction.FILL, value=value, source=AnswerSource.PROFILE, reason=None)


def test_resolve_field_keeps_prefilled_contact_fields(build_context: Callable[..., AnswerContext]) -> None:
    phone = build_field(FieldKind.PHONE, "Mobile phone number", value="11999990000")
    email = build_field(FieldKind.SELECT, "E-mail", value="maria.outra@example.com", options=["maria.outra@example.com"])

    assert resolve_field(phone, build_context()) == keep_from_linkedin("11999990000")
    assert resolve_field(email, build_context()) == keep_from_linkedin("maria.outra@example.com")


def test_resolve_field_fills_empty_contact_fields_from_profile(build_context: Callable[..., AnswerContext]) -> None:
    context = build_context()
    email_options = ["maria.outra@example.com", "maria.teste@example.com"]

    assert resolve_field(build_field(FieldKind.PHONE, "Teléfono móvil"), context) == from_profile("11912345678")
    assert resolve_field(
        build_field(FieldKind.PHONE_COUNTRY, "Código do país", options=["Afeganistão (+93)", "Brasil (+55)"]), context
    ) == from_profile("Brasil (+55)")
    assert resolve_field(build_field(FieldKind.SELECT, "Email address", options=email_options), context) == (
        from_profile("maria.teste@example.com")
    )
    assert resolve_field(build_field(FieldKind.TEXT, "First name"), context) == from_profile("Maria")
    assert resolve_field(build_field(FieldKind.TEXT, "Sobrenome"), context) == from_profile("Teste da Silva")


def test_resolve_field_profile_email_missing_from_options_becomes_pending(
    build_context: Callable[..., AnswerContext],
) -> None:
    field = build_field(FieldKind.SELECT, "E-mail", options=["maria.outra@example.com"])

    assert resolve_field(field, build_context()).action == DecisionAction.PENDING


def test_resolve_field_free_text_uses_job_message_then_generic_answer(
    build_context: Callable[..., AnswerContext],
) -> None:
    field = build_field(FieldKind.FREE_TEXT, "¿Por qué quieres trabajar con nosotros?")

    assert resolve_field(field, build_context({"mensagem": "Adoro o produto."})) == FieldDecision(
        action=DecisionAction.FILL, value="Adoro o produto.", source=AnswerSource.JOB, reason=None
    )
    assert resolve_field(field, build_context()) == FieldDecision(
        action=DecisionAction.FILL, value="Tenho interesse na vaga.", source=AnswerSource.GENERIC, reason=None
    )


def test_resolve_field_without_answer_is_pending_when_required_and_skipped_when_optional(
    build_context: Callable[..., AnswerContext],
) -> None:
    assert resolve_field(build_field(FieldKind.TEXT, "Cidade"), build_context()).action == DecisionAction.PENDING
    assert resolve_field(build_field(FieldKind.TEXT, "Cidade", required=False), build_context()).action == (
        DecisionAction.SKIP
    )


def test_resolve_field_unknown_kind_fails_only_when_required(build_context: Callable[..., AnswerContext]) -> None:
    required = build_field(FieldKind.UNKNOWN, "Carta de apresentação")
    optional = build_field(FieldKind.UNKNOWN, "Carta de apresentação", required=False)

    assert resolve_field(required, build_context()).action == DecisionAction.FAIL
    assert resolve_field(optional, build_context()).action == DecisionAction.SKIP


KEYWORD_EXPERIENCE = {
    "total_desenvolvimento": 5,
    "SQL": 5,
    "Python": 5,
    "R": 0,
    "Go": 4,
    "APIs REST": 5,
    "Webhooks": 0,
    "CI/CD": 5,
    "RPA": 3,
    "Linux": 2,
    "Kotlin": 0,
}


@pytest.mark.parametrize(
    ("kind", "label", "expected"),
    [
        (FieldKind.SELECT, "Você possui nível avançado, mais de 3 anos de experiência, em SQL?", "Yes"),
        (
            FieldKind.SELECT,
            "Você possui nível avançado, mais de 3 anos de experiência, em Python (ou ferramenta equivalente de "
            "análise de dados, como R)",
            "Yes",
        ),
        (
            FieldKind.SELECT,
            "Você possui experiência com integração de sistemas por meio de APIs REST, webhooks e bancos de dados?",
            "Yes",
        ),
        (
            FieldKind.SELECT,
            "Você possui conhecimentos ou experiência em práticas de DevOps, como automação, integração e entrega "
            "contínua (CI/CD) e gerenciamento de ambientes?",
            "Yes",
        ),
        (FieldKind.SELECT, "Do you have at least 2 years of experience with Linux?", "Yes"),
        (FieldKind.SELECT, "Você possui mais de 2 anos de experiência com Linux?", "No"),
        (FieldKind.SELECT, "Você possui experiência com Kotlin?", "No"),
        (FieldKind.NUMBER, "Possui quantos anos de experiência em Linux, RPA ou cibersegurança;", "3"),
    ],
)
def test_resolve_field_answers_experience_by_technologies_found_in_the_question(
    build_context: Callable[..., AnswerContext], kind: FieldKind, label: str, expected: str
) -> None:
    options = ["Yes", "No"] if kind == FieldKind.SELECT else []
    field = build_field(kind, label, options=options)

    assert resolve_field(field, build_context(experience=KEYWORD_EXPERIENCE)) == FieldDecision(
        action=DecisionAction.FILL, value=expected, source=AnswerSource.RULE, reason=None
    )


@pytest.mark.parametrize(
    ("kind", "label"),
    [
        (FieldKind.SELECT, "Já atuou em projetos no desenvolvimento de IA ligada a negócios?"),
        (FieldKind.NUMBER, "Possui quantos anos de experiência em redes, infraestrutura, automação ou cibersegurança;"),
        (FieldKind.SELECT, "Você tem experiência com Go?"),
    ],
)
def test_resolve_field_without_known_technology_in_the_question_stays_pending(
    build_context: Callable[..., AnswerContext], kind: FieldKind, label: str
) -> None:
    options = ["Yes", "No"] if kind == FieldKind.SELECT else []
    field = build_field(kind, label, options=options)

    assert resolve_field(field, build_context(experience=KEYWORD_EXPERIENCE)).action == DecisionAction.PENDING
