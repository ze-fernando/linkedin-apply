from selectolax.lexbor import LexborHTMLParser, LexborNode

from autoapply.modules.jobs.models import JobCard, JobDetail

CARD_SELECTOR = "div[data-job-id]"
CARD_TITLE_SELECTOR = ".artdeco-entity-lockup__title strong"
CARD_COMPANY_SELECTOR = ".artdeco-entity-lockup__subtitle"
CARD_LOCATION_SELECTOR = ".artdeco-entity-lockup__caption li"
DETAIL_TITLE_SELECTOR = ".job-details-jobs-unified-top-card__job-title h1"
DETAIL_COMPANY_SELECTOR = ".job-details-jobs-unified-top-card__company-name"
DETAIL_FACTS_SELECTOR = ".job-details-jobs-unified-top-card__tertiary-description-container > span > .tvm__text"
DETAIL_WORKPLACE_SELECTOR = ".job-details-fit-level-preferences strong"
DETAIL_DESCRIPTION_SELECTOR = "#job-details"
DETAIL_APPLY_BUTTON_SELECTOR = "button.jobs-apply-button"
EASY_APPLY_LABEL = "Candidatura simplificada"
FACT_SEPARATOR = "·"
SKILL_MATCH_MARKER = "correspondência"
LINE_BREAK_SELECTOR = "p, li, br, div, ul, ol, h1, h2, h3, h4, h5, h6"


def read_text(node: LexborNode, selector: str) -> str:
    found = node.css_first(selector)
    return found.text(strip=True) if found else ""


def parse_job_cards(html: str) -> list[JobCard]:
    cards = {}
    for node in LexborHTMLParser(html).css(CARD_SELECTOR):
        title = read_text(node, CARD_TITLE_SELECTOR)
        if title:
            job_id = node.attributes["data-job-id"]
            cards.setdefault(
                job_id,
                JobCard(
                    id=job_id,
                    title=title,
                    company=read_text(node, CARD_COMPANY_SELECTOR),
                    location=read_text(node, CARD_LOCATION_SELECTOR),
                ),
            )
    return list(cards.values())


def read_facts(tree: LexborHTMLParser) -> list[str]:
    texts = [" ".join(node.text(separator=" ").split()) for node in tree.css(DETAIL_FACTS_SELECTOR)]
    return [text for text in texts if text and text != FACT_SEPARATOR]


def read_workplace(tree: LexborHTMLParser) -> str | None:
    labels = [node.text(strip=True) for node in tree.css(DETAIL_WORKPLACE_SELECTOR)]
    workplace = [label for label in labels if label and SKILL_MATCH_MARKER not in label]
    return " · ".join(workplace) or None


def read_description(tree: LexborHTMLParser) -> str:
    node = tree.css_first(DETAIL_DESCRIPTION_SELECTOR)
    if node is None:
        return ""
    for block in node.css(LINE_BREAK_SELECTOR):
        block.insert_after("\n")
    lines = [line.strip() for line in node.text().splitlines()]
    return "\n".join(line for line in lines if line)


def has_easy_apply_button(tree: LexborHTMLParser) -> bool:
    return any(EASY_APPLY_LABEL in node.text() for node in tree.css(DETAIL_APPLY_BUTTON_SELECTOR))


def parse_job_detail(html: str) -> JobDetail:
    tree = LexborHTMLParser(html)
    facts = read_facts(tree)
    return JobDetail(
        title=read_text(tree.root, DETAIL_TITLE_SELECTOR),
        company=read_text(tree.root, DETAIL_COMPANY_SELECTOR),
        location=facts[0] if facts else "",
        posted=facts[1] if len(facts) > 1 else None,
        workplace=read_workplace(tree),
        description=read_description(tree),
        has_easy_apply=has_easy_apply_button(tree),
    )
