from urllib.parse import urlencode

from autoapply.modules.config.models import Busca, Config

SEARCH_BASE_URL = "https://www.linkedin.com/jobs/search/"
BRAZIL_GEO_ID = "106057199"
REMOTE_WORKPLACE = "2"
SECONDS_PER_DAY = 86400
EXPERIENCE_LEVELS = {"junior": ["2"], "pleno": ["3", "4"]}


def build_search_url(term: str, busca: Busca) -> str:
    levels = [level for nivel in busca.niveis for level in EXPERIENCE_LEVELS[nivel]]
    query = {
        "keywords": term,
        "location": busca.localizacao,
        "geoId": BRAZIL_GEO_ID,
        "f_AL": "true",
        "f_WT": REMOTE_WORKPLACE,
        "f_TPR": f"r{busca.publicadas_ha_no_maximo_dias * SECONDS_PER_DAY}",
        "f_E": ",".join(levels),
    }
    return f"{SEARCH_BASE_URL}?{urlencode(query)}"


def collect_search_terms(config: Config) -> list[str]:
    terms = {}
    for curriculo in config.curriculos:
        for term in curriculo.buscas:
            terms.setdefault(term.casefold(), term)
    return list(terms.values())
