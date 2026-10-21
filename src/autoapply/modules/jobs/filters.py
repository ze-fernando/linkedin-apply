import re

from autoapply.modules.config.answers import remove_accents
from autoapply.modules.config.models import Busca
from autoapply.modules.jobs.models import JobCard

LEVEL_TITLE_TERMS = {"junior": ["júnior", "jr"], "pleno": ["pleno"]}
SENIORITY_TERMS = ["sênior", "senior", "sr", "especialista", "lead", "tech lead", "principal", "staff"]


def normalize_text(text: str) -> str:
    return remove_accents(text).casefold()


def contains_term(text: str, term: str) -> bool:
    pattern = rf"(?<!\w){re.escape(normalize_text(term))}(?!\w)"
    return re.search(pattern, normalize_text(text)) is not None


def is_seniority_term(term: str) -> bool:
    return normalize_text(term) in {normalize_text(seniority) for seniority in SENIORITY_TERMS}


def mentions_wanted_level(title: str, busca: Busca) -> bool:
    return any(contains_term(title, term) for nivel in busca.niveis for term in LEVEL_TITLE_TERMS[nivel])


def find_card_block_reason(card: JobCard, busca: Busca) -> str | None:
    blocked_company = next(
        (company for company in busca.empresas_bloqueadas if normalize_text(company) == normalize_text(card.company)),
        None,
    )
    if blocked_company is not None:
        return f"empresa bloqueada: '{blocked_company}'"
    blocked_term = next((term for term in busca.termos_bloqueados_no_titulo if contains_term(card.title, term)), None)
    if blocked_term is not None and not (is_seniority_term(blocked_term) and mentions_wanted_level(card.title, busca)):
        return f"título contém '{blocked_term}'"
    return None


def find_description_block_reason(description: str, busca: Busca) -> str | None:
    blocked_word = next((word for word in busca.palavras_bloqueadas if contains_term(description, word)), None)
    if blocked_word is not None:
        return f"descrição contém '{blocked_word}'"
    return None
