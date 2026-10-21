# Spec técnica — M2: Leitura

**Status:** Aprovado · **Atualizado:** 2026-10-21
**PRD:** [../PRD.md](../PRD.md) — Épico 2 (coleta), História 3.1 (top 10 com análise), FR-004, FR-005, FR-006, NFR-001, NFR-004, NFR-005
**Base:** [M1-base.md](M1-base.md) (config, currículos, sessão, logs)

## 1. Objetivo

1. Coletar vagas Easy Apply remotas no Brasil, usando os termos de busca de cada currículo, e guardar tudo num banco local sem duplicar.
2. Avaliar as vagas: filtros por regra, pré-score por palavras-chave e análise por LLM nas melhores, com escolha do currículo, score, requisitos, palavras-chave e gap.
3. Modo busca: gerar as 10 pastas em `vagas/` com o `vaga.md` de cada vaga, prontas para você adaptar o currículo.

**Pronto quando:** `autoapply buscar` com a sessão real coleta, avalia e cria as 10 pastas com `vaga.md` completo; uma segunda execução não duplica vagas nem reanalisa as já avaliadas.

**Fora do M2:** Easy Apply, `aplicar`, informações específicas da vaga na pasta (História 3.2), modo normal, ajuste de CV por IA, relatório (M3 e M4).

## 2. Ambiente e achados

Validado em 2026-10-21, dentro do ai-jail:

- **Claude Code CLI** 2.1.306 em `~/.local/bin/claude`. A chamada `claude -p --output-format json --json-schema <schema> --model <modelo> --tools "" --no-session-persistence` com o prompt no stdin devolve um JSON com `structured_output` já validado pelo schema e `is_error`. Leva de 8 a 20 s por chamada.
- **OpenCode** está instalado fora da distrobox e **não é visível dentro do ai-jail**: `distrobox-host-exec` não roda dentro da jail e a home do host não está montada. Para usar, é preciso mapear o binário e a configuração/autenticação dele para dentro da jail, como foi feito com o `uv`. A documentação (`opencode.ai`) também está bloqueada pelo proxy, então as flags do `opencode run` serão confirmadas depois do mapeamento (seção 7.3).
- **Busca de vagas** (`/jobs/search/`) usa a interface clássica:
  - URL com filtros: `keywords`, `location=Brasil`, `geoId=106057199`, `f_AL=true` (Easy Apply), `f_WT=2` (remoto), `f_TPR=r604800` (7 dias), `f_E` (nível).
  - A lista tem 25 vagas por página. Cada card tem `data-job-id` (que é o ID da vaga) e um link `/jobs/view/<id>/`. Título, empresa e local vêm do card (`artdeco-entity-lockup__title`, `__subtitle`, `__caption`).
  - Clicar no card abre o painel de detalhe, com `?currentJobId=<id>` na URL e seletores estáveis:

| Dado | Seletor |
|---|---|
| Título | `.job-details-jobs-unified-top-card__job-title` |
| Empresa | `.job-details-jobs-unified-top-card__company-name` |
| Local · data · candidaturas | `.job-details-jobs-unified-top-card__tertiary-description-container` |
| Modalidade e tipo | `.job-details-fit-level-preferences` |
| Descrição | `#job-details` |
| Easy Apply | `.jobs-apply-button` com o texto "Candidatura simplificada" |

- A página avulsa `/jobs/view/<id>/` usa a interface nova, com classes ofuscadas. **Não usar**: o detalhe é sempre lido pelo painel da busca.
- A busca do LinkedIn é frouxa: ".NET" trouxe "Desenvolvedor Ruby Sênior", por isso os filtros por título da seção 6 são obrigatórios. O filtro de local também deixa passar vagas de fora (ex.: "relocalización A Coruña, España"); essas são mantidas (seção 12, item 10).

## 3. Estrutura (novos módulos)

```
src/autoapply/
├── shared/
│   └── database.py          # conexão SQLite e criação das tabelas
└── modules/
    ├── jobs/
    │   ├── models.py        # JobCard, Job, JobStatus
    │   ├── search_url.py    # monta a URL de busca com os filtros
    │   ├── parsing.py       # HTML do card e do painel → dados (funções puras)
    │   ├── filters.py       # bloqueios por título, empresa e palavras
    │   ├── store.py         # leitura e escrita de vagas no banco
    │   ├── collector.py     # navegação Playwright: busca, rolagem, clique, ritmo
    │   └── commands.py      # `coletar`, `vagas`
    ├── matching/
    │   ├── models.py        # JobAnalysis, Analyzer
    │   ├── keywords.py      # vocabulário, pré-score e análise simplificada
    │   ├── prompt.py        # prompt e JSON Schema da análise
    │   ├── providers.py     # claude CLI, opencode CLI, detecção e fallback
    │   └── evaluation.py    # pipeline: filtros → pré-score → top N → LLM
    └── search_mode/
        ├── folders.py       # nome da pasta e conteúdo do vaga.md
        └── commands.py      # `buscar`
```

