import json
from collections.abc import Callable
from pathlib import Path

import pytest

from autoapply.modules.config.models import Llm, ProvedorLlm
from autoapply.modules.matching.models import (
    LlmAnalysis,
    ProviderAnalysis,
    ProviderAnswer,
    ProviderFailure,
    ProviderRun,
)
from autoapply.modules.matching.prompt import build_analysis_schema
from autoapply.modules.matching.providers import (
    analyze_with_fallback,
    ask_with_fallback,
    parse_analysis,
    run_provider,
)
from autoapply.modules.tailoring.models import TailoringPlan
from autoapply.modules.tailoring.prompt import build_plan_schema, parse_tailoring_plan

RESUME_NAMES = ["Back-end", "Dados"]
ANALYSIS = {
    "curriculo": "Back-end",
    "score": 82,
    "resumo": "Boa aderência em C#.",
    "requisitos": ["C#", "Azure"],
    "palavras_chave": ["C#"],
    "gap": ["Azure"],
}
EXPECTED_ANALYSIS = LlmAnalysis(
    resume_name="Back-end",
    score=82,
    summary="Boa aderência em C#.",
    requirements=["C#", "Azure"],
    keywords=["C#"],
    gap=["Azure"],
)


def run_analysis(provider: ProvedorLlm, prompt: str, model: str, timeout_seconds: int) -> LlmAnalysis:
    schema = build_analysis_schema(RESUME_NAMES)
    return run_provider(
        provider, prompt, model, timeout_seconds, schema, lambda data: parse_analysis(data, RESUME_NAMES)
    )


def claude_output(structured_output: object, is_error: bool = False) -> str:
    return json.dumps({"type": "result", "is_error": is_error, "structured_output": structured_output})


