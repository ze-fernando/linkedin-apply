# Spec técnica — M1: Base

**Status:** Concluído · **Atualizado:** 2026-10-21
**PRD:** [../PRD.md](../PRD.md) — Épico 1 (config e currículos), História 5.1 (login persistente), Épico 6 (logs com Rich, parcial)

## 1. Objetivo

Deixar pronta a fundação que todos os outros marcos usam:

1. Projeto Python instalável, com CLI e logs bonitos (Rich).
2. Leitura e validação do `config.md`, com erro apontando linha e campo.
3. Carregamento dos currículos de `cv_base/` (`.docx` e `.pdf`) com extração de texto.
4. Login no LinkedIn com sessão persistente e detecção de checkpoint/CAPTCHA.

**Pronto quando:** `autoapply validar` mostra config e currículos OK, `autoapply login` loga uma vez e `autoapply sessao` confirma a sessão válida numa execução seguinte, sem pedir senha.

**Fora do M1:** busca de vagas, banco de dados, matching, Easy Apply, intervalos "humanos" entre ações (M2+).

## 2. Ambiente e stack

| Item | Escolha | Motivo |
|---|---|---|
| Linguagem | Python 3.15 (`requires-python >= 3.13`) | PRD. Mínimo 3.13 como reserva caso alguma dependência ainda não tenha wheel para 3.15 |
| Gerenciador | `uv` | Instala o próprio Python (a distrobox não tem Python), lockfile, rápido |
| Navegador | Playwright + Chromium | API estável, contexto persistente, interceptação de rede para testes |
| CLI | Typer | Subcomandos e `--help` sem esforço |
| Terminal | Rich (`Console`, `RichHandler`, `Progress`, `Table`, `Panel`) | PRD, Épico 6 |
| Config | PyYAML + Pydantic v2 | YAML com posição de linha + validação tipada |
| Currículos | `python-docx`, `pypdf` | Extração de texto, sem dependências nativas |
| Testes | pytest (+ `pytest-playwright` para sessão) | — |

Ambiente (validado em 2026-10-21, dentro do ai-jail):

- `uv` 0.13.4 e Python 3.15.0 mapeados do host. As dependências instalam e importam no 3.15.
- Chromium 156 em `.playwright/` (`PLAYWRIGHT_BROWSERS_PATH`), baixado pelo host porque o sandbox bloqueia `storage.googleapis.com`.
- Modo headless e janela visível no Wayland (`--ozone-platform=wayland`) funcionando.
- `linkedin.com` e `licdn.com` liberados. `accounts.google.com` e `www.google.com` continuam bloqueados (sem "Entrar com Google" e, possivelmente, sem reCAPTCHA).
- Login manual feito com o perfil `data/browser-profile/`. Uma execução seguinte em headless abriu `/feed/foryou/` já logada (cookie `li_at`).

Achados para a implementação:

- O formulário de login usa `input[type=email]` e `input[type=password]`. Os antigos `#username` e `session_key` não existem mais.
- O feed abre em `/feed/foryou/`, então o estado "logado" deve aceitar o prefixo `/feed`.
- O login pode terminar em outra aba, então o polling deve olhar todas as páginas do contexto.

## 3. Estrutura do projeto

Estrutura **modular** (regra de `instructions.md` das regras globais em `~/.claude/ai-docs/`): cada funcionalidade é um módulo em `modules/`, com seus tipos, funções e comandos de CLI.

```
linkedin-scraping/
├── PRD.md
├── specs/M1-base.md
├── config.md                 # dados pessoais (gitignored)
├── cv_base/                  # currículos (gitignored)
├── pyproject.toml
├── src/autoapply/
│   ├── __init__.py
│   ├── main.py               # app Typer, registra os comandos dos módulos
│   ├── shared/
│   │   ├── paths.py          # caminhos do projeto (data/, logs/, debug/)
│   │   └── console.py        # Console Rich + configuração de logging
│   └── modules/
│       ├── config/
│       │   ├── models.py     # tipos Pydantic do config.md
│       │   ├── loader.py     # parse do config.md (frontmatter + markdown)
│       │   ├── answers.py    # normalização e busca de respostas
│       │   └── commands.py   # comando `validar`
│       ├── resumes/
│       │   ├── models.py     # tipo Resume
│       │   └── loader.py     # carga e extração de texto dos currículos
│       └── session/
│           ├── models.py     # enum PageState, exceções
│           ├── detection.py  # detecção do estado da página
│           ├── browser.py    # abrir navegador, login, status da sessão
│           └── commands.py   # comandos `login` e `sessao`
├── tests/
│   ├── fixtures/             # config.md de exemplo, HTML de páginas do LinkedIn
│   └── modules/              # espelha src/autoapply/modules
├── data/                     # perfil do navegador (gitignored)
├── logs/                     # logs em arquivo (gitignored)
└── debug/                    # screenshots + HTML de falhas (gitignored)
```

