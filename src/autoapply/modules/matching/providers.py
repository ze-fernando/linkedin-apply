import json
import logging
import shutil
import subprocess

from autoapply.modules.config.models import Llm, ProvedorLlm
from autoapply.modules.matching.models import LlmAnalysis, ProviderAnalysis, ProviderFailure, ProviderRun
from autoapply.modules.matching.prompt import build_analysis_schema

ANALYSIS_FIELDS = {"curriculo", "score", "resumo", "requisitos", "palavras_chave", "gap"}
ATTEMPTS_PER_PROVIDER = 2
MAX_CONSECUTIVE_FAILURES = 3

logger = logging.getLogger("autoapply.matching")


def find_provider_model(llm: Llm, provider: ProvedorLlm) -> str | None:
    return {"claude": llm.claude.modelo, "opencode": llm.opencode.modelo}[provider]


def find_available_providers(llm: Llm) -> list[ProvedorLlm]:
    return [
        provider
        for provider in llm.provedores
        if shutil.which(provider) is not None and find_provider_model(llm, provider) is not None
    ]


def build_claude_command(model: str, resume_names: list[str]) -> list[str]:
    return [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--model",
        model,
        "--tools",
        "",
        "--json-schema",
        json.dumps(build_analysis_schema(resume_names), ensure_ascii=False),
    ]


def parse_analysis(data: object, resume_names: list[str]) -> LlmAnalysis:
    if not isinstance(data, dict) or not ANALYSIS_FIELDS <= data.keys():
        raise ProviderFailure(f"análise incompleta: {data!r}"[:300])
    if data["curriculo"] not in resume_names:
        raise ProviderFailure(f"currículo desconhecido: {data['curriculo']!r}")
    return LlmAnalysis(
        resume_name=data["curriculo"],
        score=data["score"],
        summary=data["resumo"],
        requirements=data["requisitos"],
        keywords=data["palavras_chave"],
        gap=data["gap"],
    )


def build_opencode_command(model: str, prompt: str, resume_names: list[str]) -> list[str]:
    schema = json.dumps(build_analysis_schema(resume_names), ensure_ascii=False)
    message = f"{prompt}\n\nResponda apenas com um objeto JSON válido que siga este JSON Schema:\n{schema}"
    return ["opencode", "run", "--standalone", "-m", model, message]


def read_claude_output(stdout: str) -> object:
    try:
        output = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise ProviderFailure(f"claude devolveu saída inválida: {stdout[:300]}") from error
    if output.get("is_error"):
        raise ProviderFailure(f"claude devolveu erro: {str(output.get('result'))[:300]}")
    return output.get("structured_output")


def read_opencode_output(stdout: str) -> object:
    decoder = json.JSONDecoder()
    for position, character in enumerate(stdout):
        if character == "{":
            try:
                data, _ = decoder.raw_decode(stdout, position)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
    raise ProviderFailure(f"opencode não devolveu JSON: {stdout[:300]}")


def run_provider(
    provider: ProvedorLlm, prompt: str, model: str, timeout_seconds: int, resume_names: list[str]
) -> LlmAnalysis:
    if provider == "claude":
        command, stdin = build_claude_command(model, resume_names), prompt
    else:
        command, stdin = build_opencode_command(model, prompt, resume_names), ""
    try:
        completed = subprocess.run(command, input=stdin, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        raise ProviderFailure(f"{provider} passou de {timeout_seconds} s") from error
    if completed.returncode != 0:
        raise ProviderFailure(f"{provider} saiu com código {completed.returncode}: {completed.stderr[:300]}")
    data = read_claude_output(completed.stdout) if provider == "claude" else read_opencode_output(completed.stdout)
    return parse_analysis(data, resume_names)


def is_provider_disabled(run: ProviderRun, provider: ProvedorLlm) -> bool:
    return run.consecutive_failures.get(provider, 0) >= MAX_CONSECUTIVE_FAILURES


def register_failure(run: ProviderRun, provider: ProvedorLlm, error: ProviderFailure) -> None:
    run.consecutive_failures[provider] = run.consecutive_failures.get(provider, 0) + 1
    logger.warning("falha no provedor %s: %s", provider, error)
    if is_provider_disabled(run, provider):
        logger.warning("provedor %s desligado após %d falhas seguidas", provider, MAX_CONSECUTIVE_FAILURES)


def analyze_with_fallback(prompt: str, resume_names: list[str], llm: Llm, run: ProviderRun) -> ProviderAnalysis | None:
    for provider in run.providers:
        model = find_provider_model(llm, provider)
        for _ in range(ATTEMPTS_PER_PROVIDER):
            if is_provider_disabled(run, provider):
                break
            try:
                analysis = run_provider(provider, prompt, model, llm.timeout_segundos, resume_names)
            except ProviderFailure as error:
                register_failure(run, provider, error)
                continue
            run.consecutive_failures[provider] = 0
            return ProviderAnalysis(provider=provider, model=model, analysis=analysis)
    return None
