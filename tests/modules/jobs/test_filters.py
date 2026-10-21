import copy

import pytest

from autoapply.modules.config.models import Busca
from autoapply.modules.jobs.filters import find_card_block_reason, find_description_block_reason
from autoapply.modules.jobs.models import JobCard


@pytest.fixture
def busca(valid_data: dict[str, object]) -> Busca:
    data = copy.deepcopy(valid_data["busca"])
    data["termos_bloqueados_no_titulo"] = ["Sênior", "Sr"]
    return Busca.model_validate(data)


def build_card(title: str, company: str = "Empresa Alfa") -> JobCard:
    return JobCard(id="1001", title=title, company=company, location="Brasil (Remoto)")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Desenvolvedor C# SENIOR", "título contém 'Sênior'"),
        ("Dev .NET SR", "título contém 'Sr'"),
        ("Engenheiro SRE", None),
        ("Desenvolvedor .NET", None),
    ],
)
def test_find_card_block_reason_matches_whole_blocked_title_terms(
    busca: Busca, title: str, expected: str | None
) -> None:
    assert find_card_block_reason(build_card(title), busca) == expected


@pytest.mark.parametrize("title", ["Desenvolvedor .NET Pleno/Sênior", "Dev Python Jr/Sr", "Desenvolvedor Júnior ou Sênior"])
def test_find_card_block_reason_allows_blocked_term_when_title_also_has_wanted_level(
    busca: Busca, title: str
) -> None:
    assert find_card_block_reason(build_card(title), busca) is None


def test_find_card_block_reason_blocks_mixed_title_when_its_level_is_not_wanted(busca: Busca) -> None:
    junior_only = busca.model_copy(update={"niveis": ["junior"]})

    assert find_card_block_reason(build_card("Desenvolvedor Pleno/Sênior"), junior_only) == "título contém 'Sênior'"


def test_find_card_block_reason_blocks_listed_company(busca: Busca) -> None:
    blocking = busca.model_copy(update={"empresas_bloqueadas": ["Consultoria Ômega"]})

    assert find_card_block_reason(build_card("Desenvolvedor .NET", company="CONSULTORIA OMEGA"), blocking) == (
        "empresa bloqueada: 'Consultoria Ômega'"
    )
    assert find_card_block_reason(build_card("Desenvolvedor .NET", company="Ômega Labs"), blocking) is None


def test_find_description_block_reason_matches_blocked_words(busca: Busca) -> None:
    blocking = busca.model_copy(update={"palavras_bloqueadas": ["presencial", "inglês fluente"]})

    assert find_description_block_reason("Vaga 100% PRESENCIAL em Recife.", blocking) == (
        "descrição contém 'presencial'"
    )
    assert find_description_block_reason("Exige Ingles Fluente.", blocking) == "descrição contém 'inglês fluente'"
    assert find_description_block_reason("Vaga remota, sem presencialidade.", blocking) is None
