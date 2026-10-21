import copy
from collections.abc import Callable
from pathlib import Path

from autoapply.modules.config.loader import parse_config_data
from autoapply.modules.jobs.models import Job
from autoapply.modules.matching.prompt import build_analysis_prompt
from autoapply.modules.resumes.models import Resume


def build_resume(name: str, text: str) -> Resume:
    return Resume(name=name, path=Path(f"cv_base/{name}.docx"), is_default=False, searches=[], text=text, problem=None)


def test_build_analysis_prompt_includes_job_resumes_and_profile_without_contacts(
    valid_data: dict[str, object], base_dir: Path, build_job: Callable[..., Job]
) -> None:
    config = parse_config_data(copy.deepcopy(valid_data), base_dir)
    resumes = [
        build_resume("Back-end", "Maria Teste · maria.teste@example.com · +55 11 91234-5678\nAPIs em C# e .NET."),
        build_resume("Dados", "Maria Teste · (11) 91234-5678\nPipelines em Python."),
    ]

    prompt = build_analysis_prompt(build_job(description="Vaga para C# e ASP.NET Core."), resumes, config)

    for expected in [
        "Vaga para C# e ASP.NET Core.",
        "Desenvolvedor .NET Pleno",
        "Currículo: Back-end",
        "APIs em C# e .NET.",
        "Currículo: Dados",
        "Pipelines em Python.",
        "junior, pleno",
        "Python: 3",
        "nunca invente",
    ]:
        assert expected in prompt
    for contact in ["maria.teste@example.com", "91234-5678"]:
        assert contact not in prompt
