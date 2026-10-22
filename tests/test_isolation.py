from pathlib import Path

from autoapply.shared.paths import BROWSER_PROFILE_DIR, CONFIG_FILE, DATABASE_FILE, VAGAS_DIR

PROJECT_DIR = Path(__file__).parent.parent


def test_tests_never_see_the_real_project_files() -> None:
    assert Path.cwd().resolve() != PROJECT_DIR.resolve()
    for path in [CONFIG_FILE, DATABASE_FILE, BROWSER_PROFILE_DIR, VAGAS_DIR]:
        assert not path.exists()
