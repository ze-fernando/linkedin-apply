import json
import logging
import re
from datetime import date, datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?55\s?)?(?:\(\d{2}\)\s?|\d{2}\s)?9?\d{4}-\d{4}(?!\d)"
    r"|(?<!\d)(?:\+?55)?\d{2}9\d{8}(?!\d)"
)
APP_LOGGER_NAME = "autoapply"
STANDARD_RECORD_FIELDS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "json_line", "event"}

console = Console()


def mask_sensitive_data(text: str) -> str:
    without_emails = EMAIL_PATTERN.sub("[email]", text)
    return PHONE_PATTERN.sub("[telefone]", without_emails)


def mask_if_text(value: object) -> object:
    return mask_sensitive_data(value) if isinstance(value, str) else value


def extract_extra_fields(record: logging.LogRecord) -> dict[str, object]:
    return {
        key: mask_if_text(value)
        for key, value in vars(record).items()
        if key not in STANDARD_RECORD_FIELDS
    }


def attach_json_line(record: logging.LogRecord) -> bool:
    record.json_line = json.dumps(
        {
            "ts": datetime.fromtimestamp(record.created).astimezone().isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", record.name),
            "msg": mask_sensitive_data(record.getMessage()),
            **extract_extra_fields(record),
        },
        ensure_ascii=False,
        default=str,
    )
    return True


def build_file_handler(log_dir: Path) -> logging.Handler:
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / f"{date.today().isoformat()}.log", encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.addFilter(attach_json_line)
    handler.setFormatter(logging.Formatter("%(json_line)s"))
    return handler


def mask_record_message(record: logging.LogRecord) -> bool:
    record.msg = mask_sensitive_data(record.getMessage())
    record.args = None
    return True


def build_terminal_handler(verbose: bool, console: Console) -> logging.Handler:
    handler = RichHandler(console=console, show_path=False, markup=False, rich_tracebacks=True)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler.addFilter(mask_record_message)
    return handler


def configure_logging(log_dir: Path, verbose: bool, console: Console) -> None:
    app_logger = logging.getLogger(APP_LOGGER_NAME)
    for existing_handler in list(app_logger.handlers):
        app_logger.removeHandler(existing_handler)
        existing_handler.close()
    app_logger.setLevel(logging.DEBUG)
    app_logger.propagate = False
    app_logger.addHandler(build_terminal_handler(verbose, console))
    app_logger.addHandler(build_file_handler(log_dir))
