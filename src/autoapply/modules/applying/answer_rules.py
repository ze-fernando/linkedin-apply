import re

from autoapply.modules.applying.models import SalaryQuestion
from autoapply.modules.config.models import FaixaSalarial, Pretensao
from autoapply.modules.jobs.filters import LEVEL_TITLE_TERMS
from autoapply.modules.matching.keywords import MIN_EXPERIENCE_TERM_LENGTH, NON_TECHNOLOGY_EXPERIENCE_KEYS
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
EXPERIENCE_WORDS = [
    "experiencia",
    "experience",
    "conhecimento",
    "conhecimentos",
    "knowledge",
    "anos",
    "years",
    "atuou",
    "trabalhou",
    "worked",
    "atua",
    "quanto tempo",
    "how long",
    "cuanto tiempo",
]
DEVELOPER_ROLE_TERMS = [
    "desenvolvedor",
    "desenvolvedora",
    "programador",
    "programadora",
    "developer",
    "programmer",
    "desarrollador",
    "desarrolladora",
    "engenheiro de software",
    "engenheira de software",
    "software engineer",
    "desenvolvimento de software",
    "software development",
]
TOTAL_EXPERIENCE_KEY = "total_desenvolvimento"
MINIMUM_YEARS_PATTERNS = [
    re.compile(
        r"(?P<qualifier>mais de|more than|over|mas de|pelo menos|ao menos|no minimo|minimo de|at least|al menos)"
        r" (?P<years>\d+) (?:anos?|years?)"
    ),
    re.compile(r"(?P<years>\d+)\+ ?(?:anos?|years?)"),
]
STRICT_QUALIFIERS = {"mais de", "more than", "over", "mas de"}
DEFAULT_MINIMUM_YEARS = 1

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


def is_experience_question(question: str) -> bool:
    normalized = normalize_rule_question(question)
    return any(contains_term(normalized, word) for word in EXPERIENCE_WORDS)


def find_question_technology_years(question: str, experience: dict[str, int]) -> list[int]:
    return [
        years
        for key, years in experience.items()
        if key not in NON_TECHNOLOGY_EXPERIENCE_KEYS
        and len(key) >= MIN_EXPERIENCE_TERM_LENGTH
        and contains_term(question, key)
    ]


def find_developer_years(question: str, experience: dict[str, int]) -> int | None:
    if TOTAL_EXPERIENCE_KEY not in experience:
        return None
    if not any(contains_term(question, term) for term in DEVELOPER_ROLE_TERMS):
        return None
    return experience[TOTAL_EXPERIENCE_KEY]


def has_minimum_experience(question: str, years: int) -> bool:
    normalized = normalize_rule_question(question)
    for pattern in MINIMUM_YEARS_PATTERNS:
        match = pattern.search(normalized)
        if match:
            minimum = int(match.group("years"))
            strict = match.groupdict().get("qualifier") in STRICT_QUALIFIERS
            return years > minimum if strict else years >= minimum
    return years >= DEFAULT_MINIMUM_YEARS


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
