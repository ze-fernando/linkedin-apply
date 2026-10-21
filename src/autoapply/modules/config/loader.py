from pathlib import Path

import yaml
from pydantic import ValidationError
from yaml.nodes import MappingNode, Node, SequenceNode

from autoapply.modules.config.answers import normalize_question
from autoapply.modules.config.models import (
    Config,
    ConfigError,
    ConfigIssue,
    MarkdownSection,
    ParsedAnswers,
)

ANSWERS_HEADING = "respostas padrao"
GENERIC_ANSWER_HEADING = "resposta generica"
BODY_FIELD_HEADINGS = {"respostas": ANSWERS_HEADING, "resposta_generica": GENERIC_ANSWER_HEADING}
FRONTMATTER_FIRST_LINE = 2
MISSING_FRONTMATTER_ISSUE = ConfigIssue(
    line=1, field="frontmatter", problem="o arquivo deve começar com um bloco YAML entre linhas ---"
)
NOT_A_MAPPING_ISSUE = ConfigIssue(
    line=FRONTMATTER_FIRST_LINE, field="frontmatter", problem="o bloco YAML deve ter os campos do config (chave: valor)"
)


def parse_config_data(data: dict[str, object], base_dir: Path) -> Config:
    return Config.model_validate(data, context={"base_dir": base_dir})


def split_frontmatter(text: str) -> tuple[str, list[tuple[int, str]]]:
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ConfigError([MISSING_FRONTMATTER_ISSUE])
    closing_index = lines.index("---", 1)
    body_lines = list(enumerate(lines[closing_index + 1 :], start=closing_index + 2))
    return "\n".join(lines[1:closing_index]), body_lines


def extract_sections(body_lines: list[tuple[int, str]]) -> dict[str, MarkdownSection]:
    sections = {}
    current_heading = None
    for line_number, line in body_lines:
        if line.startswith("# "):
            current_heading = normalize_question(line[2:])
            sections[current_heading] = MarkdownSection(heading_line=line_number, lines=[])
        elif current_heading is not None:
            sections[current_heading].lines.append((line_number, line))
    return sections


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return set("".join(cells)) <= set("-: ")


def parse_answers_table(section: MarkdownSection | None) -> ParsedAnswers:
    table_rows = [
        (line_number, split_table_row(line))
        for line_number, line in (section.lines if section else [])
        if line.strip().startswith("|")
    ]
    answers = {}
    issues = []
    for line_number, cells in table_rows[1:]:
        if is_separator_row(cells):
            continue
        question = normalize_question(cells[0])
        if question in answers:
            issues.append(
                ConfigIssue(
                    line=line_number,
                    field="respostas",
                    problem=f"pergunta repetida (igual após normalizar): {question}",
                )
            )
        answers[question] = cells[1]
    return ParsedAnswers(answers=answers, issues=issues)


def parse_blockquote(section: MarkdownSection | None) -> str:
    quoted = [
        line.strip()[1:].strip() for _, line in (section.lines if section else []) if line.strip().startswith(">")
    ]
    return " ".join(quoted)


def find_child_node(node: Node, part: str | int) -> tuple[Node, Node] | None:
    if isinstance(node, MappingNode):
        return next(((key, value) for key, value in node.value if key.value == str(part)), None)
    if isinstance(node, SequenceNode) and isinstance(part, int) and part < len(node.value):
        child = node.value[part]
        return child, child
    return None


def find_field_line(root: Node | None, location: tuple[str | int, ...]) -> int | None:
    if root is None:
        return None
    current = root
    line = None
    for part in location:
        found = find_child_node(current, part)
        if found is None:
            break
        marker, current = found
        line = marker.start_mark.line + FRONTMATTER_FIRST_LINE
    return line


def locate_issue_line(
    location: tuple[str | int, ...], root: Node | None, body_field_lines: dict[str, int]
) -> int | None:
    if location and location[0] in body_field_lines:
        return body_field_lines[location[0]]
    return find_field_line(root, location)


def build_validation_issues(
    error: ValidationError, root: Node | None, body_field_lines: dict[str, int]
) -> list[ConfigIssue]:
    return [
        ConfigIssue(
            line=locate_issue_line(tuple(detail["loc"]), root, body_field_lines),
            field=".".join(str(part) for part in detail["loc"]),
            problem=detail["msg"],
        )
        for detail in error.errors()
    ]


def build_yaml_issue(error: yaml.MarkedYAMLError) -> ConfigIssue:
    line = error.problem_mark.line + FRONTMATTER_FIRST_LINE if error.problem_mark else None
    return ConfigIssue(line=line, field="yaml", problem=f"{error.problem}")


def parse_frontmatter_yaml(frontmatter: str) -> dict[str, object]:
    try:
        data = yaml.safe_load(frontmatter)
    except yaml.MarkedYAMLError as error:
        raise ConfigError([build_yaml_issue(error)]) from error
    if not isinstance(data, dict):
        raise ConfigError([NOT_A_MAPPING_ISSUE])
    return data


def load_config(config_path: Path) -> Config:
    frontmatter, body_lines = split_frontmatter(config_path.read_text(encoding="utf-8"))
    data = parse_frontmatter_yaml(frontmatter)
    sections = extract_sections(body_lines)
    parsed_answers = parse_answers_table(sections.get(ANSWERS_HEADING))
    data["respostas"] = parsed_answers.answers
    data["resposta_generica"] = parse_blockquote(sections.get(GENERIC_ANSWER_HEADING))
    try:
        config = parse_config_data(data, config_path.parent)
    except ValidationError as error:
        body_field_lines = {
            field: sections[heading].heading_line
            for field, heading in BODY_FIELD_HEADINGS.items()
            if heading in sections
        }
        validation_issues = build_validation_issues(error, yaml.compose(frontmatter), body_field_lines)
        raise ConfigError(parsed_answers.issues + validation_issues) from error
    if parsed_answers.issues:
        raise ConfigError(parsed_answers.issues)
    return config
