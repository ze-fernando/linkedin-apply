# LinkedIn Auto-Apply

Ferramenta pessoal para encontrar vagas Easy Apply do LinkedIn (remotas, Brasil, Júnior e Pleno), comparar com os seus currículos e se candidatar. Requisitos completos em [`PRD.md`](PRD.md); o desenho técnico de cada marco fica em [`specs/`](specs/).

**Status:** M1 (base) concluído: validação do `config.md`, leitura dos currículos e sessão persistente do LinkedIn. Coleta, match e candidaturas chegam nos marcos M2 a M4.

## Requisitos

- [uv](https://docs.astral.sh/uv/) e Python 3.13 ou mais novo
- Chromium do Playwright (instalado no passo abaixo)

## Instalação

```bash
uv sync
PLAYWRIGHT_BROWSERS_PATH=.playwright uv run playwright install chromium
```

O Chromium fica em `.playwright/` dentro do projeto. O `autoapply` usa essa pasta automaticamente quando a variável `PLAYWRIGHT_BROWSERS_PATH` não está definida.

## Configuração

Estes arquivos ficam só na sua máquina (estão no `.gitignore`):

| Caminho | Conteúdo |
|---|---|
| `config.md` | Frontmatter YAML com perfil, pretensão, buscas, currículos e regras; depois as seções `# Respostas padrão` (tabela pergunta → resposta) e `# Resposta genérica` (blockquote) |
| `cv_base/` | Currículos `.docx` ou `.pdf`, um deles marcado como `padrao: true` no `config.md` |
| `data/browser-profile/` | Perfil do navegador com a sessão do LinkedIn |
| `logs/` | Log do dia em JSON Lines (`AAAA-MM-DD.log`), com e-mail e telefone mascarados |
| `debug/` | Print e HTML de páginas inesperadas |

## Comandos

```bash
uv run autoapply validar                # valida o config.md e os currículos
uv run autoapply login                  # abre o navegador para você logar à mão
uv run autoapply sessao [--visivel]     # confere se a sessão salva ainda vale
uv run autoapply --verbose <comando>    # mostra mensagens de depuração
uv run autoapply --version
```

| Comando | Código de saída |
|---|---|
| `validar` | `0` válido · `2` config ou currículo padrão inválido |
| `login` | `0` sessão salva · `1` não logou em 5 min |
| `sessao` | `0` sessão ativa · `1` sessão expirada · `3` verificação ou página inesperada (salva em `debug/`) |

O login é sempre manual: o sistema nunca guarda a sua senha e nunca tenta resolver CAPTCHA ou verificação. Quando aparece uma, ele para e avisa.

## Testes

```bash
uv run pytest
```

Os testes de sessão usam o Chromium headless com páginas falsas e nunca acessam o LinkedIn de verdade.
