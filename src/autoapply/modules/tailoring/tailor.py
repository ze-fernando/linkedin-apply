import dataclasses
import sqlite3
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from autoapply.modules.applying.models import ApplicationCandidate
from autoapply.modules.jobs.models import Job
from autoapply.modules.matching.models import JobAnalysis, ProviderAnswer
from autoapply.modules.resumes.loader import read_text_and_problem
from autoapply.modules.search_mode.folders import MAX_FOLDER_NAME_LENGTH, cut_slug, slugify
from autoapply.modules.tailoring.models import (
    ResumeStructureError,
    TailoredResume,
    TailoringPlan,
    TailoringResult,
    TailoringStatus,
)
from autoapply.modules.tailoring.plan import apply_tailoring_plan
from autoapply.modules.tailoring.prompt import build_tailoring_prompt
from autoapply.modules.tailoring.resume_structure import read_resume_document
from autoapply.modules.tailoring.store import find_tailored_resume, save_tailored_resume
from autoapply.modules.tailoring.template import render_resume_html
from autoapply.modules.tailoring.verification import find_new_information

NO_PROVIDER_REASON = "nenhum provedor de LLM respondeu"
TAILORABLE_SUFFIX = ".docx"
USED_WARNING = "cv ajustado"


def discard(reason: str, answer: ProviderAnswer[TailoringPlan] | None, pdf_path: Path | None = None) -> TailoringResult:
    return TailoringResult(
        status=TailoringStatus.DISCARDED,
        pdf_path=pdf_path,
        reason=reason,
        provider=answer.provider if answer else None,
        model=answer.model if answer else None,
    )


def tailor_resume(
    base_resume: Path,
    job: Job,
    analysis: JobAnalysis,
    vocabulary: list[str],
    ask: Callable[[str], ProviderAnswer[TailoringPlan] | None],
    render_pdf: Callable[[str, Path], Path],
    pdf_path: Path,
) -> TailoringResult:
    try:
        base = read_resume_document(base_resume)
    except ResumeStructureError as error:
        return discard(str(error), None)
    answer = ask(build_tailoring_prompt(base, job, analysis))
    if answer is None:
        return discard(NO_PROVIDER_REASON, None)
    tailored = apply_tailoring_plan(base, answer.value)
    if isinstance(tailored, str):
        return discard(tailored, answer)
    new_information = find_new_information(base, tailored, vocabulary)
    if new_information is not None:
        return discard(new_information, answer)
    render_pdf(render_resume_html(tailored), pdf_path)
    _, text_problem = read_text_and_problem(pdf_path)
    if text_problem is not None:
        return discard(f"PDF ajustado: {text_problem}", answer, pdf_path)
    return TailoringResult(
        status=TailoringStatus.USED, pdf_path=pdf_path, reason=None, provider=answer.provider, model=answer.model
    )


def build_pdf_name(job: Job, day: date, pdf_dir: Path) -> str:
    slug = slugify(f"{day.isoformat()} {job.company} {job.title}")
    name = f"{cut_slug(slug, MAX_FOLDER_NAME_LENGTH)}.pdf"
    if not (pdf_dir / name).exists():
        return name
    return f"{cut_slug(slug, MAX_FOLDER_NAME_LENGTH - len(job.id) - 1)}-{job.id}.pdf"


def add_warning(candidate: ApplicationCandidate, warning: str) -> str:
    return warning if candidate.warning is None else f"{candidate.warning} · {warning}"


def use_tailored_pdf(candidate: ApplicationCandidate, pdf_path: Path) -> ApplicationCandidate:
    return dataclasses.replace(
        candidate,
        resume_file=pdf_path,
        warning=add_warning(candidate, USED_WARNING),
        tailoring=TailoringStatus.USED,
    )


def find_reusable_pdf(connection: sqlite3.Connection, job_id: str) -> Path | None:
    saved = find_tailored_resume(connection, job_id)
    if saved is None or saved.status != TailoringStatus.USED or saved.pdf_path is None:
        return None
    return saved.pdf_path if saved.pdf_path.exists() else None


def prepare_tailored_candidate(
    connection: sqlite3.Connection,
    candidate: ApplicationCandidate,
    simulate: bool,
    tailor: Callable[[ApplicationCandidate, Path], TailoringResult],
    now: datetime,
    pdf_dir: Path,
) -> ApplicationCandidate:
    if candidate.resume_file.suffix.lower() != TAILORABLE_SUFFIX:
        return candidate
    reusable = None if simulate else find_reusable_pdf(connection, candidate.job.id)
    if reusable is not None:
        return use_tailored_pdf(candidate, reusable)
    result = tailor(candidate, pdf_dir / build_pdf_name(candidate.job, now.date(), pdf_dir))
    if not simulate:
        save_tailored_resume(
            connection,
            TailoredResume(
                job_id=candidate.job.id,
                base_resume=candidate.resume_file,
                pdf_path=result.pdf_path,
                status=result.status,
                reason=result.reason,
                provider=result.provider,
                model=result.model,
                created_at=now,
            ),
        )
    if result.status == TailoringStatus.USED and result.pdf_path is not None:
        return use_tailored_pdf(candidate, result.pdf_path)
    return dataclasses.replace(
        candidate,
        warning=add_warning(candidate, f"ajuste descartado: {result.reason}"),
        tailoring=TailoringStatus.DISCARDED,
    )