> As anotações `# ...` da árvore acima são só documentação da spec. O código não terá comentários.

### 3.1 Regras de código (das regras globais em `~/.claude/ai-docs/`)

- **Nenhum comentário no código**, em nenhuma hipótese. Os nomes de funções e variáveis devem se explicar.
- **Classes só para DTOs e tipos** (modelos Pydantic, dataclasses, enums, exceções). Lógica sempre em **funções de módulo**: nada de `Service`, `Repository` ou `Manager`.
- **Tipagem obrigatória** em parâmetros, retornos e tipos customizados. **Não** tipar variáveis locais comuns.
- Nomes de funções descritivos (`load_config`, `extract_resume_text`, `detect_page_state`), sem abreviações.
- **Commits:** semânticos, com emoji, conforme o `guia-commits.md` das regras globais (ex.: `:sparkles: feat: Leitura do config`). Primeira linha com no máximo 4 palavras. **Sem `Co-Authored-By`**. O guia deve ser consultado antes de cada commit.

**Idioma dos identificadores:** funções e tipos em inglês. Os campos dos modelos de config usam as mesmas chaves em português do `config.md`, sem alias.

## 4. Config (`config.md`)

### 4.1 Formato

- **Frontmatter YAML** entre os dois primeiros `---`: dados estruturados.
- **Corpo markdown**:
  - `# Respostas padrão`: primeira tabela da seção, colunas *Pergunta* | *Resposta*.
  - `# Resposta genérica`: texto do primeiro blockquote (`>`) da seção, com as linhas unidas.

### 4.2 Modelos (Pydantic, `extra="forbid"`)

```python
class Config:            # raiz
    perfil: Perfil
    disponibilidade: Disponibilidade
    contrato: Contrato
    pretensao: Pretensao          # junior/pleno -> clt/pj -> {min, max, formulario}; padrao_nivel
    idiomas: dict[str, Nivel]
    formacao: Formacao
    experiencia_anos: dict[str, int]   # >= 0
    diversidade: Diversidade
    busca: Busca
    curriculos: list[Curriculo]        # exatamente 1 com padrao=true
    regras: Regras                     # score_minimo 0-100, limite_diario >= 1
    respostas: dict[str, str]          # vem do corpo markdown (chave normalizada)
    resposta_generica: str             # vem do corpo markdown, não vazia
```

Validações além dos tipos:

- `pretensao.*.*`: `min <= formulario <= max`.
- `curriculos`: exatamente um `padrao: true`; nomes únicos; cada `arquivo` existe e termina em `.docx` ou `.pdf`.
- `perfil.email`: e-mail válido. `perfil.telefone`: começa com `+55`.
- `busca.modalidade`: `remoto` (único valor aceito no MVP).

### 4.3 Erros com linha

1. **Erro de sintaxe YAML:** PyYAML já traz a linha. Soma-se o deslocamento do frontmatter (linha 2 do arquivo).
2. **Erro de validação:** o `loc` do Pydantic (ex.: `("pretensao", "pleno", "pj", "formulario")`) é resolvido percorrendo a árvore de nós do `yaml.compose()`, que guarda `start_mark.line`.
3. Todos os erros são mostrados juntos numa tabela Rich (linha · campo · problema), e o comando sai com código 2.

```
✖ config.md inválido (2 erros)
 Linha │ Campo                        │ Problema
 42    │ pretensao.pleno.pj.formulario│ deve estar entre min (6000) e max (7000)
 112   │ curriculos[0].arquivo        │ arquivo não encontrado: cv_base/dotnet.docx
```

### 4.4 Respostas

