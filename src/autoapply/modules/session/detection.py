from enum import StrEnum
from html.parser import HTMLParser
from urllib.parse import urlparse

LOGGED_IN_PATH_PREFIXES = ("/feed", "/jobs", "/in/")
LOGGED_OUT_PATH_PREFIXES = ("/login", "/uas/login", "/authwall")
CHECKPOINT_PATH_PREFIXES = ("/checkpoint/", "/challenge")
GLOBAL_NAV_LINK_PREFIXES = ("/mynetwork", "/messaging")
CAPTCHA_MARKERS = ("captcha", "/checkpoint/challenge")

HtmlTag = tuple[str, dict[str, str]]


class PageState(StrEnum):
    LOGGED_IN = "LOGGED_IN"
    LOGGED_OUT = "LOGGED_OUT"
    CHECKPOINT = "CHECKPOINT"
    UNKNOWN = "UNKNOWN"


def collect_tags(html: str) -> list[HtmlTag]:
    tags = []
    parser = HTMLParser()
    parser.handle_starttag = lambda tag, attrs: tags.append(
        (tag, {name: value or "" for name, value in attrs})
    )
    parser.feed(html)
    return tags


def has_global_nav(tags: list[HtmlTag]) -> bool:
    return any(
        tag == "a" and urlparse(attrs.get("href", "")).path.startswith(GLOBAL_NAV_LINK_PREFIXES)
        for tag, attrs in tags
    )


def has_captcha_frame(tags: list[HtmlTag]) -> bool:
    return any(
        tag == "iframe" and any(marker in attrs.get(name, "") for name in ("id", "src") for marker in CAPTCHA_MARKERS)
        for tag, attrs in tags
    )


def has_password_form(tags: list[HtmlTag]) -> bool:
    return any(tag == "input" and attrs.get("type") == "password" for tag, attrs in tags)


def detect_page_state(url: str, html: str) -> PageState:
    path = urlparse(url).path
    tags = collect_tags(html)
    if path.startswith(CHECKPOINT_PATH_PREFIXES) or has_captcha_frame(tags):
        return PageState.CHECKPOINT
    if path.startswith(LOGGED_OUT_PATH_PREFIXES) or has_password_form(tags):
        return PageState.LOGGED_OUT
    if path.startswith(LOGGED_IN_PATH_PREFIXES) and has_global_nav(tags):
        return PageState.LOGGED_IN
    return PageState.UNKNOWN
