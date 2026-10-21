from collections.abc import Callable
from pathlib import Path

import pytest
import yaml


DEFAULT_BODY = """
# Respostas padrão

| Pergunta | Resposta |
| --- | --- |
| Aceita contratação PJ? | Sim |
| Nível de inglês | Intermediário |

# Resposta genérica

> Tenho interesse
> na vaga.
"""


@pytest.fixture
def write_config(base_dir: Path) -> Callable[..., Path]:
    def write(data: dict[str, object], body: str = DEFAULT_BODY) -> Path:
        frontmatter = {key: value for key, value in data.items() if key not in {"respostas", "resposta_generica"}}
        config_path = base_dir / "config.md"
        yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
        config_path.write_text(f"---\n{yaml_text}---\n{body}", encoding="utf-8")
        return config_path

    return write
