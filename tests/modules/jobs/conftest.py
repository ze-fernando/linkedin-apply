from collections.abc import Callable

import pytest

from tests.fakes.linkedin_jobs import SEARCH_PATH, FakeJob, build_search_page


@pytest.fixture
def serve_search_page(serve_pages: Callable[[dict[str, str]], None]) -> Callable[..., None]:
    def serve(jobs: list[FakeJob], rendered_cards: int | None = None, initial_items: int | None = None) -> None:
        visible = len(jobs) if rendered_cards is None else rendered_cards
        present = len(jobs) if initial_items is None else initial_items
        serve_pages({SEARCH_PATH: build_search_page(jobs, visible, present)})

    return serve
