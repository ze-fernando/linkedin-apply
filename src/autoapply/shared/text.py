import re
import unicodedata


def remove_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def normalize_text(text: str) -> str:
    return remove_accents(text).casefold()


def contains_term(text: str, term: str) -> bool:
    pattern = rf"(?<!\w){re.escape(normalize_text(term))}(?!\w)"
    return re.search(pattern, normalize_text(text)) is not None
