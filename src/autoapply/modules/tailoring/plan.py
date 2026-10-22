import dataclasses

from autoapply.modules.tailoring.models import ResumeDocument, TailoringPlan


def is_permutation(order: list[int], size: int) -> bool:
    return sorted(order) == list(range(size))


def find_plan_problem(document: ResumeDocument, plan: TailoringPlan) -> str | None:
    experience_count = len(document.experiences)
    if len(plan.bullet_orders) != experience_count:
        return f"ordem dos bullets tem {len(plan.bullet_orders)} experiências, o currículo tem {experience_count}"
    for index, (order, experience) in enumerate(zip(plan.bullet_orders, document.experiences, strict=True)):
        if not is_permutation(order, len(experience.bullets)):
            return f"ordem dos bullets da experiência {index} não é permutação: {order}"
    if not is_permutation(plan.skill_line_order, len(document.skill_lines)):
        return f"ordem das competências não é permutação: {plan.skill_line_order}"
    if len(plan.skill_item_orders) != len(document.skill_lines):
        return f"ordem dos itens tem {len(plan.skill_item_orders)} linhas, o currículo tem {len(document.skill_lines)}"
    for index, (order, skill_line) in enumerate(zip(plan.skill_item_orders, document.skill_lines, strict=True)):
        if not is_permutation(order, len(skill_line.items)):
            return f"ordem dos itens da linha {index} não é permutação: {order}"
    return None


def apply_tailoring_plan(document: ResumeDocument, plan: TailoringPlan) -> ResumeDocument | str:
    problem = find_plan_problem(document, plan)
    if problem is not None:
        return problem
    experiences = [
        dataclasses.replace(experience, bullets=[experience.bullets[position] for position in order])
        for order, experience in zip(plan.bullet_orders, document.experiences, strict=True)
    ]
    skill_lines = [
        dataclasses.replace(skill_line, items=[skill_line.items[position] for position in order])
        for order, skill_line in zip(plan.skill_item_orders, document.skill_lines, strict=True)
    ]
    return dataclasses.replace(
        document,
        summary=plan.summary,
        experiences=experiences,
        skill_lines=[skill_lines[position] for position in plan.skill_line_order],
    )
