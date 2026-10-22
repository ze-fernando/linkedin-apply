from autoapply.modules.jobs.models import Job
from autoapply.modules.matching.models import JobAnalysis, ProviderFailure
from autoapply.modules.tailoring.models import ExperienceEntry, ResumeDocument, SkillLine, TailoringPlan
from autoapply.shared.console import mask_sensitive_data

PLAN_FIELDS = {"resumo", "ordem_bullets", "ordem_competencias", "ordem_itens"}
INSTRUCTIONS = """Você ajusta um currículo para uma vaga sem inventar nada.
Regras:
- Responda em português.
- resumo: reescreva o Resumo Profissional destacando o que a vaga pede, usando só fatos que já estão no currículo.
- Não cite tecnologia, empresa, cargo, certificação, número ou tempo de experiência que não esteja no currículo.
- O resumo novo pode ter no máximo o dobro do tamanho do atual.
- ordem_bullets: para cada experiência, na ordem em que aparecem, os números dos bullets na nova ordem, \
mais relevantes para a vaga primeiro. Use todos os números, sem repetir: \
cada ordem tem exatamente a quantidade de bullets indicada na experiência.
- ordem_competencias: os números das linhas de competências na nova ordem, usando todos, sem repetir.
- ordem_itens: para cada linha de competências, na ordem original das linhas, os números dos itens na nova ordem, \
usando todos, sem repetir."""


def build_plan_schema() -> dict[str, object]:
    order = {"type": "array", "items": {"type": "integer", "minimum": 0}}
    return {
        "type": "object",
        "properties": {
            "resumo": {"type": "string"},
            "ordem_bullets": {"type": "array", "items": order},
            "ordem_competencias": order,
            "ordem_itens": {"type": "array", "items": order},
        },
        "required": sorted(PLAN_FIELDS),
        "additionalProperties": False,
    }


def is_order(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(index, int) and not isinstance(index, bool) for index in value)


def is_order_list(value: object) -> bool:
    return isinstance(value, list) and all(is_order(order) for order in value)


def parse_tailoring_plan(data: object) -> TailoringPlan:
    if (
        not isinstance(data, dict)
        or not PLAN_FIELDS <= data.keys()
        or not isinstance(data["resumo"], str)
        or not is_order_list(data["ordem_bullets"])
        or not is_order(data["ordem_competencias"])
        or not is_order_list(data["ordem_itens"])
    ):
        raise ProviderFailure(f"plano de ajuste inválido: {data!r}"[:300])
    return TailoringPlan(
        summary=data["resumo"],
        bullet_orders=data["ordem_bullets"],
        skill_line_order=data["ordem_competencias"],
        skill_item_orders=data["ordem_itens"],
    )


def format_experience(index: int, experience: ExperienceEntry) -> str:
    bullets = [f"[{position}] {bullet.lead}{bullet.text}" for position, bullet in enumerate(experience.bullets)]
    header = f"Experiência {index} ({len(experience.bullets)} bullets): {experience.title} ({experience.period})"
    return "\n".join([header, *bullets])


def format_skill_line(index: int, skill_line: SkillLine) -> str:
    items = " | ".join(f"[{position}] {item}" for position, item in enumerate(skill_line.items))
    return f"Linha {index}: {skill_line.label}: {items}"


def build_tailoring_prompt(document: ResumeDocument, job: Job, analysis: JobAnalysis) -> str:
    sections = [
        INSTRUCTIONS,
        f"## Vaga\nTítulo: {job.title}\nEmpresa: {job.company}\n\n{job.description or ''}\n\n"
        f"Requisitos: {', '.join(analysis.requirements)}\nGap: {', '.join(analysis.gap)}",
        f"## Resumo Profissional\n{document.summary}",
        "## Experiências\n"
        + "\n\n".join(format_experience(index, experience) for index, experience in enumerate(document.experiences)),
        "## Competências\n"
        + "\n".join(format_skill_line(index, skill_line) for index, skill_line in enumerate(document.skill_lines)),
    ]
    return mask_sensitive_data("\n\n".join(sections))
