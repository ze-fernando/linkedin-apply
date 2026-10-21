from autoapply.modules.config.models import Config
from autoapply.modules.jobs.models import Job
from autoapply.modules.resumes.models import Resume
from autoapply.shared.console import mask_sensitive_data

INSTRUCTIONS = """Você avalia a aderência de uma vaga aos currículos de um candidato.
Regras:
- Responda em português.
- Use só o que está escrito nos currículos e no perfil; nunca invente experiência, tecnologia ou tempo de atuação.
- Escolha o currículo mais aderente pelo nome exato.
- score: de 0 a 100, quanto o currículo escolhido atende à vaga, considerando o nível pretendido.
- resumo: 2 ou 3 frases justificando o score.
- requisitos: requisitos técnicos e de experiência que a vaga pede.
- palavras_chave: termos da vaga que valem destacar no currículo.
- gap: o que a vaga pede e o currículo escolhido não mostra."""


def format_resume(resume: Resume) -> str:
    return f"### Currículo: {resume.name}\n{mask_sensitive_data(resume.text)}"


def format_profile(config: Config) -> str:
    experience = "\n".join(f"- {technology}: {years}" for technology, years in config.experiencia_anos.items())
    return f"Níveis pretendidos: {', '.join(config.busca.niveis)}\nAnos de experiência:\n{experience}"


def build_analysis_prompt(job: Job, resumes: list[Resume], config: Config) -> str:
    sections = [
        INSTRUCTIONS,
        f"## Vaga\nTítulo: {job.title}\nEmpresa: {job.company}\nLocal: {job.location}\n\n{job.description or ''}",
        f"## Perfil\n{format_profile(config)}",
        "## Currículos\n" + "\n\n".join(format_resume(resume) for resume in resumes),
    ]
    return "\n\n".join(sections)


def build_analysis_schema(resume_names: list[str]) -> dict[str, object]:
    text_list = {"type": "array", "items": {"type": "string"}}
    return {
        "type": "object",
        "properties": {
            "curriculo": {"type": "string", "enum": resume_names},
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "resumo": {"type": "string"},
            "requisitos": text_list,
            "palavras_chave": text_list,
            "gap": text_list,
        },
        "required": ["curriculo", "score", "resumo", "requisitos", "palavras_chave", "gap"],
        "additionalProperties": False,
    }
