# LinkedIn Auto-Apply

Ferramenta pessoal para encontrar vagas Easy Apply do LinkedIn (remotas, Brasil, Júnior e Pleno), comparar com os seus currículos e se candidatar. Requisitos completos em [`PRD.md`](PRD.md); o desenho técnico de cada marco fica em [`specs/`](specs/).

**Status:** M2 (leitura) concluído: coleta de vagas, avaliação por LLM e modo busca com as pastas das 10 melhores vagas. As candidaturas chegam nos marcos M3 e M4.

## Requisitos

- [uv](https://docs.astral.sh/uv/) e Python 3.13 ou mais novo
- Chromium do Playwright (instalado no passo abaixo)
- Opcional, para a análise por LLM: o [Claude Code](https://claude.com/claude-code) (`claude`) logado e/ou o [OpenCode](https://opencode.ai) (`opencode`) no PATH. Sem nenhum dos dois, a avaliação usa só palavras-chave

## Instalação

```bash
uv sync
PLAYWRIGHT_BROWSERS_PATH=.playwright uv run playwright install chromium
```

O Chromium fica em `.playwright/` dentro do projeto. O `autoapply` usa essa pasta automaticamente quando a variável `PLAYWRIGHT_BROWSERS_PATH` não está definida.

## Configuração

Comece copiando o modelo, que tem todas as seções com dados fictícios, e troque pelos seus dados:

```bash
cp config.example.md config.md
```

Estes arquivos ficam só na sua máquina (estão no `.gitignore`):

| Caminho | Conteúdo |
|---|---|
| `config.md` | Frontmatter YAML com perfil, pretensão, buscas, currículos e regras; depois as seções `# Respostas padrão` (tabela pergunta → resposta) e `# Resposta genérica` (blockquote) |
| `cv_base/` | Currículos `.docx` ou `.pdf`, um deles marcado como `padrao: true` no `config.md` |
| `data/browser-profile/` | Perfil do navegador com a sessão do LinkedIn |
| `data/autoapply.db` | Banco SQLite com as vagas e as análises |
| `vagas/` | Uma pasta por vaga do modo busca, com o `vaga.md` |
| `logs/` | Log do dia em JSON Lines (`AAAA-MM-DD.log`), com e-mail e telefone mascarados |
| `debug/` | Print e HTML de páginas inesperadas |

## Comandos

```bash
uv run autoapply validar                # valida o config.md e os currículos
uv run autoapply login                  # abre o navegador para você logar à mão
uv run autoapply sessao [--visivel]     # confere se a sessão salva ainda vale
uv run autoapply coletar [--visivel]    # coleta as vagas e grava no banco
uv run autoapply buscar [--visivel]     # coleta, avalia e cria as pastas das 10 melhores vagas
uv run autoapply vagas [--status <s>]   # mostra as vagas do banco (coletada, ignorada, avaliada, aguardando_cv)
uv run autoapply --verbose <comando>    # mostra mensagens de depuração
uv run autoapply --version
```

| Comando | Código de saída |
|---|---|
| `validar` | `0` válido · `2` config ou currículo padrão inválido |
| `login` | `0` sessão salva · `1` não logou em 5 min |
| `sessao` | `0` sessão ativa · `1` sessão expirada · `3` verificação ou página inesperada (salva em `debug/`) |
| `coletar` e `buscar` | `0` ok · `1` sessão expirada · `2` config inválido · `3` verificação ou página inesperada (salva em `debug/`) |

O login é sempre manual: o sistema nunca guarda a sua senha e nunca tenta resolver CAPTCHA ou verificação. Quando aparece uma, ele para e avisa.

## Modo busca

1. **Coleta:** para cada termo das `buscas` dos currículos, abre a busca do LinkedIn (Easy Apply, remoto, Brasil, níveis do `config.md`) e lê só as vagas novas, com uma pausa aleatória de 3 a 15 s entre as ações. Título, empresa ou palavra bloqueada e vaga sem Candidatura simplificada ficam `ignorada`, com o motivo.
2. **Avaliação:** calcula um pré-score por palavras-chave para cada currículo. As `regras.analise_llm_max_vagas` melhores vão para o LLM, na ordem de `llm.provedores`; uma falha tenta de novo uma vez e depois passa para o próximo provedor. As outras vagas, ou quando nenhum LLM responde, recebem a análise simplificada por palavras-chave, com aviso no terminal e no `vaga.md`.
3. **Pastas:** as `regras.modo_busca_quantidade` vagas de maior score viram `vagas/AAAA-MM-DD-empresa-cargo/vaga.md` (resumo, requisitos, palavras-chave, gap e descrição completa) e ficam `aguardando_cv`. Salve o currículo adaptado na pasta como `cv.docx` ou `cv.pdf`.

Uma nova execução não duplica vagas, não reanalisa as já avaliadas e não repete as que estão em `aguardando_cv`. Só o texto da vaga, os currículos (com e-mail e telefone mascarados), os níveis e os anos de experiência vão para o LLM.

O OpenCode lê a configuração de `$XDG_CONFIG_HOME` e `$XDG_DATA_HOME`. Se ele não achar o login ou os modelos ao rodar pelo `autoapply`, confira essas variáveis.

## Testes

```bash
uv run pytest
```

Os testes de sessão e de coleta usam o Chromium headless com páginas falsas e nunca acessam o LinkedIn de verdade. Os testes de LLM usam executáveis `claude` e `opencode` falsos.
