import re

from autoapply.modules.applying.answer_rules import (
    choose_salary,
    find_experience_technology,
    find_experience_years,
    find_question_technology_years,
    find_salary_question,
    has_minimum_experience,
    is_experience_question,
)
from autoapply.modules.applying.models import (
    AnswerContext,
    AnswerSource,
    DecisionAction,
    FieldDecision,
    FieldKind,
    FormField,
)
from autoapply.modules.config.answers import normalize_question
from autoapply.shared.text import normalize_text

CHOICE_KINDS = {FieldKind.SELECT, FieldKind.RADIO, FieldKind.PHONE_COUNTRY}
YES_WORDS = {"sim", "yes", "si"}
NO_WORDS = {"nao", "no"}
YES_ANSWER = "Sim"
NO_ANSWER = "Não"
NUMBER_PATTERN = re.compile(r"^\d+(?:[.,]\d+)?$")
JOB_SALARY_KEY = "pretensao salarial"
JOB_MESSAGE_KEY = "mensagem"
EMAIL_LABEL_TERMS = ["email", "e mail", "correo"]
FIRST_NAME_LABELS = {"first name", "nome", "primeiro nome", "nombre"}
LAST_NAME_LABELS = {"last name", "sobrenome", "apellido", "apellidos"}
COUNTRY_CODE_PATTERN = re.compile(r"^\+(\d+)")


def fill(value: str, source: AnswerSource) -> FieldDecision:
    return FieldDecision(action=DecisionAction.FILL, value=value, source=source, reason=None)


def pending(reason: str) -> FieldDecision:
    return FieldDecision(action=DecisionAction.PENDING, value=None, source=None, reason=reason)


def find_yes_no_group(answer: str) -> set[str] | None:
    normalized = normalize_text(answer)
    return next((group for group in (YES_WORDS, NO_WORDS) if normalized in group), None)


def match_option(answer: str, options: list[str]) -> str | None:
    exact = next((option for option in options if normalize_text(option) == normalize_text(answer)), None)
    if exact is not None:
        return exact
    group = find_yes_no_group(answer)
    return next((option for option in options if group and normalize_text(option) in group), None)


def decide_with_answer(field: FormField, answer: str, source: AnswerSource) -> FieldDecision:
    if field.kind in CHOICE_KINDS:
        option = match_option(answer, field.options)
        if option is None:
            return pending(f"a resposta '{answer}' não casa com as opções do formulário")
        return fill(option, source)
    if field.kind == FieldKind.NUMBER and not NUMBER_PATTERN.match(answer.strip()):
        return pending(f"a resposta '{answer}' não é um número")
    return fill(answer, source)


def find_stored_answer(field: FormField, context: AnswerContext) -> tuple[AnswerSource, str] | None:
    question = normalize_question(field.label)
    if question in context.job_answers:
        return AnswerSource.JOB, context.job_answers[question]
    if question in context.config.respostas:
        return AnswerSource.CONFIG, context.config.respostas[question]
    return None


def find_salary_answer(field: FormField, context: AnswerContext) -> tuple[AnswerSource, str] | None:
    salary_question = find_salary_question(field.label)
    if salary_question is None:
        return None
    if JOB_SALARY_KEY in context.job_answers:
        return AnswerSource.JOB, context.job_answers[JOB_SALARY_KEY]
    if salary_question.foreign_currency:
        return None
    return AnswerSource.RULE, str(choose_salary(context.job_title, salary_question, context.config.pretensao))


def find_experience_answer(field: FormField, context: AnswerContext) -> tuple[AnswerSource, str] | None:
    technology = find_experience_technology(field.label)
    years = None if technology is None else find_experience_years(technology, context.config.experiencia_anos)
    return None if years is None else (AnswerSource.RULE, str(years))


def find_keyword_experience_answer(field: FormField, context: AnswerContext) -> tuple[AnswerSource, str] | None:
    if not is_experience_question(field.label):
        return None
    years = find_question_technology_years(field.label, context.config.experiencia_anos)
    if not years:
        return None
    if field.kind == FieldKind.NUMBER:
        return AnswerSource.RULE, str(max(years))
    if field.kind in CHOICE_KINDS:
        return AnswerSource.RULE, YES_ANSWER if has_minimum_experience(field.label, max(years)) else NO_ANSWER
    return None


def find_country_option(field: FormField, phone: str) -> str | None:
    code = COUNTRY_CODE_PATTERN.match(phone.strip())
    if code is None:
        return None
    return next((option for option in field.options if f"(+{code.group(1)})" in option), None)


def find_profile_answer(field: FormField, context: AnswerContext) -> str | None:
    perfil = context.config.perfil
    label = normalize_question(field.label)
    if field.kind == FieldKind.PHONE:
        return re.sub(r"\D", "", perfil.ddd + perfil.celular)
    if field.kind == FieldKind.PHONE_COUNTRY:
        return find_country_option(field, perfil.telefone) or ""
    if field.kind == FieldKind.SELECT and any(term in label for term in EMAIL_LABEL_TERMS):
        return perfil.email
    if field.kind == FieldKind.TEXT and label in FIRST_NAME_LABELS:
        return perfil.primeiro_nome
    if field.kind == FieldKind.TEXT and label in LAST_NAME_LABELS:
        return perfil.sobrenome
    return None


def resolve_contact_field(field: FormField, context: AnswerContext) -> FieldDecision | None:
    profile_answer = find_profile_answer(field, context)
    if profile_answer is None:
        return None
    if field.value is not None:
        return FieldDecision(action=DecisionAction.KEEP, value=field.value, source=AnswerSource.LINKEDIN, reason=None)
    return decide_with_answer(field, profile_answer, AnswerSource.PROFILE)


def resolve_unanswered_field(field: FormField, context: AnswerContext) -> FieldDecision:
    if field.kind == FieldKind.FREE_TEXT:
        if JOB_MESSAGE_KEY in context.job_answers:
            return fill(context.job_answers[JOB_MESSAGE_KEY], AnswerSource.JOB)
        return fill(context.config.resposta_generica, AnswerSource.GENERIC)
    if not field.required:
        return FieldDecision(action=DecisionAction.SKIP, value=None, source=None, reason="campo opcional sem resposta")
    return pending("sem resposta no respostas.md nem no config.md")


def resolve_field(field: FormField, context: AnswerContext) -> FieldDecision:
    if field.kind == FieldKind.UNKNOWN:
        action = DecisionAction.FAIL if field.required else DecisionAction.SKIP
        reason = f"tipo de campo não suportado: '{field.label}'"
        return FieldDecision(action=action, value=None, source=None, reason=reason)
    contact_decision = resolve_contact_field(field, context)
    if contact_decision is not None:
        return contact_decision
    for find_answer in (find_stored_answer, find_salary_answer, find_experience_answer, find_keyword_experience_answer):
        found = find_answer(field, context)
        if found is not None:
            source, answer = found
            return decide_with_answer(field, answer, source)
    if field.value is not None:
        return FieldDecision(action=DecisionAction.KEEP, value=field.value, source=AnswerSource.LINKEDIN, reason=None)
    return resolve_unanswered_field(field, context)
