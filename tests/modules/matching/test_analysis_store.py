from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from autoapply.modules.jobs.models import Job
from autoapply.modules.jobs.store import insert_job
from autoapply.modules.matching.models import Analyzer, JobAnalysis
from autoapply.modules.matching.store import find_analysis, save_analysis
from autoapply.shared.database import open_database


def test_saved_analysis_is_found_with_lists_preserved(tmp_path: Path, build_job: Callable[..., Job]) -> None:
    analysis = JobAnalysis(
        job_id="4481248162",
        resume_name="Back-end .NET",
        score=82,
        pre_score=64,
        summary="Boa aderência em C# e ASP.NET Core.",
        requirements=["C#", "ASP.NET Core", "Azure"],
        keywords=["C#", "APIs REST"],
        gap=["Azure"],
        analyzer=Analyzer.CLAUDE,
        model="sonnet",
        analyzed_at=datetime(2026, 10, 21, 16, 0, 0),
    )
    with open_database(tmp_path / "autoapply.db") as connection:
        insert_job(connection, build_job())
        save_analysis(connection, analysis)

        assert find_analysis(connection, "4481248162") == analysis
        assert find_analysis(connection, "999") is None
