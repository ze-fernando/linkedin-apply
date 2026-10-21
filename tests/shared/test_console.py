import json
import logging
from datetime import date, datetime
from pathlib import Path

import pytest
from rich.console import Console

from autoapply.shared.console import configure_logging, mask_sensitive_data


def read_log_entries(log_dir: Path) -> list[dict]:
    log_file = log_dir / f"{date.today().isoformat()}.log"
    return [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]


def test_mask_sensitive_data_hides_email_address() -> None:
    masked = mask_sensitive_data("contato: maria.teste@example.com ok")

    assert masked == "contato: [email] ok"


@pytest.mark.parametrize(
    "phone",
    [
        "+55 11 91234-5678",
        "(11) 91234-5678",
        "11912345678",
        "+5511912345678",
        "91234-5678",
    ],
)
def test_mask_sensitive_data_hides_brazilian_phone_formats(phone: str) -> None:
    masked = mask_sensitive_data(f"tel {phone} fim")

    assert masked == "tel [telefone] fim"


def test_mask_sensitive_data_keeps_regular_numbers() -> None:
    text = "score 82 de 100, limite 15/dia em 2026-10-21"

    assert mask_sensitive_data(text) == text


def test_log_file_records_json_line_with_default_event(tmp_path: Path) -> None:
    configure_logging(tmp_path, verbose=False, console=Console(record=True))

    logging.getLogger("autoapply.session").info("Sessão válida")

    [entry] = read_log_entries(tmp_path)
    assert entry["level"] == "INFO"
    assert entry["event"] == "autoapply.session"
    assert entry["msg"] == "Sessão válida"
    assert isinstance(datetime.fromisoformat(entry["ts"]), datetime)


def test_log_file_records_debug_even_when_not_verbose(tmp_path: Path) -> None:
    configure_logging(tmp_path, verbose=False, console=Console(record=True))

    logging.getLogger("autoapply.session").debug("Verificando cookies")

    [entry] = read_log_entries(tmp_path)
    assert entry["level"] == "DEBUG"
    assert entry["msg"] == "Verificando cookies"


def test_log_file_uses_event_and_extra_fields_from_caller(tmp_path: Path) -> None:
    configure_logging(tmp_path, verbose=False, console=Console(record=True))

    logging.getLogger("autoapply.apply").info(
        "Candidatura enviada",
        extra={"event": "application.sent", "job_id": "4012345678", "score": 82},
    )

    [entry] = read_log_entries(tmp_path)
    assert entry["event"] == "application.sent"
    assert entry["job_id"] == "4012345678"
    assert entry["score"] == 82


def test_log_file_masks_sensitive_data_in_message_and_extras(tmp_path: Path) -> None:
    configure_logging(tmp_path, verbose=False, console=Console(record=True))

    logging.getLogger("autoapply.apply").info(
        "Preenchendo e-mail maria.teste@example.com",
        extra={"answer": "(11) 91234-5678"},
    )

    raw_log = (tmp_path / f"{date.today().isoformat()}.log").read_text(encoding="utf-8")
    assert "maria.teste@example.com" not in raw_log
    assert "91234-5678" not in raw_log
    [entry] = read_log_entries(tmp_path)
    assert entry["msg"] == "Preenchendo e-mail [email]"
    assert entry["answer"] == "[telefone]"


@pytest.mark.parametrize("job_id", ["4012345678", "3998877665"])
def test_mask_sensitive_data_keeps_linkedin_job_ids(job_id: str) -> None:
    text = f"vaga {job_id} aplicada"

    assert mask_sensitive_data(text) == text


def test_terminal_shows_info_and_hides_debug_when_not_verbose(tmp_path: Path) -> None:
    terminal = Console(record=True, width=120)
    configure_logging(tmp_path, verbose=False, console=terminal)

    logging.getLogger("autoapply.session").info("Sessão válida")
    logging.getLogger("autoapply.session").debug("Verificando cookies")

    output = terminal.export_text()
    assert "Sessão válida" in output
    assert "Verificando cookies" not in output


def test_terminal_shows_debug_when_verbose(tmp_path: Path) -> None:
    terminal = Console(record=True, width=120)
    configure_logging(tmp_path, verbose=True, console=terminal)

    logging.getLogger("autoapply.session").debug("Verificando cookies")

    assert "Verificando cookies" in terminal.export_text()


def test_terminal_masks_sensitive_data(tmp_path: Path) -> None:
    terminal = Console(record=True, width=120)
    configure_logging(tmp_path, verbose=False, console=terminal)

    logging.getLogger("autoapply.apply").info("Telefone (11) 91234-5678 e e-mail maria.teste@example.com")

    output = terminal.export_text()
    assert "91234-5678" not in output
    assert "maria.teste@example.com" not in output
    assert "[telefone]" in output
    assert "[email]" in output


def test_log_file_writes_non_json_extras_as_text(tmp_path: Path) -> None:
    configure_logging(tmp_path, verbose=False, console=Console(record=True))

    logging.getLogger("autoapply.resumes").info("Currículo lido", extra={"path": Path("cv_base/dotnet.docx")})

    [entry] = read_log_entries(tmp_path)
    assert entry["path"] == "cv_base/dotnet.docx"
