import shutil

from autoapply.modules.config.models import Llm, ProvedorLlm


def find_provider_model(llm: Llm, provider: ProvedorLlm) -> str | None:
    return {"claude": llm.claude.modelo, "opencode": llm.opencode.modelo}[provider]


def find_available_providers(llm: Llm) -> list[ProvedorLlm]:
    return [
        provider
        for provider in llm.provedores
        if shutil.which(provider) is not None and find_provider_model(llm, provider) is not None
    ]