As regras do M1 continuam valendo (seção 3.1 do M1): sem comentários, funções em vez de classes de serviço, tipagem de parâmetros e retornos.

## 4. Config (`config.md`): campos novos

```yaml
llm:
  provedores: [claude, opencode]   # ordem de tentativa; palavras-chave é sempre o último recurso
  claude:
    modelo: sonnet
  opencode:
    modelo: <provedor/modelo>       # a definir depois do mapeamento
  timeout_segundos: 180

regras:
  analise_llm_max_vagas: 30         # quantas vagas (após o pré-score) vão para o LLM por execução
```

- Os modelos Pydantic do M1 ganham `Llm`, `LlmClaude` e `LlmOpencode`, e `Regras` ganha `analise_llm_max_vagas` (≥ 1). Continua com `extra="forbid"` e erro com linha.
- O `validar` passa a mostrar os provedores de LLM e se cada um está disponível (`shutil.which`).

## 5. Banco (`data/autoapply.db`, `sqlite3` da stdlib)

```sql
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,            -- data-job-id do LinkedIn
  title TEXT NOT NULL,
  company TEXT NOT NULL,
  location TEXT NOT NULL,
  workplace TEXT,                 -- "Remoto", "Tempo integral"...
  posted TEXT,                    -- texto relativo, ex.: "há 1 dia"
  description TEXT,
  url TEXT NOT NULL,              -- https://www.linkedin.com/jobs/view/<id>/
  search_term TEXT NOT NULL,
  status TEXT NOT NULL,           -- JobStatus
  discard_reason TEXT,
  collected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
  job_id TEXT PRIMARY KEY REFERENCES jobs(id),
  resume_name TEXT NOT NULL,
  score INTEGER NOT NULL,
  pre_score INTEGER NOT NULL,
  summary TEXT NOT NULL,
  requirements TEXT NOT NULL,     -- JSON (lista)
  keywords TEXT NOT NULL,         -- JSON (lista)
  gap TEXT NOT NULL,              -- JSON (lista)
  analyzer TEXT NOT NULL,         -- claude | opencode | palavras_chave
  model TEXT,
  analyzed_at TEXT NOT NULL
);
```

- `JobStatus` (StrEnum), seguindo o ciclo do PRD: `coletada`, `ignorada` (filtro), `avaliada`, `aguardando_cv`. Os outros estados (`aprovada`, `aplicada`, `falhou`, `pendente_pergunta`) chegam no M3.
- Sem duplicar: o `id` é a chave. Uma vaga já existente nunca é reaberta nem recoletada (NFR-004).
- Sem ORM e sem "Repository": `store.py` tem funções como `insert_job(connection, job)`, `find_known_ids(connection, ids)`, `update_status(...)`.

## 6. Coleta (`coletar`)

1. Abre o navegador (headless por padrão; `--visivel` mostra a janela) e chama `ensure_session`. Se der `SessionExpired`, `CheckpointDetected` ou `UnknownPageState`, para e salva o dump em `debug/` (M1).
2. **Termos:** a união das `buscas` de todos os currículos, sem repetir (hoje são 13).
3. **URL** por termo (`search_url.py`, função pura): os filtros da seção 2, com `f_TPR` vindo de `busca.publicadas_ha_no_maximo_dias` e `f_E` vindo de `busca.niveis` (`junior` → 2; `pleno` → 3 e 4).
4. **Lista:** rola a lista até carregar os 25 cards e lê de cada um `JobCard(id, title, company, location)`.
5. **Filtros antes de abrir a vaga**, sobre o card (`filters.py`, funções puras):
   - ID já no banco → pula (não conta como nova);
   - `termos_bloqueados_no_titulo`, `empresas_bloqueadas` → `ignorada`, com o motivo.
   - O local **não** é filtrado: vaga remota de fora do Brasil segue normalmente e o local aparece no `vaga.md`.
