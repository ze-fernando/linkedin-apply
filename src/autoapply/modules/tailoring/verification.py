import re

from autoapply.modules.matching.keywords import find_terms
from autoapply.modules.tailoring.models import ResumeDocument
from autoapply.shared.text import normalize_text

MAX_SUMMARY_GROWTH = 2
NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")
WORD_PATTERN = re.compile(r"[^\W\d_][\w-]*")
SENTENCE_END_PATTERN = re.compile(r"(?<=[.!?])\s+")


def build_document_text(document: ResumeDocument) -> str:
    parts = [document.name, document.headline, *document.contact_lines, document.summary]
    for experience in document.experiences:
        parts += [experience.title, experience.period, experience.company, experience.company_detail]
        parts += [f"{bullet.lead}{bullet.text}" for bullet in experience.bullets]
    for education in document.education:
        parts += [education.course, education.period, education.institution]
    for skill_line in document.skill_lines:
        parts += [skill_line.label, *skill_line.items]
    parts += [run.text for run in document.languages]
    return "\n".join(parts)


def find_words_inside_sentences(text: str) -> list[str]:
    return [
        word for sentence in SENTENCE_END_PATTERN.split(text.strip()) for word in WORD_PATTERN.findall(sentence)[1:]
    ]


def find_new_information(base: ResumeDocument, tailored: ResumeDocument, vocabulary: list[str]) -> str | None:
    summary = tailored.summary.strip()
    base_text = build_document_text(base)
    if not summary:
        return "resumo vazio"
    limit = MAX_SUMMARY_GROWTH * len(base.summary.strip())
    if len(summary) > limit:
        return f"resumo com {len(summary)} caracteres passa do dobro do original ({len(base.summary.strip())})"
    base_terms = set(find_terms(base_text, vocabulary))
    for term in find_terms(summary, vocabulary):
        if term not in base_terms:
            return f"resumo cita tecnologia que não está no currículo: {term}"
    base_numbers = set(NUMBER_PATTERN.findall(base_text))
    for number in NUMBER_PATTERN.findall(summary):
        if number not in base_numbers:
            return f"resumo cita número que não está no currículo: {number}"
    base_words = {normalize_text(word) for word in WORD_PATTERN.findall(base_text)}
    for word in find_words_inside_sentences(summary):
        if word[0].isupper() and normalize_text(word) not in base_words:
            return f"resumo cita nome que não está no currículo: {word}"
    return None
