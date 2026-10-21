import pytest

from autoapply.modules.applying.answer_rules import (
    choose_salary,
    find_experience_technology,
    find_experience_years,
    find_salary_question,
)
from autoapply.modules.applying.models import SalaryQuestion
from autoapply.modules.config.models import Pretensao

EXPERIENCE = {"total_desenvolvimento": 5, "C#": 2, "ASP.NET Core": 2, "Python": 3, "Node.js": 1}


@pytest.mark.parametrize(
    ("question", "technology"),
    [
        ("How many years of work experience do you have with ASP.NET Core?", "asp.net core"),
        ("How many years of experience do you have with C#?", "c#"),
        ("How many years of experience in Python", "python"),
        ("Quantos anos de experiência você tem com Node.js?", "node.js"),
        ("Quantos anos de experiência com C#?", "c#"),
        ("¿Cuántos años de experiencia tienes con Python?", "python"),
        ("Cuántos años de experiencia en C#?", "c#"),
        ("Você trabalharia remotamente?", None),
        ("Cuál es tu pretendido mensual en usd?", None),
    ],
)
def test_find_experience_technology_reads_pt_en_and_es(question: str, technology: str | None) -> None:
    assert find_experience_technology(question) == technology


def test_find_experience_years_matches_whole_configured_technology() -> None:
    assert find_experience_years("asp.net core", EXPERIENCE) == 2
    assert find_experience_years("c#", EXPERIENCE) == 2
    assert find_experience_years("asp.net", EXPERIENCE) is None
    assert find_experience_years("aws", EXPERIENCE) is None


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Qual a sua pretensão salarial?", SalaryQuestion(is_pj=False, foreign_currency=False)),
        ("Pretensão salarial (PJ)", SalaryQuestion(is_pj=True, foreign_currency=False)),
        ("Qual sua expectativa salarial como PJ?", SalaryQuestion(is_pj=True, foreign_currency=False)),
        ("What is your salary expectation?", SalaryQuestion(is_pj=False, foreign_currency=False)),
        ("Expected salary in USD", SalaryQuestion(is_pj=False, foreign_currency=True)),
        ("Cuál es tu pretendido mensual en usd?", SalaryQuestion(is_pj=False, foreign_currency=True)),
        ("¿Cuál es tu pretensión salarial en dólares?", SalaryQuestion(is_pj=False, foreign_currency=True)),
        ("Salary expectation (EUR)", SalaryQuestion(is_pj=False, foreign_currency=True)),
        ("Você trabalharia remotamente?", None),
        ("How many years of experience with C#?", None),
    ],
)
def test_find_salary_question_detects_contract_and_foreign_currency(
    question: str, expected: SalaryQuestion | None
) -> None:
    assert find_salary_question(question) == expected


@pytest.mark.parametrize(
    ("title", "is_pj", "salary"),
    [
        ("Desenvolvedor .NET Júnior", False, 3500),
        ("Desenvolvedor .NET Jr", True, 4500),
        ("Desenvolvedor .NET Pleno", False, 6500),
        ("Desenvolvedor Jr/Pleno", True, 8000),
        ("Software Engineer", False, 3500),
    ],
)
def test_choose_salary_uses_title_level_contract_and_default_level(
    valid_data: dict[str, object], title: str, is_pj: bool, salary: int
) -> None:
    pretensao = Pretensao.model_validate(valid_data["pretensao"])

    assert choose_salary(title, SalaryQuestion(is_pj=is_pj, foreign_currency=False), pretensao) == salary