6. **Detalhe:** clica no card, espera o painel com `currentJobId=<id>` e lê descrição, modalidade, data e o botão Easy Apply. Se não tiver "Candidatura simplificada" → `ignorada`. Se `palavras_bloqueadas` aparecerem na descrição → `ignorada`.
7. Grava como `coletada`.
8. **Ritmo (NFR-001):** espera aleatória de 3 a 15 s entre ações (clique, troca de termo). A espera é uma função injetável para os testes rodarem sem esperar.
9. **Falhas:** a cada navegação roda `detect_page_state`. Um checkpoint interrompe tudo com dump. Se uma vaga não carregar, salva o dump e segue para a próxima (NFR-005).
10. **Terminal:** barra de progresso por termo e, no fim, a tabela "termo · encontradas · novas · ignoradas".

## 7. Avaliação

### 7.1 Pipeline (`evaluation.py`)

1. Pega as vagas `coletada`.
2. **Pré-score por palavras-chave** (`keywords.py`, funções puras), para cada currículo:
   - o vocabulário é a união das chaves de `experiencia_anos` com uma lista fixa de tecnologias em `keywords.py`;
   - termos da vaga = termos do vocabulário que aparecem na descrição (sem acento, minúsculas, com fronteira de palavra);
   - pré-score = % dos termos da vaga que aparecem no texto do currículo;
   - o melhor currículo é o de maior pré-score (empate → o padrão).
3. Ordena pelo pré-score e manda as `analise_llm_max_vagas` melhores para o LLM. As outras recebem a **análise simplificada** (7.4) e também ficam `avaliada`.
4. Grava em `analyses`. Vaga já avaliada não é reanalisada.

### 7.2 Análise por LLM (`prompt.py`)

- **Uma chamada por vaga**, com os 3 currículos. O LLM escolhe o melhor, o que evita 3 chamadas por vaga.
- **Entrada:** descrição da vaga; texto de cada currículo com e-mail e telefone mascarados (`mask_sensitive_data` do M1); níveis e anos de experiência do `config.md`. Endereço e documentos não são enviados (PRD, Dados e privacidade).
- **Instruções:** responder em português, usar só o que está no currículo, nunca inventar experiência e listar no gap o que a vaga pede e o currículo não mostra.
- **Saída (JSON Schema):** `curriculo` (um dos nomes), `score` (0 a 100), `resumo` (justificativa em 2 ou 3 frases), `requisitos[]`, `palavras_chave[]`, `gap[]`.
- O sistema confere se `curriculo` existe; se não existir, trata como falha da chamada.

### 7.3 Provedores (`providers.py`)

| Provedor | Disponível quando | Chamada |
|---|---|---|
| `claude` | `claude` no PATH | `claude -p --output-format json --json-schema <schema> --model <llm.claude.modelo> --tools "" --no-session-persistence`, prompt no stdin; lê `structured_output` |
| `opencode` | `opencode` no PATH | `opencode run --model <llm.opencode.modelo> ...`, com o prompt pedindo só JSON; extrai e valida o JSON da saída. **Flags exatas a confirmar** depois do mapeamento |
| `palavras_chave` | sempre | análise simplificada (7.4) |

- A ordem vem de `llm.provedores`. A disponibilidade é verificada uma vez por execução, e o terminal mostra qual provedor foi usado.
- **Falha numa vaga** (timeout, `is_error`, JSON inválido): tenta de novo uma vez e depois passa para o próximo provedor *naquela vaga*. Três falhas seguidas do mesmo provedor o desligam pelo resto da execução.

### 7.4 Análise simplificada (sem LLM)

- `score` = pré-score; `requisitos` = `palavras_chave` = termos da vaga; `gap` = termos da vaga que faltam no currículo; `resumo` = "Análise simplificada por palavras-chave (sem LLM)".
- O `vaga.md` e o terminal mostram o aviso "análise simplificada".

## 8. Modo busca (`buscar`)

1. Roda a coleta (seção 6) e a avaliação (seção 7).
2. Escolhe as `regras.modo_busca_quantidade` (10) vagas `avaliada` de maior score, sem score mínimo. Quando o score fica abaixo de `regras.score_minimo`, o `vaga.md` mostra um aviso.
3. Para cada uma, cria `vagas/<AAAA-MM-DD>-<empresa>-<cargo>/vaga.md` (slug sem acento, minúsculo, até 60 caracteres; se o nome já existir, acrescenta o ID da vaga) e muda o status para `aguardando_cv`.
4. Vagas `aguardando_cv` não entram de novo nas próximas buscas (História 3.1).
5. `vagas/` vai para o `.gitignore`.

`vaga.md`:

