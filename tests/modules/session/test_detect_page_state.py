from collections.abc import Callable

import pytest

from autoapply.modules.session.detection import detect_page_state
from autoapply.modules.session.models import PageState


def test_feed_with_global_nav_is_logged_in(read_page: Callable[[str], str]) -> None:
    state = detect_page_state("https://www.linkedin.com/feed/foryou/", read_page("feed.html"))

    assert state == PageState.LOGGED_IN


def test_feed_without_global_nav_is_unknown(read_page: Callable[[str], str]) -> None:
    state = detect_page_state("https://www.linkedin.com/feed/", read_page("blank.html"))

    assert state == PageState.UNKNOWN


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/login",
        "https://www.linkedin.com/uas/login?session_redirect=%2Ffeed%2F",
        "https://www.linkedin.com/authwall?trk=bf",
    ],
)
def test_login_and_authwall_urls_are_logged_out(url: str, read_page: Callable[[str], str]) -> None:
    state = detect_page_state(url, read_page("blank.html"))

    assert state == PageState.LOGGED_OUT


def test_page_with_password_form_is_logged_out(read_page: Callable[[str], str]) -> None:
    state = detect_page_state("https://www.linkedin.com/", read_page("login_form.html"))

    assert state == PageState.LOGGED_OUT


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/checkpoint/challenge/AgG1x?ut=abc",
        "https://www.linkedin.com/checkpoint/lg/login-submit",
    ],
)
def test_checkpoint_urls_are_checkpoint(url: str, read_page: Callable[[str], str]) -> None:
    state = detect_page_state(url, read_page("login_form.html"))

    assert state == PageState.CHECKPOINT


def test_feed_with_captcha_iframe_is_checkpoint(read_page: Callable[[str], str]) -> None:
    state = detect_page_state("https://www.linkedin.com/feed/foryou/", read_page("feed_captcha.html"))

    assert state == PageState.CHECKPOINT


def test_job_page_with_invisible_recaptcha_badge_is_not_checkpoint(read_page: Callable[[str], str]) -> None:
    state = detect_page_state(
        "https://www.linkedin.com/jobs/view/4479314122/", read_page("job_invisible_recaptcha.html")
    )

    assert state == PageState.LOGGED_IN


def test_other_page_is_unknown(read_page: Callable[[str], str]) -> None:
    state = detect_page_state("https://www.linkedin.com/company/acme/", read_page("blank.html"))

    assert state == PageState.UNKNOWN
