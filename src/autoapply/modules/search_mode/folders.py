import re
import sqlite3
from datetime import date
from pathlib import Path

from autoapply.modules.config.models import Config
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import update_job_status
from autoapply.modules.matching.models import Analyzer, JobAnalysis
from autoapply.modules.matching.store import list_jobs_by_score
from autoapply.shared.text import normalize_text

MAX_FOLDER_NAME_LENGTH = 60
SIMPLIFIED_WARNING = "> **Aviso:** análise simplificada por palavras-chave (sem LLM)."
LOW_SCORE_WARNING = "> **Aviso:** score {score} abaixo do mínimo configurado ({minimum})."
ANALYZER_LABELS = {Analyzer.KEYWORDS: "palavras-chave"}
SAVE_RESUME_HINT = "Salve o currículo adaptado nesta pasta como `cv.docx` ou `cv.pdf`."


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize_text(text)).strip("-")


def cut_slug(slug: str, length: int) -> str:
    return slug[:length].rstrip("-")


def build_folder_name(job: Job, day: date, vagas_dir: Path) -> str:
    slug = slugify(f"{day.isoformat()} {job.company} {job.title}")
    name = cut_slug(slug, MAX_FOLDER_NAME_LENGTH)
    if not (vagas_dir / name).exists():
        return name
    return f"{cut_slug(slug, MAX_FOLDER_NAME_LENGTH - len(job.id) - 1)}-{job.id}"


def format_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- (nenhum)"


def format_analyzer(analysis: JobAnalysis) -> str:
    if analysis.analyzer in ANALYZER_LABELS:
        return ANALYZER_LABELS[analysis.analyzer]
    return f"{analysis.analyzer} ({analysis.model})"


def build_warnings(analysis: JobAnalysis, minimum_score: int) -> list[str]:
    warnings = []
    if analysis.analyzer == Analyzer.KEYWORDS:
        warnings.append(SIMPLIFIED_WARNING)
    if analysis.score < minimum_score:
        warnings.append(LOW_SCORE_WARNING.format(score=analysis.score, minimum=minimum_score))
    return warnings


def render_job_markdown(job: Job, analysis: JobAnalysis, resume_file: str, minimum_score: int) -> str:
    location = " · ".join(part for part in [job.location, job.workplace, job.posted] if part)
    header = "\n".join(
        [
            f"# {job.title} — {job.company}",
            "",
            f"- **Link:** {job.url}",
            f"- **Local:** {location}",
            f"- **Score:** {analysis.score}/100 · **Currículo sugerido:** {analysis.resume_name} (`{resume_file}`)",
            f"- **Análise:** {format_analyzer(analysis)}",
        ]
    )
    sections = [
        header,
        *build_warnings(analysis, minimum_score),
        f"## Resumo\n\n{analysis.summary}",
        f"## Requisitos\n\n{format_list(analysis.requirements)}",
        f"## Palavras-chave\n\n{format_list(analysis.keywords)}",
        f"## Gap (a vaga pede e o currículo não mostra)\n\n{format_list(analysis.gap)}",
        f"## Descrição completa\n\n{job.description or ''}",
        f"---\n{SAVE_RESUME_HINT}\n",
    ]
    return "\n\n".join(sections)


def format_resume_file(config: Config, resume_name: str) -> str:
    path = next((curriculo.arquivo for curriculo in config.curriculos if curriculo.nome == resume_name), None)
    if path is None:
        return "currículo não encontrado no config.md"
    return str(path.relative_to(Path.cwd())) if path.is_relative_to(Path.cwd()) else str(path)


def create_job_folders(connection: sqlite3.Connection, config: Config, vagas_dir: Path, day: date) -> list[Path]:
    selected = list_jobs_by_score(connection, JobStatus.EVALUATED)[: config.regras.modo_busca_quantidade]
    folders = []
    for job, analysis in selected:
        folder = vagas_dir / build_folder_name(job, day, vagas_dir)
        folder.mkdir(parents=True)
        markdown = render_job_markdown(
            job, analysis, format_resume_file(config, analysis.resume_name), config.regras.score_minimo
        )
        (folder / "vaga.md").write_text(markdown, encoding="utf-8")
        update_job_status(connection, job.id, JobStatus.AWAITING_RESUME)
        folders.append(folder)
    return folders
