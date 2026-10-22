from datetime import datetime
from pathlib import Path

from autoapply.modules.applying.models import ApplyMode, AttemptOutcome
from autoapply.modules.reporting.models import ReportEntry
from autoapply.modules.reporting.report import write_report_csv

ENTRIES = [
    ReportEntry(
        job_id="e",
        attempted_at=datetime(2026, 10, 21, 12, 0),
        mode=ApplyMode.NORMAL,
        outcome=AttemptOutcome.APPLIED,
        company="Empresa Teste",
        title="Desenvolvedora Python",
        score=85,
        resume_file="curriculos-enviados/2026-10-21-empresa-teste-dev.pdf",
        tailored=True,
        url="https://www.linkedin.com/jobs/view/e/",
    ),
    ReportEntry(
        job_id="b",
        attempted_at=datetime(2026, 10, 18, 9, 5),
        mode=ApplyMode.SEARCH,
        outcome=AttemptOutcome.FAILED,
        company="Empresa; Filial",
        title="Dev .NET",
        score=None,
        resume_file="vagas/2026-10-18-empresa-filial-dev-net/cv.pdf",
        tailored=False,
        url="https://www.linkedin.com/jobs/view/b/",
    ),
]


def test_write_report_csv_uses_semicolons_and_utf8_bom_for_spreadsheets(tmp_path: Path) -> None:
    path = tmp_path / "saida" / "relatorio.csv"

    write_report_csv(ENTRIES, path)

    content = path.read_bytes()
    assert content.startswith(b"\xef\xbb\xbf")
    assert content.decode("utf-8-sig").splitlines() == [
        "Data;Modo;Resultado;Empresa;Cargo;Score;Currículo;Arquivo do currículo;Link",
        "2026-10-21 12:00;normal;aplicada;Empresa Teste;Desenvolvedora Python;85;ajustado;"
        "curriculos-enviados/2026-10-21-empresa-teste-dev.pdf;https://www.linkedin.com/jobs/view/e/",
        '2026-10-18 09:05;busca;falhou;"Empresa; Filial";Dev .NET;;base;'
        "vagas/2026-10-18-empresa-filial-dev-net/cv.pdf;https://www.linkedin.com/jobs/view/b/",
    ]
