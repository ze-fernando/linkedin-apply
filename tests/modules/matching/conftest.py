from collections.abc import Callable
from pathlib import Path

import pytest

FAKE_CLI_SCRIPT = """#!/bin/sh
printf '%s\\n' "$@" > "{directory}/{name}.args"
echo call >> "{directory}/{name}.calls"
cat > "{directory}/{name}.stdin"
sleep {delay}
cat "{directory}/{name}.stdout"
exit {exit_code}
"""


@pytest.fixture
def fake_cli_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "fake-bin"
    directory.mkdir()
    monkeypatch.setenv("PATH", f"{directory}:/usr/bin:/bin")
    return directory


@pytest.fixture
def install_fake_cli(fake_cli_dir: Path) -> Callable[..., None]:
    def install(name: str, stdout: str, exit_code: int = 0, delay: float = 0) -> None:
        (fake_cli_dir / f"{name}.stdout").write_text(stdout, encoding="utf-8")
        script = fake_cli_dir / name
        script.write_text(
            FAKE_CLI_SCRIPT.format(directory=fake_cli_dir, name=name, delay=delay, exit_code=exit_code),
            encoding="utf-8",
        )
        script.chmod(0o755)

    return install
