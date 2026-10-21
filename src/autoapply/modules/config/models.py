import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

SUPPORTED_RESUME_EXTENSIONS = {".docx", ".pdf"}
EMAIL_PATTERN = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")

NivelVaga = Literal["junior", "pleno"]
NivelIdioma = Literal["basico", "intermediario", "avancado", "fluente", "nativo"]
AnosExperiencia = Annotated[int, Field(ge=0)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Perfil(StrictModel):
    nome: str
    primeiro_nome: str
    sobrenome: str
    email: str
    telefone: str
    ddd: str
    celular: str
    cidade: str
    estado: str
    pais: str
    linkedin: str
    github: str | None = None
    portfolio: str | None = None
    autorizado_trabalhar_brasil: bool
    precisa_patrocinio_visto: bool

    @field_validator("email")
    @classmethod
    def ensure_valid_email(cls, email: str) -> str:
        if not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("e-mail inválido")
        return email

    @field_validator("telefone")
    @classmethod
    def ensure_brazilian_prefix(cls, telefone: str) -> str:
        if not telefone.startswith("+55"):
            raise ValueError("deve começar com +55")
        return telefone


class Disponibilidade(StrictModel):
    inicio: str
    aviso_previo_dias: int
    aceita_viagens_esporadicas: bool
    aceita_mudanca_cidade: bool
    modalidades_aceitas: list[str]


class Contrato(StrictModel):
    aceita: list[str]
    possui_cnpj: bool


class FaixaSalarial(StrictModel):
    min: int
    max: int
    formulario: int

    @field_validator("formulario")
    @classmethod
    def ensure_within_range(cls, formulario: int, info: ValidationInfo) -> int:
        minimum = info.data.get("min")
        maximum = info.data.get("max")
        if minimum is not None and maximum is not None and not minimum <= formulario <= maximum:
            raise ValueError(f"deve estar entre min ({minimum}) e max ({maximum})")
        return formulario


class PretensaoPorContrato(StrictModel):
    clt: FaixaSalarial
    pj: FaixaSalarial


class Pretensao(StrictModel):
    junior: PretensaoPorContrato
    pleno: PretensaoPorContrato
    padrao_nivel: NivelVaga


class Formacao(StrictModel):
    curso: str
    instituicao: str
    status: str
    conclusao_prevista: str


class Diversidade(StrictModel):
    genero: str
    orientacao_sexual: str
    raca_cor: str
    pcd: bool


class Busca(StrictModel):
    localizacao: str
    modalidade: Literal["remoto"]
    niveis: list[NivelVaga]
    publicadas_ha_no_maximo_dias: int
    somente_easy_apply: bool
    termos_bloqueados_no_titulo: list[str]
    empresas_bloqueadas: list[str]
    palavras_bloqueadas: list[str]


class Curriculo(StrictModel):
    arquivo: Path
    nome: str
    padrao: bool = False
    buscas: list[str]

    @field_validator("arquivo")
    @classmethod
    def resolve_existing_resume_file(cls, arquivo: Path, info: ValidationInfo) -> Path:
        if arquivo.suffix.lower() not in SUPPORTED_RESUME_EXTENSIONS:
            raise ValueError(f"formato não suportado (use .docx ou .pdf): {arquivo}")
        resolved = info.context["base_dir"] / arquivo
        if not resolved.is_file():
            raise ValueError(f"arquivo não encontrado: {arquivo}")
        return resolved


class Regras(StrictModel):
    score_minimo: int = Field(ge=0, le=100)
    limite_diario: int = Field(ge=1)
    modo_busca_quantidade: int
    ajuste_cv_ia: bool


class Config(StrictModel):
    perfil: Perfil
    disponibilidade: Disponibilidade
    contrato: Contrato
    pretensao: Pretensao
    idiomas: dict[str, NivelIdioma]
    formacao: Formacao
    experiencia_anos: dict[str, AnosExperiencia]
    diversidade: Diversidade
    busca: Busca
    curriculos: list[Curriculo]
    regras: Regras
    respostas: dict[str, str]
    resposta_generica: str

    @field_validator("resposta_generica")
    @classmethod
    def ensure_generic_answer_text(cls, resposta_generica: str) -> str:
        if not resposta_generica.strip():
            raise ValueError("não pode ficar vazia")
        return resposta_generica.strip()

    @field_validator("curriculos")
    @classmethod
    def ensure_single_default(cls, curriculos: list[Curriculo]) -> list[Curriculo]:
        if sum(curriculo.padrao for curriculo in curriculos) != 1:
            raise ValueError("exatamente um currículo deve ter padrao: true")
        names = [curriculo.nome for curriculo in curriculos]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise ValueError(f"nome de currículo repetido: {', '.join(repeated)}")
        return curriculos


@dataclass(frozen=True)
class ConfigIssue:
    line: int | None
    field: str
    problem: str


class ConfigError(Exception):
    def __init__(self, issues: list[ConfigIssue]) -> None:
        super().__init__(f"config.md inválido ({len(issues)} erros)")
        self.issues = issues


@dataclass(frozen=True)
class MarkdownSection:
    heading_line: int
    lines: list[tuple[int, str]]


@dataclass(frozen=True)
class ParsedAnswers:
    answers: dict[str, str]
    issues: list[ConfigIssue]
