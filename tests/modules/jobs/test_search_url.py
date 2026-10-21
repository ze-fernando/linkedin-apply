import copy
from urllib.parse import parse_qs, urlparse

import pytest

from autoapply.modules.config.models import Busca
from autoapply.modules.jobs.search_url import build_search_url


@pytest.fixture
def busca(valid_data: dict[str, object]) -> Busca:
    return Busca.model_validate(copy.deepcopy(valid_data["busca"]))


def read_query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


def test_build_search_url_applies_all_filters_for_term(busca: Busca) -> None:
    url = build_search_url("Desenvolvedor C#", busca)

    assert url.startswith("https://www.linkedin.com/jobs/search/?")
    assert read_query(url) == {
        "keywords": ["Desenvolvedor C#"],
        "location": ["Brasil"],
        "geoId": ["106057199"],
        "f_AL": ["true"],
        "f_WT": ["2"],
        "f_TPR": ["r604800"],
        "f_E": ["2,3,4"],
    }


def test_build_search_url_maps_only_junior_level(busca: Busca) -> None:
    junior_only = busca.model_copy(update={"niveis": ["junior"], "publicadas_ha_no_maximo_dias": 1})

    query = read_query(build_search_url("Python", junior_only))

    assert query["f_E"] == ["2"]
    assert query["f_TPR"] == ["r86400"]