def test_run_provider_claude_sends_prompt_and_schema_and_reads_structured_output(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    install_fake_cli("claude", claude_output(ANALYSIS))

    analysis = run_analysis("claude", "PROMPT DA VAGA", "sonnet", 10)

    assert analysis == EXPECTED_ANALYSIS
    arguments = (fake_cli_dir / "claude.args").read_text(encoding="utf-8").splitlines()
    assert arguments[:4] == ["-p", "--output-format", "json", "--no-session-persistence"]
    assert arguments[arguments.index("--model") + 1] == "sonnet"
    assert arguments[arguments.index("--tools") + 1] == ""
    schema = json.loads(arguments[arguments.index("--json-schema") + 1])
    assert set(schema["required"]) == set(ANALYSIS)
    assert (fake_cli_dir / "claude.stdin").read_text(encoding="utf-8") == "PROMPT DA VAGA"


@pytest.mark.parametrize(
    ("stdout", "exit_code", "delay"),
    [
        (claude_output(ANALYSIS, is_error=True), 0, 0),
        ("isto não é json", 0, 0),
        (claude_output(ANALYSIS), 1, 0),
        (claude_output(ANALYSIS), 0, 3),
        (claude_output({**ANALYSIS, "curriculo": "Inventado"}), 0, 0),
        (claude_output({key: value for key, value in ANALYSIS.items() if key != "gap"}), 0, 0),
    ],
    ids=["is_error", "nao_json", "codigo_saida", "timeout", "curriculo_inexistente", "campo_faltando"],
)
def test_run_provider_claude_turns_any_failure_into_provider_failure(
    install_fake_cli: Callable[..., None], stdout: str, exit_code: int, delay: float
) -> None:
    install_fake_cli("claude", stdout, exit_code=exit_code, delay=delay)

    with pytest.raises(ProviderFailure):
        run_analysis("claude", "PROMPT", "sonnet", 1)


def test_run_provider_opencode_extracts_json_from_text_answer(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    answer = f"> build · deepseek-v4.1-flash-free\n\nSegue a análise:\n```json\n{json.dumps(ANALYSIS, ensure_ascii=False)}\n```\n"
    install_fake_cli("opencode", answer)

    analysis = run_analysis("opencode", "PROMPT DA VAGA", "opencode/deepseek-v4.1-flash-free", 10)

    assert analysis == EXPECTED_ANALYSIS
    arguments = (fake_cli_dir / "opencode.args").read_text(encoding="utf-8").split("\n", 4)
    assert arguments[:4] == ["run", "--standalone", "-m", "opencode/deepseek-v4.1-flash-free"]
    assert arguments[4].startswith("PROMPT DA VAGA")
    assert "JSON" in arguments[4]


def test_run_provider_opencode_without_json_in_answer_fails(install_fake_cli: Callable[..., None]) -> None:
    install_fake_cli("opencode", "> build · modelo\n\nNão consegui analisar.\n")

    with pytest.raises(ProviderFailure):
        run_analysis("opencode", "PROMPT", "opencode/deepseek-v4.1-flash-free", 10)


def build_llm() -> Llm:
    return Llm(
        provedores=["claude", "opencode"],
        claude={"modelo": "sonnet"},
        opencode={"modelo": "opencode/deepseek-v4.1-flash-free"},
        timeout_segundos=10,
    )


def count_calls(fake_cli_dir: Path, name: str) -> int:
    calls_file = fake_cli_dir / f"{name}.calls"
    return len(calls_file.read_text(encoding="utf-8").splitlines()) if calls_file.exists() else 0


def test_analyze_with_fallback_tries_each_provider_once_then_uses_the_next(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    install_fake_cli("claude", "falhou", exit_code=1)
    install_fake_cli("opencode", json.dumps(ANALYSIS))
    run = ProviderRun(providers=["claude", "opencode"])

    result = analyze_with_fallback("PROMPT", RESUME_NAMES, build_llm(), run)

    assert result == ProviderAnalysis(
        provider="opencode", model="opencode/deepseek-v4.1-flash-free", analysis=EXPECTED_ANALYSIS
    )
    assert count_calls(fake_cli_dir, "claude") == 1
    assert count_calls(fake_cli_dir, "opencode") == 1


def test_analyze_with_fallback_returns_none_when_all_providers_fail(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    install_fake_cli("claude", "falhou", exit_code=1)
    install_fake_cli("opencode", "sem json")
    run = ProviderRun(providers=["claude", "opencode"])

    assert analyze_with_fallback("PROMPT", RESUME_NAMES, build_llm(), run) is None
    assert count_calls(fake_cli_dir, "claude") == 1
    assert count_calls(fake_cli_dir, "opencode") == 1


def test_analyze_with_fallback_disables_provider_after_three_consecutive_failures(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    install_fake_cli("claude", "falhou", exit_code=1)
    install_fake_cli("opencode", json.dumps(ANALYSIS))
    run = ProviderRun(providers=["claude", "opencode"])

    for _ in range(3):
        assert analyze_with_fallback("PROMPT", RESUME_NAMES, build_llm(), run) is not None

    assert count_calls(fake_cli_dir, "claude") == 3
    assert count_calls(fake_cli_dir, "opencode") == 3


PLAN = {
    "resumo": "Desenvolvedora back-end com foco em Python.",
    "ordem_bullets": [[1, 0], [0]],
    "ordem_competencias": [1, 0],
    "ordem_itens": [[2, 0, 1], [0, 1, 2]],
}


def test_ask_with_fallback_sends_the_given_schema_and_returns_the_parsed_answer(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    install_fake_cli("claude", "falhou", exit_code=1)
    install_fake_cli("opencode", f"Segue o plano:\n{json.dumps(PLAN, ensure_ascii=False)}\n")
    run = ProviderRun(providers=["claude", "opencode"])

    result = ask_with_fallback("PROMPT DO AJUSTE", build_plan_schema(), parse_tailoring_plan, build_llm(), run)

    assert result == ProviderAnswer(
        provider="opencode",
        model="opencode/deepseek-v4.1-flash-free",
        value=TailoringPlan(
            summary="Desenvolvedora back-end com foco em Python.",
            bullet_orders=[[1, 0], [0]],
            skill_line_order=[1, 0],
            skill_item_orders=[[2, 0, 1], [0, 1, 2]],
        ),
    )
    claude_arguments = (fake_cli_dir / "claude.args").read_text(encoding="utf-8").splitlines()
    schema = json.loads(claude_arguments[claude_arguments.index("--json-schema") + 1])
    assert set(schema["required"]) == set(PLAN)
    assert "ordem_competencias" in (fake_cli_dir / "opencode.args").read_text(encoding="utf-8")


def test_ask_with_fallback_rejects_an_answer_that_does_not_follow_the_plan(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    install_fake_cli("claude", claude_output({key: value for key, value in PLAN.items() if key != "ordem_itens"}))
    install_fake_cli("opencode", json.dumps({**PLAN, "ordem_bullets": "primeiro o 2"}))
    run = ProviderRun(providers=["claude", "opencode"])

    assert ask_with_fallback("PROMPT", build_plan_schema(), parse_tailoring_plan, build_llm(), run) is None
    assert count_calls(fake_cli_dir, "claude") == 1
    assert count_calls(fake_cli_dir, "opencode") == 1
