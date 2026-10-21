from pathlib import Path

import pytest


@pytest.fixture
def base_dir(tmp_path: Path) -> Path:
    resumes_dir = tmp_path / "cv_base"
    resumes_dir.mkdir()
    (resumes_dir / "backend.docx").write_bytes(b"docx")
    (resumes_dir / "dados.pdf").write_bytes(b"pdf")
    return tmp_path


@pytest.fixture
def valid_data() -> dict[str, object]:
    return {
        "perfil": {
            "nome": "Maria Teste da Silva",
            "primeiro_nome": "Maria",
            "sobrenome": "Teste da Silva",
            "email": "maria.teste@example.com",
            "telefone": "+55 11 91234-5678",
            "ddd": "11",
            "celular": "91234-5678",
            "cidade": "São Paulo",
            "estado": "SP",
            "pais": "Brasil",
            "linkedin": "https://www.linkedin.com/in/maria-teste",
            "github": "https://github.com/maria-teste",
            "portfolio": None,
            "autorizado_trabalhar_brasil": True,
            "precisa_patrocinio_visto": False,
        },
        "disponibilidade": {
            "inicio": "Imediato",
            "aviso_previo_dias": 0,
            "aceita_viagens_esporadicas": True,
            "aceita_mudanca_cidade": False,
            "modalidades_aceitas": ["remoto"],
        },
        "contrato": {"aceita": ["CLT", "PJ"], "possui_cnpj": False},
        "pretensao": {
            "junior": {
                "clt": {"min": 3000, "max": 4000, "formulario": 3500},
                "pj": {"min": 4000, "max": 5000, "formulario": 4500},
            },
            "pleno": {
                "clt": {"min": 6000, "max": 7000, "formulario": 6500},
                "pj": {"min": 7000, "max": 9000, "formulario": 8000},
            },
            "padrao_nivel": "junior",
        },
        "idiomas": {"portugues": "nativo", "ingles": "intermediario"},
        "formacao": {
            "curso": "Ciência da Computação",
            "instituicao": "Universidade Teste",
            "status": "em andamento",
            "conclusao_prevista": "2027-12",
        },
        "experiencia_anos": {"Python": 3, "SQL": 2},
        "diversidade": {
            "genero": "Mulher cisgênero",
            "orientacao_sexual": "Prefiro não informar",
            "raca_cor": "Parda",
            "pcd": False,
        },
        "busca": {
            "localizacao": "Brasil",
            "modalidade": "remoto",
            "niveis": ["junior", "pleno"],
            "publicadas_ha_no_maximo_dias": 7,
            "somente_easy_apply": True,
            "termos_bloqueados_no_titulo": ["Sênior"],
            "empresas_bloqueadas": [],
            "palavras_bloqueadas": [],
        },
        "curriculos": [
            {
                "arquivo": "cv_base/backend.docx",
                "nome": "Back-end",
                "padrao": True,
                "buscas": ["Desenvolvedor Python"],
            },
            {
                "arquivo": "cv_base/dados.pdf",
                "nome": "Dados",
                "buscas": ["Analista de Dados"],
            },
        ],
        "regras": {
            "score_minimo": 70,
            "limite_diario": 15,
            "modo_busca_quantidade": 10,
            "ajuste_cv_ia": False,
        },
        "respostas": {"aceita pj": "Sim"},
        "resposta_generica": "Tenho interesse na vaga.",
    }
