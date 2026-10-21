import logging
import sqlite3
from datetime import datetime

from autoapply.modules.config.models import Config, ProvedorLlm
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import list_jobs, update_job_status
from autoapply.modules.matching.keywords import (
    build_keyword_analysis,
    build_vocabulary,
    choose_best_resume,
    match_resume,
)
from autoapply.modules.matching.models import (
    Analyzer,
    EvaluationSummary,
    JobAnalysis,
    ProviderAnalysis,
    ProviderRun,
    ResumeMatch,
)
from autoapply.modules.matching.prompt import build_analysis_prompt
from autoapply.modules.matching.providers import analyze_with_fallback
from autoapply.modules.matching.store import save_analysis
from autoapply.modules.resumes.models import Resume

logger = logging.getLogger("autoapply.matching")


def rank_by_pre_score(jobs: list[Job], resumes: list[Resume], vocabulary: list[str]) -> list[tuple[Job, ResumeMatch]]:
    matches = [(job, choose_best_resume(job.description or "", resumes, vocabulary)) for job in jobs]
    return sorted(matches, key=lambda pair: pair[1].pre_score, reverse=True)


def build_llm_analysis(
    job_id: str, result: ProviderAnalysis, chosen_match: ResumeMatch, analyzed_at: datetime
) -> JobAnalysis:
    return JobAnalysis(
        job_id=job_id,
        resume_name=result.analysis.resume_name,
        score=result.analysis.score,
        pre_score=chosen_match.pre_score,
        summary=result.analysis.summary,
        requirements=result.analysis.requirements,
        keywords=result.analysis.keywords,
        gap=result.analysis.gap,
        analyzer=Analyzer(result.provider),
        model=result.model,
        analyzed_at=analyzed_at,
    )


def analyze_job(
    job: Job, best_match: ResumeMatch, resumes: list[Resume], config: Config, run: ProviderRun | None
) -> JobAnalysis:
    result = None
    if run is not None:
        prompt = build_analysis_prompt(job, resumes, config)
        result = analyze_with_fallback(prompt, [resume.name for resume in resumes], config.llm, run)
    if result is None:
        return build_keyword_analysis(job.id, best_match, datetime.now())
    chosen = next(resume for resume in resumes if resume.name == result.analysis.resume_name)
    return build_llm_analysis(job.id, result, match_resume(best_match.job_terms, chosen), datetime.now())


def evaluate_jobs(
    connection: sqlite3.Connection, config: Config, resumes: list[Resume], providers: list[ProvedorLlm]
) -> EvaluationSummary:
    readable = [resume for resume in resumes if resume.problem is None]
    ranked = rank_by_pre_score(list_jobs(connection, JobStatus.COLLECTED), readable, build_vocabulary(config))
    run = ProviderRun(providers=providers)
    llm_count = 0
    for position, (job, best_match) in enumerate(ranked):
        use_llm = position < config.regras.analise_llm_max_vagas
        analysis = analyze_job(job, best_match, readable, config, run if use_llm else None)
        save_analysis(connection, analysis)
        update_job_status(connection, job.id, JobStatus.EVALUATED)
        llm_count += analysis.analyzer != Analyzer.KEYWORDS
        logger.info(
            "vaga %s avaliada por %s: score %d",
            job.id,
            analysis.analyzer,
            analysis.score,
            extra={"event": "matching.job_evaluated", "job_id": job.id},
        )
    return EvaluationSummary(llm=llm_count, keywords=len(ranked) - llm_count)
