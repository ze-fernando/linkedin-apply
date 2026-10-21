import json
from collections.abc import Callable
from pathlib import Path

import pytest

from autoapply.modules.config.models import Llm
from autoapply.modules.matching.models import LlmAnalysis, ProviderAnalysis, ProviderFailure, ProviderRun
from autoapply.modules.matching.providers import analyze_with_fallback, run_provider

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


def claude_output(structured_output: object, is_error: bool = False) -> str:
    return json.dumps({"type": "result", "is_error": is_error, "structured_output": structured_output})


def test_run_provider_claude_sends_prompt_and_schema_and_reads_structured_output(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    install_fake_cli("claude", claude_output(ANALYSIS))

    analysis = run_provider("claude", "PROMPT DA VAGA", "sonnet", 10, RESUME_NAMES)

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
        run_provider("claude", "PROMPT", "sonnet", 1, RESUME_NAMES)


def test_run_provider_opencode_extracts_json_from_text_answer(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    answer = f"> build · deepseek-v4.1-flash-free\n\nSegue a análise:\n```json\n{json.dumps(ANALYSIS, ensure_ascii=False)}\n```\n"
    install_fake_cli("opencode", answer)

    analysis = run_provider("opencode", "PROMPT DA VAGA", "opencode/deepseek-v4.1-flash-free", 10, RESUME_NAMES)

    assert analysis == EXPECTED_ANALYSIS
    arguments = (fake_cli_dir / "opencode.args").read_text(encoding="utf-8").split("\n", 4)
    assert arguments[:4] == ["run", "--standalone", "-m", "opencode/deepseek-v4.1-flash-free"]
    assert arguments[4].startswith("PROMPT DA VAGA")
    assert "JSON" in arguments[4]


def test_run_provider_opencode_without_json_in_answer_fails(install_fake_cli: Callable[..., None]) -> None:
    install_fake_cli("opencode", "> build · modelo\n\nNão consegui analisar.\n")

    with pytest.raises(ProviderFailure):
        run_provider("opencode", "PROMPT", "opencode/deepseek-v4.1-flash-free", 10, RESUME_NAMES)


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


def test_analyze_with_fallback_retries_once_then_uses_next_provider(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    install_fake_cli("claude", "falhou", exit_code=1)
    install_fake_cli("opencode", json.dumps(ANALYSIS))
    run = ProviderRun(providers=["claude", "opencode"])

    result = analyze_with_fallback("PROMPT", RESUME_NAMES, build_llm(), run)

    assert result == ProviderAnalysis(
        provider="opencode", model="opencode/deepseek-v4.1-flash-free", analysis=EXPECTED_ANALYSIS
    )
    assert count_calls(fake_cli_dir, "claude") == 2
    assert count_calls(fake_cli_dir, "opencode") == 1


def test_analyze_with_fallback_returns_none_when_all_providers_fail(
    install_fake_cli: Callable[..., None], fake_cli_dir: Path
) -> None:
    install_fake_cli("claude", "falhou", exit_code=1)
    install_fake_cli("opencode", "sem json")
    run = ProviderRun(providers=["claude", "opencode"])

    assert analyze_with_fallback("PROMPT", RESUME_NAMES, build_llm(), run) is None
    assert count_calls(fake_cli_dir, "claude") == 2
    assert count_calls(fake_cli_dir, "opencode") == 2


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
