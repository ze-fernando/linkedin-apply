from datetime import datetime

from autoapply.modules.config.models import Config
from autoapply.modules.matching.models import Analyzer, JobAnalysis, ResumeMatch
from autoapply.modules.resumes.models import Resume
from autoapply.shared.text import contains_term, normalize_text

NON_TECHNOLOGY_EXPERIENCE_KEYS = {"total_desenvolvimento"}
SIMPLIFIED_ANALYSIS_SUMMARY = "Análise simplificada por palavras-chave (sem LLM)."
TECH_VOCABULARY = [
    "C#",
    "Java",
    "Kotlin",
    "PHP",
    "Ruby",
    "Rust",
    "C++",
    "Scala",
    "Dart",
    "Elixir",
    "ASP.NET",
    "ASP.NET Core",
    ".NET Framework",
    "Blazor",
    "LINQ",
    "xUnit",
    "Angular",
    "Vue",
    "Nuxt",
    "HTML",
    "CSS",
    "Tailwind",
    "Redux",
    "Flutter",
    "Spring",
    "Django",
    "FastAPI",
    "Flask",
    "Express",
    "Laravel",
    "GraphQL",
    "REST",
    "gRPC",
    "SQL Server",
    "Oracle",
    "Redis",
    "Elasticsearch",
    "DynamoDB",
    "Kafka",
    "RabbitMQ",
    "AWS",
    "Azure",
    "GCP",
    "Kubernetes",
    "Terraform",
    "CI/CD",
    "GitHub Actions",
    "Azure DevOps",
    "Jenkins",
    "Git",
    "Microservices",
    "Serverless",
    "TDD",
    "Testes unitários",
    "Clean Architecture",
    "DDD",
    "SOLID",
    "Scrum",
    "RPA",
    "Selenium",
    "Playwright",
    "LangChain",
    "OpenAI",
    "Power Automate",
    "Zapier",
    "Make",
]


def unique_terms(terms: list[str]) -> list[str]:
    unique = {}
    for term in terms:
        unique.setdefault(normalize_text(term), term)
    return list(unique.values())


def build_vocabulary(config: Config) -> list[str]:
    experience_terms = [key for key in config.experiencia_anos if key not in NON_TECHNOLOGY_EXPERIENCE_KEYS]
    return unique_terms(experience_terms + TECH_VOCABULARY)


def find_terms(text: str, vocabulary: list[str]) -> list[str]:
    return unique_terms([term for term in vocabulary if contains_term(text, term)])


def match_resume(job_terms: list[str], resume: Resume) -> ResumeMatch:
    missing_terms = [term for term in job_terms if not contains_term(resume.text, term)]
    covered = len(job_terms) - len(missing_terms)
    return ResumeMatch(
        resume_name=resume.name,
        pre_score=round(100 * covered / len(job_terms)) if job_terms else 0,
        job_terms=job_terms,
        missing_terms=missing_terms,
    )


def choose_best_resume(description: str, resumes: list[Resume], vocabulary: list[str]) -> ResumeMatch:
    job_terms = find_terms(description, vocabulary)
    readable = [resume for resume in resumes if resume.problem is None]
    ranked = sorted(readable, key=lambda resume: not resume.is_default)
    return max((match_resume(job_terms, resume) for resume in ranked), key=lambda match: match.pre_score)


def build_keyword_analysis(job_id: str, match: ResumeMatch, analyzed_at: datetime) -> JobAnalysis:
    return JobAnalysis(
        job_id=job_id,
        resume_name=match.resume_name,
        score=match.pre_score,
        pre_score=match.pre_score,
        summary=SIMPLIFIED_ANALYSIS_SUMMARY,
        requirements=match.job_terms,
        keywords=match.job_terms,
        gap=match.missing_terms,
        analyzer=Analyzer.KEYWORDS,
        model=None,
        analyzed_at=analyzed_at,
    )