```markdown
# <Cargo> — <Empresa>

- **Link:** https://www.linkedin.com/jobs/view/<id>/
- **Local:** <local> · <modalidade> · <data>
- **Score:** 82/100 · **Currículo sugerido:** Back-end .NET (`cv_base/dotnet.docx`)
- **Análise:** claude (sonnet)

## Resumo
## Requisitos
## Palavras-chave
## Gap (a vaga pede e o currículo não mostra)
## Descrição completa

---
Salve o currículo adaptado nesta pasta como `cv.docx` ou `cv.pdf`.
```

## 9. CLI

```
autoapply coletar [--visivel]          # só coleta e grava no banco
autoapply buscar [--visivel]           # coleta + avaliação + 10 pastas
autoapply vagas [--status <status>]    # tabela das vagas no banco
```

Códigos de saída: `0` ok; `1` sessão expirada; `2` config inválido; `3` checkpoint ou página inesperada (mesmos do M1).

## 10. Testes

| Área | Como |
|---|---|
| URL de busca | Função pura: filtros, codificação dos termos, níveis |
| Parsing | HTML mínimo escrito à mão em `tests/fixtures/pages/` (lista e painel), com os seletores da seção 2 |
| Filtros | Função pura: título, empresa e palavras |
| Banco | SQLite em `tmp_path`: inserção, IDs conhecidos, status e análise |
| Coleta | Chromium headless com rotas falsas e a trava de rede do M1; espera injetada (zero); checkpoint no meio interrompe; vaga sem Easy Apply é ignorada; segunda execução não duplica |
| Pré-score e análise simplificada | Função pura com textos curtos |
| Provedores | Executáveis falsos `claude`/`opencode` (scripts em `tmp_path` no PATH) que devolvem JSON válido, inválido, erro ou demoram: sucesso, retry, fallback para o próximo e para palavras-chave |
| Modo busca | Top N, nomes de pasta, conteúdo do `vaga.md`, `aguardando_cv` não volta |

O LinkedIn real e os LLMs reais **nunca** são chamados nos testes. Eles são validados à mão no critério de pronto.

## 11. Tarefas

- [x] **T1 — Config do LLM.** Campos `llm` e `regras.analise_llm_max_vagas`, com validação e exibição no `validar`.
- [ ] **T2 — Banco.** `shared/database.py` e `jobs/store.py`.
- [ ] **T3 — URL, parsing e filtros.** Funções puras com fixtures.
- [ ] **T4 — Coletor + `coletar`.** Playwright com rotas, ritmo, dump e tabela final. *Pronto:* testes passam e uma coleta real grava vagas.
- [ ] **T5 — Pré-score e análise simplificada.**
- [ ] **T6 — Provedores LLM.** claude CLI, opencode CLI, retry e fallback. *Pronto:* testes com executáveis falsos e uma análise real com `claude`.
- [ ] **T7 — Avaliação.** Pipeline completo gravando `analyses`.
- [ ] **T8 — Modo busca + `buscar` e `vagas`.** *Pronto:* o critério de pronto da seção 1 com a sessão real.
- [ ] **T9 — Fechamento.** README e PRD.

Ordem: T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9. TDD, com as seams combinadas antes, e um commit por tarefa na `develop`.

## 12. Decisões

Confirmadas em 2026-10-21:

1. Match: tenta LLM e cai para palavras-chave. Ordem `claude` (CLI `claude -p`) → `opencode` (CLI `opencode run`) → palavras-chave.
2. Modelo do Claude configurável, com padrão `sonnet`.
3. Coleta pela tela de busca, 1 página (~25) por termo, abrindo só vagas novas.
4. Pré-score por palavras-chave; as 30 melhores (configurável) vão para o LLM.
5. Comandos `coletar`, `buscar` e `vagas`.
6. SQLite em `data/autoapply.db` com `sqlite3` da stdlib.
7. Currículos sem campos de idioma e área (ajustar o critério da História 1.2 no PRD).
8. Níveis → `f_E`: `junior` → 2, `pleno` → 3 e 4. As vagas sênior que vierem junto são cortadas pelos termos bloqueados no título.
9. Top 10 do modo busca sem score mínimo, com aviso no `vaga.md` abaixo de `regras.score_minimo`.
10. Vagas remotas com local fora do Brasil são mantidas.

**A confirmar:**

1. **OpenCode:** mapear o binário e a configuração para dentro do ai-jail e definir `llm.opencode.modelo`. Até lá, o provedor fica implementado e testado com executável falso, mas não validado de verdade.
