import copy
from datetime import datetime
from pathlib import Path

from autoapply.modules.config.loader import parse_config_data
from autoapply.modules.matching.keywords import (
    build_keyword_analysis,
    build_vocabulary,
    choose_best_resume,
    find_terms,
)
from autoapply.modules.matching.models import Analyzer, JobAnalysis, ResumeMatch
from autoapply.modules.resumes.models import Resume

VOCABULARY = ["C#", ".NET", "ASP.NET Core", "Node.js", "Java", "JavaScript", "SQL Server", "Testes unitários"]


def test_find_terms_matches_symbols_accents_and_whole_words_once() -> None:
    text = (
        "Vaga para c# com .net 8 e asp.net core. Conhecimento em NODE.JS e javascript; "
        "sql server e testes unitarios. Mais C# no dia a dia."
    )

    assert find_terms(text, VOCABULARY) == [
        "C#",
        ".NET",
        "ASP.NET Core",
        "Node.js",
        "JavaScript",
        "SQL Server",
        "Testes unitários",
    ]


def test_build_vocabulary_joins_experience_keys_and_fixed_terms_without_repeating(
    valid_data: dict[str, object], base_dir: Path
) -> None:
    data = copy.deepcopy(valid_data)
    data["experiencia_anos"] = {"total_desenvolvimento": 5, "Python": 3, "c#": 2}
    vocabulary = build_vocabulary(parse_config_data(data, base_dir))

    assert vocabulary[:2] == ["Python", "c#"]
    assert "total_desenvolvimento" not in vocabulary
    assert [term.casefold() for term in vocabulary].count("c#") == 1
    assert {"Kafka", "ASP.NET Core", "Testes unitários"} <= set(vocabulary)


def build_resume(name: str, text: str, is_default: bool = False, problem: str | None = None) -> Resume:
    return Resume(
        name=name,
        path=Path(f"cv_base/{name}.docx"),
        is_default=is_default,
        searches=[],
        text=text,
        problem=problem,
    )


JOB_DESCRIPTION = "Precisamos de C# e .NET, com Azure e Kafka."


def test_choose_best_resume_picks_highest_share_of_job_terms() -> None:
    resumes = [
        build_resume("Back-end", "Experiência com C# e .NET.", is_default=True),
        build_resume("Cloud", "C#, Azure e Kafka em produção."),
    ]

    match = choose_best_resume(JOB_DESCRIPTION, resumes, VOCABULARY + ["Azure", "Kafka"])

    assert match == ResumeMatch(
        resume_name="Cloud",
        pre_score=75,
        job_terms=["C#", ".NET", "Azure", "Kafka"],
        missing_terms=[".NET"],
    )


def test_choose_best_resume_prefers_default_on_tie_and_skips_unreadable() -> None:
    resumes = [
        build_resume("Cloud", "C# e Azure."),
        build_resume("Back-end", "C# e .NET.", is_default=True),
        build_resume("Escaneado", "C# .NET Azure Kafka", problem="texto insuficiente"),
    ]

    match = choose_best_resume(JOB_DESCRIPTION, resumes, VOCABULARY + ["Azure", "Kafka"])

    assert (match.resume_name, match.pre_score) == ("Back-end", 50)


def test_choose_best_resume_without_known_terms_scores_zero_with_default() -> None:
    resumes = [build_resume("Cloud", "C# e Azure."), build_resume("Back-end", "C# e .NET.", is_default=True)]

    match = choose_best_resume("Vaga de atendimento ao cliente.", resumes, VOCABULARY)

    assert match == ResumeMatch(resume_name="Back-end", pre_score=0, job_terms=[], missing_terms=[])


def test_build_keyword_analysis_marks_simplified_analysis() -> None:
    match = ResumeMatch(resume_name="Cloud", pre_score=75, job_terms=["C#", "Azure"], missing_terms=["Azure"])
    analyzed_at = datetime(2026, 10, 21, 17, 0, 0)

    analysis = build_keyword_analysis("4481248162", match, analyzed_at)

    assert analysis == JobAnalysis(
        job_id="4481248162",
        resume_name="Cloud",
        score=75,
        pre_score=75,
        summary="Análise simplificada por palavras-chave (sem LLM).",
        requirements=["C#", "Azure"],
        keywords=["C#", "Azure"],
        gap=["Azure"],
        analyzer=Analyzer.KEYWORDS,
        model=None,
        analyzed_at=analyzed_at,
    )
