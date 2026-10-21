import re

from autoapply.modules.applying.models import SalaryQuestion
from autoapply.modules.config.models import FaixaSalarial, Pretensao
from autoapply.modules.jobs.filters import LEVEL_TITLE_TERMS
from autoapply.shared.text import contains_term, normalize_text

QUESTION_EDGE_CHARACTERS = " ¿?¡!.:"
EXPERIENCE_PATTERNS = [
    re.compile(
        r"^how many years (?:of )?(?:work |professional )?experience "
        r"(?:do you have )?(?:with|in|using) (?P<technology>.+)$"
    ),
    re.compile(
        r"^quantos anos de experiencia (?:profissional )?(?:voce tem |possui )?(?:com|em) (?P<technology>.+)$"
    ),
    re.compile(
        r"^cuantos anos de experiencia (?:profesional )?(?:tienes |tenes |posees )?(?:con|en) (?P<technology>.+)$"
    ),
]

SALARY_PHRASES = [
    "pretensao salarial",
    "expectativa salarial",
    "salario pretendido",
    "remuneracao pretendida",
    "salary expectation",
    "expected salary",
    "desired salary",
    "pretension salarial",
    "pretendido",
]
FOREIGN_CURRENCY_TERMS = ["usd", "us$", "dolar", "dolares", "dollar", "dollars", "eur", "euro", "euros"]
PJ_TERM = "pj"
HIGHEST_LEVEL_FIRST = ["pleno", "junior"]


def normalize_rule_question(question: str) -> str:
    return " ".join(normalize_text(question).split()).strip(QUESTION_EDGE_CHARACTERS)


def find_experience_technology(question: str) -> str | None:
    normalized = normalize_rule_question(question)
    for pattern in EXPERIENCE_PATTERNS:
        match = pattern.match(normalized)
        if match:
            return match.group("technology").strip(QUESTION_EDGE_CHARACTERS)
    return None


def find_experience_years(technology: str, experience: dict[str, int]) -> int | None:
    return next((years for key, years in experience.items() if normalize_text(key) == technology), None)


def find_salary_question(question: str) -> SalaryQuestion | None:
    normalized = normalize_rule_question(question)
    if not any(phrase in normalized for phrase in SALARY_PHRASES):
        return None
    return SalaryQuestion(
        is_pj=contains_term(normalized, PJ_TERM),
        foreign_currency=any(contains_term(normalized, term) for term in FOREIGN_CURRENCY_TERMS),
    )


def find_title_level(title: str, default_level: str) -> str:
    mentioned = [
        level
        for level in HIGHEST_LEVEL_FIRST
        if any(contains_term(title, term) for term in LEVEL_TITLE_TERMS[level])
    ]
    return mentioned[0] if mentioned else default_level


def choose_salary(title: str, salary_question: SalaryQuestion, pretensao: Pretensao) -> int:
    by_contract = getattr(pretensao, find_title_level(title, pretensao.padrao_nivel))
    salary_range: FaixaSalarial = by_contract.pj if salary_question.is_pj else by_contract.clt
    return salary_range.formulario
