import re
import unicodedata

from autoapply.modules.config.models import Config

NON_WORD_PATTERN = re.compile(r"[^\w\s]")
WHITESPACE_PATTERN = re.compile(r"\s+")


def remove_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def normalize_question(question: str) -> str:
    without_punctuation = NON_WORD_PATTERN.sub(" ", remove_accents(question).lower())
    return WHITESPACE_PATTERN.sub(" ", without_punctuation).strip()


def find_answer(config: Config, question: str) -> str | None:
    return config.respostas.get(normalize_question(question))