- **Normalização** (`answers.normalize`): minúsculas, sem acentos (NFKD), sem pontuação, espaços colapsados. Ex.: `"Aceita contratação PJ?"` → `"aceita contratacao pj"`.
- `find_answer(pergunta) -> str | None`: busca exata pela chave normalizada. A busca aproximada (sinônimos, LLM) fica para o M3.
- Duas perguntas que viram a mesma chave normalizada geram erro de validação.

## 5. Currículos

```python
@dataclass(frozen=True)
class Resume:
    name: str           # "Back-end .NET"
    path: Path
    is_default: bool
    searches: list[str]
    text: str           # texto extraído
```

- `.docx`: parágrafos do corpo + células de tabelas, na ordem do documento.
- `.pdf`: `pypdf`, página a página.
- **Texto insuficiente** (< 300 caracteres sem espaços): o currículo é marcado como **inválido** (provável PDF escaneado), aparece no `validar` com aviso e é ignorado pelos marcos seguintes. Se o currículo padrão for inválido, o erro é fatal.
- Sem cache no M1: a extração leva milissegundos.

## 6. Sessão do LinkedIn

### 6.1 Abordagem

- **Contexto persistente** do Playwright (`launch_persistent_context(user_data_dir="data/browser-profile")`). Guarda cookies, localStorage e o histórico como um navegador normal, o que é mais parecido com uso humano que injetar `storage_state`.
- Locale `pt-BR`, fuso `America/Bahia`, viewport fixo de desktop. Sem truques anti-detecção, porque a constituição do PRD proíbe contornar verificações.
- **Senha nunca é usada pelo sistema.** O login é sempre manual, na janela aberta (decisão do PRD, História 5.1). Assim não existe `.env` com senha no M1.

### 6.2 Estados da página (`detection.py`)

| Estado | Como detectar (por URL primeiro, DOM como reforço) |
|---|---|
| `LOGGED_IN` | URL com prefixo `/feed` (ex.: `/feed/foryou/`), `/jobs` ou `/in/`, e presença da barra de navegação global (links para `/mynetwork` ou `/messaging`, porque as classes do LinkedIn são ofuscadas) |
| `LOGGED_OUT` | URL em `/login`, `/uas/login`, `/authwall` ou formulário de login visível |
| `CHECKPOINT` | URL em `/checkpoint/` ou `/challenge`, ou iframe/elemento de CAPTCHA |
| `UNKNOWN` | Nenhum dos anteriores |

Os seletores ficam centralizados em `detection.py`. A detecção é uma função pura sobre `(url, html)`, testável com HTML salvo.

### 6.3 Comandos

- **`autoapply login`**: abre o navegador **visível** em `linkedin.com/login`. Você loga à mão (incluindo 2FA). O sistema verifica o estado a cada 2 s, com timeout de 5 min:
  - `LOGGED_IN` → painel verde "Sessão salva", fecha o navegador.
  - `CHECKPOINT` → painel amarelo "Resolva a verificação na janela", continua esperando.
  - Timeout → erro, sai com código 1.
- **`autoapply sessao [--visivel]`**: abre o navegador (headless por padrão), vai para `/feed` e informa o estado:
  - `LOGGED_IN` → OK (código 0).
  - `LOGGED_OUT` → "Sessão expirada, rode `autoapply login`" (código 1).
  - `CHECKPOINT`/`UNKNOWN` → salva screenshot + HTML em `debug/<timestamp>-<estado>/` e avisa (código 3).
- **API interna** usada pelos próximos marcos: `with open_browser_context(headless, profile_dir) as context:` abre o navegador e `ensure_session(context) -> Page` devolve a página do feed. Levanta `SessionExpired`, `CheckpointDetected` ou `UnknownPageState`, que interrompem a execução inteira.

## 7. CLI e logs

```
autoapply validar           # valida config.md + currículos, mostra resumo
autoapply login             # login manual com janela visível
autoapply sessao [--visivel]
autoapply --verbose ...     # nível DEBUG no terminal
```

- `shared/console.py` cria um único `Console` e configura o `logging`:
  - **Terminal:** `RichHandler` (INFO; DEBUG com `--verbose`), com cores, horário e sem caminho do arquivo.
  - **Arquivo:** `logs/AAAA-MM-DD.log` em JSON Lines (DEBUG sempre), com `ts`, `level`, `event`, `msg` e campos extras.
