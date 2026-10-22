# LinkedIn Auto-Apply

Ferramenta pessoal para encontrar vagas Easy Apply do LinkedIn (remotas, Brasil, Júnior e Pleno), comparar com os seus currículos e se candidatar. Requisitos completos em [`PRD.md`](PRD.md); o desenho técnico de cada marco fica em [`specs/`](specs/).

**Status:** M4 (ajuste por IA) concluído, fechando o MVP: coleta de vagas, avaliação por LLM, modo busca com as pastas das 10 melhores vagas, candidatura pelo Easy Apply no modo busca (`apply`) e no modo normal (`run`), ajuste do currículo por IA e relatório (`report`).

## Requisitos

- [uv](https://docs.astral.sh/uv/) e Python 3.13 ou mais novo
- Chromium do Playwright (instalado no passo abaixo)
- Opcional, para a análise por LLM: o [Claude Code](https://claude.com/claude-code) (`claude`) logado e/ou o [OpenCode](https://opencode.ai) (`opencode`) no PATH. Sem nenhum dos dois, a avaliação usa só palavras-chave

## Instalação

```bash
make
```

O `make` mostra o que vai ser feito e pergunta se deseja continuar. Depois instala o uv (se faltar), as dependências e o Chromium do Playwright, cria o `config.md` a partir do `config.example.md` (se ainda não existir) e a pasta `cv_base/`, e abre o navegador para você fazer login no LinkedIn. Depois disso, falta só preencher o `config.md` e colocar os currículos em `cv_base/`.

Sem `make`, os mesmos passos à mão:

```bash
uv sync
PLAYWRIGHT_BROWSERS_PATH=.playwright uv run playwright install chromium
cp config.example.md config.md
uv run autoapply login
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
| `data/autoapply.db` | Banco SQLite com as vagas, as análises, as tentativas de candidatura e as perguntas pendentes |
| `vagas/` | Uma pasta por vaga do modo busca, com o `vaga.md`, o `respostas.md` e o seu `cv.docx` ou `cv.pdf` |
| `curriculos-enviados/` | PDFs dos currículos ajustados pela IA (`AAAA-MM-DD-empresa-cargo.pdf`) |
| `logs/` | Log do dia em JSON Lines (`AAAA-MM-DD.log`), com e-mail e telefone mascarados |
| `debug/` | Print e HTML de páginas inesperadas e de falhas na candidatura; HTML da tela de sucesso de cada envio; em `debug/simulacao-cv/`, os PDFs ajustados do `--simulate` |

## Comandos

```bash
uv run autoapply --tutorial                                                              # mostra o passo a passo de uso
uv run autoapply validate                                                                # valida o config.md e os currículos
uv run autoapply login                                                                   # abre o navegador para você logar à mão
uv run autoapply session [--visible]                                                     # confere se a sessão salva ainda vale
uv run autoapply collect [--visible]                                                     # coleta as vagas e grava no banco
uv run autoapply search [--visible]                                                      # coleta, avalia e cria as pastas das 10 melhores vagas
uv run autoapply jobs [--status <s>]                                                     # mostra as vagas do banco (coletada, ignorada, avaliada, aguardando_cv,
                                                                                         # aplicada, falhou, pendente_pergunta)
uv run autoapply apply <job> [--auto] [--interactive] [--simulate] [--visible]           # aplica numa vaga do modo busca (ID ou pasta)
uv run autoapply apply --ready [--auto] [--interactive] [--simulate] [--visible]         # aplica nas vagas com CV na pasta
uv run autoapply run [--auto] [--interactive] [--skip-collect] [--simulate] [--visible]  # modo normal: coleta, avalia e aplica
uv run autoapply pending                                                                 # perguntas sem resposta que travaram candidaturas
uv run autoapply report [--days N] [--csv <arquivo>]                                     # histórico das candidaturas (padrão 7 dias; 0 = tudo) e CSV
uv run autoapply --verbose <comando>                                                     # mostra mensagens de depuração
uv run autoapply --version
uv run autoapply <comando> -h                                                            # mostra as opções de um comando
```

| Comando | Código de saída |
|---|---|
| `validate` | `0` válido · `2` config ou currículo padrão inválido |
| `login` | `0` sessão salva · `1` não logou em 5 min |
| `session` | `0` sessão ativa · `1` sessão expirada · `3` verificação ou página inesperada (salva em `debug/`) |
| `collect` e `search` | `0` ok · `1` sessão expirada · `2` config inválido · `3` verificação ou página inesperada (salva em `debug/`) |
| `apply` e `run` | Os mesmos de `collect`, mais `2` para `<job>` não encontrada ou argumento faltando |

O login é sempre manual: o sistema nunca guarda a sua senha e nunca tenta resolver CAPTCHA ou verificação. Quando aparece uma, ele para e avisa.

## Modo busca

1. **Coleta:** para cada termo das `buscas` dos currículos, abre a busca do LinkedIn (Easy Apply, remoto, Brasil, níveis do `config.md`) e lê só as vagas novas, com uma pausa aleatória de 3 a 15 s entre as ações. Título, empresa ou palavra bloqueada e vaga sem Candidatura simplificada ficam `ignorada`, com o motivo.
2. **Avaliação:** calcula um pré-score por palavras-chave para cada currículo. As `regras.analise_llm_max_vagas` melhores vão para o LLM, na ordem de `llm.provedores`; se um provedor falha, passa para o próximo. As outras vagas, ou quando nenhum LLM responde, recebem a análise simplificada por palavras-chave, com aviso no terminal e no `vaga.md`.
3. **Pastas:** as `regras.modo_busca_quantidade` vagas de maior score viram `vagas/AAAA-MM-DD-empresa-cargo/vaga.md` (resumo, requisitos, palavras-chave, gap e descrição completa) e ficam `aguardando_cv`. Salve o currículo adaptado na pasta como `cv.docx` ou `cv.pdf`.

Uma nova execução não duplica vagas, não reanalisa as já avaliadas e não repete as que estão em `aguardando_cv`. Só o texto da vaga, os currículos (com e-mail e telefone mascarados), os níveis e os anos de experiência vão para o LLM.

O OpenCode lê a configuração de `$XDG_CONFIG_HOME` e `$XDG_DATA_HOME`. Se ele não achar o login ou os modelos ao rodar pelo `autoapply`, confira essas variáveis.

## Candidaturas

- **Modo busca:** salve o currículo adaptado na pasta da vaga como `cv.docx` ou `cv.pdf` (até 2 MB, com texto legível) e rode `apply <job>` ou `apply --ready`. No `respostas.md` da pasta você pode responder perguntas só daquela vaga, além das linhas especiais `pretensão salarial` e `mensagem`. Essas respostas têm prioridade sobre o `config.md`.
- **Modo normal:** `run` coleta e avalia como o `search` e aplica nas vagas sem pasta com score maior ou igual a `regras.score_minimo`, do maior score para o menor, com o currículo do `cv_base/` escolhido na análise. As vagas avaliadas abaixo do mínimo ficam `ignorada`, com o motivo. Com `--skip-collect`, aplica direto nas vagas já avaliadas no banco.
- **Perguntas sem resposta:** com `--interactive` (no `run` e no `apply`), o terminal pergunta o que viraria pendente; Enter vazio deixa a vaga pendente, e uma resposta válida pode ser salva no `config.md`. O campo de cidade com autocomplete usa `perfil.cidade`.
- **Envio:** com `--auto`, envia sem perguntar. Sem a flag, mostra as respostas preenchidas e pergunta `Enviar? [y/N]`; com "n", descarta o rascunho e não grava nada. O `--simulate` percorre o formulário, nunca clica em Enviar e não grava nada no banco.
- **Respostas:** contato vem do perfil; depois `respostas.md` da vaga, respostas padrão do `config.md`, pretensão pelo nível do título (CLT ou PJ), anos de experiência pelas tecnologias citadas na pergunta, o valor que o LinkedIn já trouxe preenchido e, em texto livre, a resposta genérica. Pergunta objetiva sem resposta não é chutada: a vaga vira `pendente_pergunta` e aparece em `pending`, que diz onde responder.
- **Limite e ritmo:** no máximo `regras.limite_diario` candidaturas por dia, somando `apply` e `run`. Pausa de 2 a 6 s entre etapas do formulário e de 20 a 60 s entre candidaturas. O currículo sempre vai por upload e "Siga a empresa" é desmarcado.
- **Segurança:** uma vaga já aplicada nunca é reenviada. Sem a tela de sucesso depois do Enviar, a vaga fica `falhou`, com dump em `debug/`, para você conferir à mão.

## Ajuste do currículo por IA

Com `regras.ajuste_cv_ia: true`, o `run` ajusta o currículo `.docx` escolhido antes de cada candidatura real (o modo busca continua com o seu `cv.docx` ou `cv.pdf`):

- **O que muda:** o LLM (na ordem de `llm.provedores`, uma tentativa por provedor) reescreve o Resumo Profissional e reordena os bullets de cada experiência e as competências. Cargos, empresas, datas e o texto dos bullets não mudam. O cabeçalho com os seus contatos não vai para o LLM, e o resto vai com e-mail e telefone mascarados.
- **Checagem:** o plano só vale se as ordens forem permutações completas e o resumo não estiver vazio, não passar do dobro do original e não citar tecnologia, número ou nome que não está no currículo base. O PDF gerado é relido para conferir o texto.
- **Resultado:** o PDF, com o visual do `.docx`, vai para `curriculos-enviados/AAAA-MM-DD-empresa-cargo.pdf` e a linha da vaga mostra `cv ajustado`. Se a checagem reprova ou nenhum LLM responde, vai o currículo base e a linha mostra `ajuste descartado: <motivo>`. Uma vaga que volta (ex.: depois de uma pendente) reaproveita o PDF já usado.
- **Simulação:** com `--simulate`, os PDFs vão para `debug/simulacao-cv/` e nada é gravado no banco.

## Relatório

`report` lê só o banco local e mostra, para os últimos `--days` dias (padrão 7; `0` = todo o histórico): tentativas por modo e resultado, vagas ignoradas, taxa de conclusão (aplicadas ÷ aplicadas + falhas + pendentes), os 3 motivos de falha mais comuns e a última tentativa de cada vaga, com score e se o currículo foi o base ou o ajustado. Com `--csv <arquivo>`, salva essa lista em CSV com `;` e UTF-8 com BOM, pronto para abrir na planilha.

## Testes

```bash
uv run pytest
```

Os testes de sessão, de coleta e do Easy Apply usam o Chromium headless com páginas e um modal falsos, montados a partir de HTML real anonimizado, e nunca acessam o LinkedIn de verdade. Os testes de LLM usam executáveis `claude` e `opencode` falsos.
