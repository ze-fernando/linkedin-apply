import copy
from pathlib import Path

import pytest
from pydantic import ValidationError

from autoapply.modules.config.loader import parse_config_data


def collect_errors(data: dict[str, object], base_dir: Path) -> list[tuple[str, str]]:
    with pytest.raises(ValidationError) as raised:
        parse_config_data(data, base_dir)
    return [(".".join(str(part) for part in error["loc"]), error["msg"]) for error in raised.value.errors()]


def test_parse_config_data_returns_typed_config_for_valid_data(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    config = parse_config_data(valid_data, base_dir)

    assert config.perfil.nome == "Maria Teste da Silva"
    assert config.pretensao.pleno.pj.formulario == 8000
    assert config.busca.niveis == ["junior", "pleno"]
    assert config.curriculos[0].arquivo == base_dir / "cv_base/backend.docx"
    assert config.curriculos[1].padrao is False
    assert config.regras.limite_diario == 15


def test_parse_config_data_rejects_form_salary_outside_range(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    data = copy.deepcopy(valid_data)
    data["pretensao"]["pleno"]["pj"]["formulario"] = 9500

    errors = collect_errors(data, base_dir)

    assert errors == [("pretensao.pleno.pj.formulario", "Value error, deve estar entre min (7000) e max (9000)")]


@pytest.mark.parametrize("default_flags", [(False, False), (True, True)])
def test_parse_config_data_requires_exactly_one_default_resume(
    valid_data: dict[str, object], base_dir: Path, default_flags: tuple[bool, bool]
) -> None:
    data = copy.deepcopy(valid_data)
    for resume, is_default in zip(data["curriculos"], default_flags):
        resume["padrao"] = is_default

    errors = collect_errors(data, base_dir)

    assert errors == [("curriculos", "Value error, exatamente um currículo deve ter padrao: true")]


def test_parse_config_data_rejects_duplicated_resume_names(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    data = copy.deepcopy(valid_data)
    data["curriculos"][1]["nome"] = "Back-end"

    errors = collect_errors(data, base_dir)

    assert errors == [("curriculos", "Value error, nome de currículo repetido: Back-end")]


def test_parse_config_data_rejects_missing_resume_file(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    data = copy.deepcopy(valid_data)
    data["curriculos"][1]["arquivo"] = "cv_base/inexistente.pdf"

    errors = collect_errors(data, base_dir)

    assert errors == [("curriculos.1.arquivo", "Value error, arquivo não encontrado: cv_base/inexistente.pdf")]


def test_parse_config_data_rejects_unsupported_resume_extension(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    (base_dir / "cv_base" / "antigo.odt").write_bytes(b"odt")
    data = copy.deepcopy(valid_data)
    data["curriculos"][1]["arquivo"] = "cv_base/antigo.odt"

    errors = collect_errors(data, base_dir)

    assert errors == [("curriculos.1.arquivo", "Value error, formato não suportado (use .docx ou .pdf): cv_base/antigo.odt")]


@pytest.mark.parametrize("email", ["maria.teste", "maria@", "maria@example", "maria teste@example.com"])
def test_parse_config_data_rejects_invalid_email(
    valid_data: dict[str, object], base_dir: Path, email: str
) -> None:
    data = copy.deepcopy(valid_data)
    data["perfil"]["email"] = email

    errors = collect_errors(data, base_dir)

    assert errors == [("perfil.email", "Value error, e-mail inválido")]


@pytest.mark.parametrize("phone", ["11 91234-5678", "(11) 91234-5678", "+1 555 0100"])
def test_parse_config_data_requires_brazilian_phone_prefix(
    valid_data: dict[str, object], base_dir: Path, phone: str
) -> None:
    data = copy.deepcopy(valid_data)
    data["perfil"]["telefone"] = phone

    errors = collect_errors(data, base_dir)

    assert errors == [("perfil.telefone", "Value error, deve começar com +55")]


def test_parse_config_data_accepts_only_remote_search(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    data = copy.deepcopy(valid_data)
    data["busca"]["modalidade"] = "hibrido"

    errors = collect_errors(data, base_dir)

    assert errors == [("busca.modalidade", "Input should be 'remoto'")]


def test_parse_config_data_accepts_only_junior_and_pleno_levels(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    data = copy.deepcopy(valid_data)
    data["busca"]["niveis"] = ["junior", "senior"]
    data["pretensao"]["padrao_nivel"] = "senior"

    errors = collect_errors(data, base_dir)

    assert errors == [
        ("pretensao.padrao_nivel", "Input should be 'junior' or 'pleno'"),
        ("busca.niveis.1", "Input should be 'junior' or 'pleno'"),
    ]


def test_parse_config_data_accepts_only_known_language_levels(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    data = copy.deepcopy(valid_data)
    data["idiomas"]["espanhol"] = "mais ou menos"

    errors = collect_errors(data, base_dir)

    assert errors == [
        ("idiomas.espanhol", "Input should be 'basico', 'intermediario', 'avancado', 'fluente' or 'nativo'")
    ]


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("regras", "score_minimo", 101, "Input should be less than or equal to 100"),
        ("regras", "score_minimo", -1, "Input should be greater than or equal to 0"),
        ("regras", "limite_diario", 0, "Input should be greater than or equal to 1"),
        ("experiencia_anos", "Python", -2, "Input should be greater than or equal to 0"),
    ],
)
def test_parse_config_data_enforces_numeric_bounds(
    valid_data: dict[str, object], base_dir: Path, section: str, field: str, value: int, message: str
) -> None:
    data = copy.deepcopy(valid_data)
    data[section][field] = value

    errors = collect_errors(data, base_dir)

    assert errors == [(f"{section}.{field}", message)]


@pytest.mark.parametrize("generic_answer", ["", "   "])
def test_parse_config_data_requires_generic_answer_text(
    valid_data: dict[str, object], base_dir: Path, generic_answer: str
) -> None:
    data = copy.deepcopy(valid_data)
    data["resposta_generica"] = generic_answer

    errors = collect_errors(data, base_dir)

    assert errors == [("resposta_generica", "Value error, não pode ficar vazia")]


def test_parse_config_data_rejects_unknown_fields(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    data = copy.deepcopy(valid_data)
    data["perfil"]["apelido"] = "Mari"

    errors = collect_errors(data, base_dir)

    assert errors == [("perfil.apelido", "Extra inputs are not permitted")]
