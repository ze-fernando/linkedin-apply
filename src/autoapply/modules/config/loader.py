from pathlib import Path

from autoapply.modules.config.models import Config


def parse_config_data(data: dict[str, object], base_dir: Path) -> Config:
    return Config.model_validate(data, context={"base_dir": base_dir})