- Dados sensíveis (telefone, e-mail, cookies) nunca vão para o log. Um filtro de logging mascara o e-mail e o telefone se aparecerem.
- `validar` mostra:
  - um painel com nome, contato, níveis, contrato e regras;
  - uma tabela de currículos (nome, arquivo, padrão, nº de caracteres, status);
  - a quantidade de respostas padrão e se há resposta genérica.

## 8. Testes

| Área | Como |
|---|---|
| Config: válido | `tests/fixtures/config_ok.md` (dados fictícios) carrega sem erro |
| Config: erros | Um caso por regra (YAML quebrado, campo extra, `formulario` fora da faixa, dois padrões, arquivo inexistente), verificando **linha e campo** do erro |
| Respostas | Normalização (acentos, pontuação), colisão de chaves, tabela e blockquote do corpo |
| Currículos | `.docx` gerado no teste com `python-docx`; PDF com texto; PDF sem texto → inválido |
| Detecção | `detect_page_state(url, html)` com HTML salvo de cada estado em `tests/fixtures/pages/` |
| Sessão | Playwright headless com `context.route("**/*")` servindo as páginas fixture. Nunca acessa o LinkedIn de verdade. Sem redirecionamento 302, porque o Playwright não intercepta o destino do redirect; uma trava no fixture falha o teste se alguma requisição escapar da rota |
| CLI | `typer.testing.CliRunner` para `validar` (códigos de saída e textos principais) |

**Ficam sem teste automático:** o login real e a sessão real. São validados à mão no critério de pronto.

## 9. Tarefas

- [x] **T1 — Setup.** `uv init`, `pyproject.toml` com as dependências e o entry point `autoapply`, `.gitignore` (`config.md`, `cv_base/`, `cv.docx`, `data/`, `logs/`, `debug/`, `.venv/`), `git init` e commit inicial (`:tada: init: Commit inicial`). Verificar se Playwright, Pydantic e python-docx têm wheels para a versão de Python escolhida.
  *Pronto:* `uv run autoapply --help` funciona.
- [x] **T2 — `shared/console.py` + logging.** Console Rich, `RichHandler`, arquivo JSONL, filtro de dados sensíveis.
  *Pronto:* teste confirma que e-mail e telefone saem mascarados no arquivo.
- [x] **T3 — Modelos de config.** Pydantic com todas as validações da seção 4.2.
  *Pronto:* testes de modelo passam.
- [x] **T4 — Loader do `config.md`.** Frontmatter, tabela de respostas, resposta genérica e mapeamento de erros para linha.
  *Pronto:* testes de erro verificam linha e campo.
- [x] **T5 — Currículos.** Módulo `resumes` com docx/pdf e detecção de texto insuficiente.
  *Pronto:* testes passam e os 3 CVs reais de `cv_base/` são lidos.
- [x] **T6 — Comando `validar`.** Painel, tabelas e códigos de saída.
  *Pronto:* `uv run autoapply validar` com o `config.md` real mostra tudo OK.
- [x] **T7 — `session/detection.py`.** Estados por URL/DOM com fixtures HTML.
  *Pronto:* testes passam para os 4 estados.
- [x] **T8 — `session/browser.py` + `login`/`sessao`.** Contexto persistente, polling do login, `ensure_session()`, dump em `debug/`.
  *Pronto:* testes com rotas interceptadas passam, e o teste manual (login uma vez e `sessao` OK depois) funciona.
- [x] **T9 — Fechamento.** README curto (setup e comandos) e atualização do PRD (M1 concluído).

Ordem: T1 → T2 → (T3 → T4) ∥ T5 → T6 → T7 → T8 → T9. Um commit semântico por tarefa concluída.

## 10. Decisões (confirmadas em 2026-10-21)

1. **Python:** 3.15, com queda para 3.13 se faltar wheel de alguma dependência.
2. **Navegador:** Chromium do Playwright.
3. **Comando:** `autoapply`.
4. **Identificadores:** funções e tipos em inglês. Os campos do config usam as mesmas chaves em português do `config.md`.
5. **Bibliotecas:** `uv`, Typer, Rich, Pydantic v2, PyYAML, python-docx, pypdf, Playwright e pytest.
6. **Login:** sempre manual, sem senha guardada. Login automático com credenciais no `.env` fica para depois do MVP.
7. **Commits:** emoji em código (`:sparkles: feat: ...`).
