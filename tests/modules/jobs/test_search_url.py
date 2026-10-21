import copy
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from autoapply.modules.config.models import Busca
from autoapply.modules.config.loader import parse_config_data
from autoapply.modules.jobs.search_url import build_search_url, collect_search_terms


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


def test_collect_search_terms_joins_resume_searches_without_repeating(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    data = copy.deepcopy(valid_data)
    data["curriculos"][0]["buscas"] = ["Desenvolvedor Python", "Back-end Python"]
    data["curriculos"][1]["buscas"] = ["Analista de Dados", "desenvolvedor python"]
    config = parse_config_data(data, base_dir)

    assert collect_search_terms(config) == ["Desenvolvedor Python", "Back-end Python", "Analista de Dados"]
