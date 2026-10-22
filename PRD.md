# PRD: LinkedIn Auto-Apply

**Status:** MVP concluído (M4 concluído)
**Autor:** Ze fernando
**Criado em:** 2026-10-21
**Atualizado em:** 2026-10-21
**Versão:** 0.7

---

## Resumo executivo

**Em uma frase:** ferramenta pessoal que busca vagas no LinkedIn, escolhe o melhor currículo para cada uma e se candidata sozinha pelo Easy Apply. Ela também tem um modo para preparar candidaturas com cuidado, à mão.

**Visão geral:**

Hoje, candidatar-se a vagas no LinkedIn é repetitivo. É preciso ler cada vaga, decidir se vale a pena, escolher o currículo e preencher o mesmo formulário várias vezes com nome, telefone, pretensão salarial e anos de experiência. A ferramenta automatiza esse ciclo a partir de um arquivo `config.md`, que guarda os dados pessoais e as respostas padrão.

A ferramenta tem dois modos:

- **Modo busca:** traz as 10 melhores vagas, cada uma com a descrição completa, os requisitos e palavras-chave e o que falta no seu currículo atual em relação à vaga. Você adapta o currículo de cada vaga e o sistema faz a candidatura usando o currículo adaptado.
- **Modo normal:** busca as vagas, calcula o match com os seus currículos e aplica sozinho, com o currículo de maior match. O currículo pode ser ajustado por IA antes do envio. Há um limite diário de candidaturas.

**Resumo:**

- **Usuário:** o dono da ferramenta, procurando emprego
- **Problema resolvido:** horas gastas lendo vagas e preenchendo formulários repetidos
- **Métrica principal:** candidaturas relevantes enviadas por semana sem intervenção manual
- **Entrega alvo:** MVP em ~4 semanas

---

## Declaração do problema

### O problema

Aplicar para muitas vagas toma tempo. Aplicar para poucas reduz as chances. Mandar o mesmo currículo genérico para todas as vagas diminui a taxa de resposta.

### Situação atual

Hoje o processo é todo manual. Você busca no LinkedIn, abre cada vaga, decide se tem match, escolhe o currículo, adapta o currículo quando dá tempo e preenche o Easy Apply à mão.

### Impacto

- Cerca de 5 a 10 minutos por candidatura simples. Vagas boas e recentes se perdem porque não há tempo de aplicar no mesmo dia.
- As vagas mais importantes não recebem um currículo adaptado.

---

## Objetivos

### Objetivos do usuário

1. **Volume com qualidade:** aplicar automaticamente só em vagas com match real.
2. **Foco nas vagas-chave:** receber uma lista curta (10 vagas) com tudo o que é preciso para adaptar o currículo.
3. **Zero digitação repetida:** dados pessoais e respostas ficam num único `config.md`.
4. **Conta segura:** não ser bloqueado pelo LinkedIn.

### Não-objetivos

- Não é um produto para terceiros nem para várias contas.
- Não aplica em sites externos (Gupy, Workday etc.) na v1.
- Não envia mensagens a recrutadores.

---

## Persona

**Candidato(a) usando a própria conta.** Tem conhecimento técnico médio ou alto, roda a ferramenta pelo terminal e mantém de 2 a 4 currículos base (por área ou idioma). Quer volume no dia a dia e cuidado extra nas vagas que mais interessam.

---

## Histórias de usuário e requisitos

### Épico 1: Configuração (`config.md`)

#### História 1.1: Dados pessoais e respostas padrão (P0)

```
Como candidato,
quero manter meus dados e respostas num único arquivo config.md,
para que o sistema preencha qualquer formulário sem me perguntar de novo.
```

**Critérios de aceite:**

- [x] O `config.md` contém: nome, e-mail, telefone, cidade, LinkedIn, GitHub e portfólio, pretensão salarial, disponibilidade, modelo de trabalho aceito, idiomas e anos de experiência por tecnologia.
- [x] O `config.md` contém uma seção de **respostas padrão** (pergunta → resposta), por exemplo: "Possui CNH?" → "Sim".
- [x] O `config.md` contém uma seção de **buscas**: palavras-chave, localização, remoto/híbrido/presencial, senioridade e data de publicação. Padrão: **somente vagas remotas, localização "Brasil"** (todo o país).
- [x] O `config.md` contém uma **resposta genérica** para perguntas de texto livre (ex.: "Por que quer trabalhar aqui?").
- [x] O `config.md` contém uma seção de **regras**: empresas e palavras bloqueadas, score mínimo, limite diário de candidaturas.
- [x] Dado um `config.md` com erro de formato, quando executo qualquer comando, então o sistema aponta a linha e o campo inválidos e não executa. *(No M1, pelo `autoapply validar`.)*

#### História 1.2: Currículos base (P0)

```
Como candidato,
quero cadastrar vários currículos base (ex.: "Backend PT", "Dados EN"),
para que o sistema use o mais adequado para cada vaga.
```

**Critérios de aceite:**

- [ ] Os currículos ficam na pasta `cv_base/` e cada um tem nome, idioma e área. O currículo padrão é a v2 gerada na análise do CV original (ver M0 no cronograma). *(M1: pasta, nome e padrão prontos; idioma e área ainda não são campos do `config.md`.)* *(M1: `cv_base/` e nome prontos; idioma e área ainda não são campos do `config.md`.)*
- [x] O sistema aceita `.docx` e `.pdf` e extrai o texto para usar no match.
- [x] Edge case: se o PDF é escaneado (sem texto), o sistema avisa e não usa esse currículo.

### Épico 2: Coleta de vagas

#### História 2.1: Buscar vagas Easy Apply (P0)

```
Como candidato,
quero que o sistema execute minhas buscas e salve as vagas encontradas,
para não precisar navegar no LinkedIn manualmente.
```

**Critérios de aceite:**

- [x] O sistema coleta só vagas com **Easy Apply**.
- [x] Para cada vaga, salva: ID, título, empresa, local, modalidade, data, descrição completa e link.
- [x] Dado que uma vaga já foi coletada ou aplicada, quando ela aparece de novo, então ela não é duplicada.
- [x] Vagas de empresas ou com palavras bloqueadas são descartadas.

### Épico 3: Modo busca (curadoria manual)

#### História 3.1: Top 10 vagas com análise (P0)

```
Como candidato,
quero receber as 10 vagas de maior match com uma análise de cada uma,
para adaptar meu currículo com precisão.
```

**Critérios de aceite:**

- [x] O comando `search` gera uma pasta por vaga em `vagas/<data>-<empresa>-<cargo>/`.
- [x] Cada pasta contém um `vaga.md` com: descrição completa, link, requisitos e palavras-chave extraídos, currículo base sugerido, score e **gap** (o que a vaga pede e o currículo não mostra).
- [x] As 10 vagas são ordenadas por score e ficam com o status `aguardando_cv`.
- [x] Vagas que já estão em `aguardando_cv` não entram de novo nas próximas buscas.

#### História 3.2: Aplicar com o currículo adaptado (P0)

```
Como candidato,
quero colocar meu currículo adaptado na pasta da vaga e mandar aplicar,
para que a candidatura use a minha versão.
```

**Critérios de aceite:**

- [x] Dado um `cv.docx` ou `cv.pdf` na pasta da vaga, quando executo `apply <job>` (ou `apply --ready`), então o sistema faz o Easy Apply com esse arquivo.
- [x] Na pasta da vaga posso incluir **informações específicas da vaga**, como respostas a perguntas daquela vaga, pretensão salarial diferente ou uma mensagem. Esses valores têm prioridade sobre o `config.md`.
- [x] Sem currículo na pasta, a vaga não é aplicada e continua `aguardando_cv`.

### Épico 4: Modo normal (automático)

#### História 4.1: Escolher o melhor currículo (P0)

```
Como candidato,
quero que o sistema compare cada vaga com todos os meus currículos,
para que ele use o de maior match.
```

**Critérios de aceite:**

- [x] Cada vaga recebe um score de 0 a 100 para cada currículo base, e o sistema escolhe o maior.
- [x] Vagas com score abaixo do mínimo do `config.md` são ignoradas e o motivo fica registrado.
- [x] Cada decisão tem uma justificativa curta: requisitos atendidos e requisitos faltantes.

#### História 4.2: Ajuste automático do currículo (P1)

```
Como candidato,
quero que o sistema ajuste o currículo escolhido para a vaga antes de enviar,
para aumentar a aderência sem que eu precise intervir.
```

**Critérios de aceite:**

- [x] O ajuste só **reordena, enfatiza e reescreve** o que já está no currículo base: resumo, ordem das skills e destaque de experiências relevantes. *(M4: reescreve o resumo e reordena os bullets de cada experiência e as competências; cargos, empresas, datas e o texto dos bullets não mudam.)*
- [x] O ajuste **nunca inventa** experiência, skill, cargo, empresa ou certificação. Uma checagem compara o resultado com o currículo base e bloqueia o envio se aparecer algo novo.
- [x] Cada vaga tem uma cópia do currículo ajustado (PDF), guardada para consulta. *(M4: em `curriculos-enviados/`.)*
- [x] O ajuste pode ser ligado ou desligado no `config.md`. Desligado, o sistema envia o currículo base escolhido.

#### História 4.3: Candidatura automática com limite (P0)

```
Como candidato,
quero que o sistema aplique sozinho nas vagas aprovadas, respeitando um limite diário,
para ganhar volume sem arriscar a conta.
```

**Critérios de aceite:**

- [x] O sistema preenche o Easy Apply com dados do `config.md` e envia o currículo escolhido.
- [x] Dado que o limite diário foi atingido, nenhuma nova candidatura é enviada naquele dia.
- [x] Dado que o formulário traz uma pergunta de **texto livre** sem resposta específica, o sistema usa a resposta genérica do `config.md`.
- [x] Dado que o formulário traz uma pergunta **objetiva** (sim/não, número, seleção) sem resposta no `config.md`, a vaga **não é enviada**, a pergunta vai para uma lista de pendentes e a vaga fica para a próxima execução, depois que você responder.
- [x] Antes de enviar, o sistema confirma que ainda não aplicou nessa vaga.
- [x] Ao final, o sistema mostra um relatório com as vagas aplicadas, ignoradas, com falha e as perguntas pendentes.

Com `--auto`, `apply` e `run` enviam sem supervisão. Sem a flag, cada envio pede `Enviar? [y/N]` no terminal. Perguntas de experiência são respondidas pelos anos de `experiencia_anos` das tecnologias citadas na pergunta.

### Épico 5: Sessão e segurança

#### História 5.1: Login persistente (P0)

```
Como candidato,
quero fazer login uma vez e reaproveitar a sessão,
para reduzir o risco de bloqueio e não digitar a senha sempre.
```

**Critérios de aceite:**

- [x] O primeiro login é manual, numa janela do navegador. Depois disso, a sessão é reaproveitada.
- [x] Dado que o LinkedIn pede verificação (CAPTCHA ou código), a execução **para** e avisa. O sistema nunca tenta resolver a verificação sozinho.

#### História 5.2: Modo simulação (P1)

```
Como candidato,
quero rodar tudo sem enviar nada,
para testar as configurações com segurança.
```

**Critérios de aceite:**

- [x] A flag `--simulate` percorre o formulário até a última etapa e não clica em "Enviar".

### Épico 6: Execução e acompanhamento

#### História 6.1: Execução manual com logs ao vivo (P0)

```
Como candidato,
quero rodar a ferramenta quando eu quiser e acompanhar tudo no terminal,
para ver em tempo real o que está sendo feito.
```

**Critérios de aceite:**

- [x] A ferramenta só roda quando você executa o comando. Não há agendamento.
- [ ] O terminal mostra, com **Rich**, painéis e barras de progresso por etapa (login, coleta, match, aplicação). *(M3: indicador de status por etapa e tabelas; ainda sem barras de progresso.)*
- [x] Cada vaga gera uma linha colorida com status, empresa, cargo, score e currículo usado. Exemplo: `✔ Aplicada · Empresa X · Dev Python Pleno · score 82 · cv_base/padrao.docx`.
- [ ] Mostra contadores ao vivo: aplicadas, ignoradas, falhas, pendentes e quanto resta do limite diário. *(M3: aplicadas, pendentes, falhas e limite ao vivo; as ignoradas aparecem em linhas antes das candidaturas.)*
- [x] No fim, mostra uma tabela-resumo da execução.
- [x] O mesmo log é gravado em arquivo detalhado (com data e hora) em `logs/`, para consulta depois.
- [x] A flag `--verbose` mostra cada passo do formulário (campo preenchido, resposta usada e de onde veio a resposta).

### Requisitos funcionais

| ID     | Descrição                                                                      | Prioridade |
| ------ | ------------------------------------------------------------------------------ | ---------- |
| FR-001 | Ler e validar o `config.md` (dados, respostas, buscas, regras)                 | P0         |
| FR-002 | Cadastrar currículos base e extrair o texto                                    | P0         |
| FR-003 | Login com sessão persistente e detecção de verificação                         | P0         |
| FR-004 | Coletar vagas Easy Apply com deduplicação                                      | P0         |
| FR-005 | Calcular o score de match vaga × currículo, com justificativa                  | P0         |
| FR-006 | Modo busca: top 10 vagas com pasta, análise e gap                              | P0         |
| FR-007 | Aplicar com o CV adaptado manualmente e com as informações específicas da vaga | P0         |
| FR-008 | Modo normal: aplicação automática com limite diário                            | P0         |
| FR-009 | Lista de perguntas pendentes                                                   | P0         |
| FR-010 | Histórico e relatório das candidaturas                                         | P0         |
| FR-011 | Ajuste automático do currículo por IA, sem inventar informação                 | P1         |
| FR-012 | Modo simulação                                                                 | P1         |
| FR-013 | Execução manual com logs ao vivo (Rich) e log em arquivo                       | P0         |

### Requisitos não funcionais

| ID      | Categoria          | Descrição                                                       | Meta                                               |
| ------- | ------------------ | --------------------------------------------------------------- | -------------------------------------------------- |
| NFR-001 | Segurança da conta | Intervalo aleatório entre ações                                 | 3 a 15 s na coleta; 2 a 6 s entre etapas do formulário; 20 a 60 s entre candidaturas |
| NFR-002 | Segurança da conta | Limite diário de candidaturas (configurável)                    | Padrão: 15/dia                                     |
| NFR-003 | Privacidade        | Senha só no `.env`; `config.md`, currículos e banco fora do git | Nenhum dado pessoal no repositório                 |
| NFR-004 | Confiabilidade     | Execução retomável e sem candidatura duplicada                  | 0 duplicadas                                       |
| NFR-005 | Depuração          | Falha salva screenshot e HTML da página                         | 100% das falhas                                    |

---

## Métricas de sucesso

**Métrica principal:** candidaturas relevantes enviadas por semana sem intervenção manual.

| Métrica                                                                      | Meta                        |
| ---------------------------------------------------------------------------- | --------------------------- |
| Taxa de conclusão do Easy Apply (enviadas ÷ tentadas)                        | ≥ 80%                       |
| Candidaturas duplicadas                                                      | 0                           |
| Bloqueios ou restrições da conta                                             | 0                           |
| Concordância com o match (amostra revisada por você)                         | ≥ 80%                       |
| Tempo para preparar as 10 vagas do modo busca (sem contar a adaptação do CV) | < 5 min                     |
| Taxa de resposta das empresas, modo busca × modo normal                      | Acompanhar (sem meta na v1) |

---

## Escopo

### Dentro do escopo (MVP)

- `config.md` com dados, respostas, buscas e regras
- Vários currículos base
- Coleta só de vagas Easy Apply
- Modo busca (top 10, análise, gap, aplicação com o CV adaptado)
- Modo normal (match, escolha do CV, aplicação automática com limite)
- Ajuste automático do CV por IA, com proteção contra informações inventadas
- Perguntas pendentes e relatório

### Fora do escopo

- Sites externos (ATS), porque são muito mais frágeis e cada site é diferente
- Carta de apresentação gerada
- Interface web (o uso é pelo terminal)
- Várias contas

### Futuro

- Candidatura em ATS populares (Gupy primeiro)
- Aprender com as vagas que você aprova ou recusa
- Notificação no Telegram ou WhatsApp
- Acompanhar as respostas das empresas

---

## Considerações técnicas

### Arquitetura (proposta)

```
config.md ─┐
cv_base/ ──┼─► [Coleta] ─► banco local ─► [Match] ─┬─► Modo busca: vagas/<pasta>/vaga.md ─► (você adapta) ─┐
.env ──────┘    (navegador)                         └─► Modo normal: [Ajuste de CV] ─────────────────────────┴─► [Easy Apply] ─► relatório
```

- **Linguagem:** Python 3.15+
- **Navegador:** Playwright, com a sessão salva em disco
- **Banco:** SQLite (vagas, matches, candidaturas, status)
- **Match:** primeiro filtros por regras e pré-score por palavras-chave (baratos), depois LLM nas melhores vagas pelo CLI do Claude Code (`claude -p`) ou do OpenCode (`opencode run`), com retry, fallback entre provedores e, por último, análise simplificada por palavras-chave
- **Ajuste de CV:** LLM pelos mesmos provedores do match; o LLM só devolve um plano (resumo novo e ordens), e uma checagem bloqueia o que não está no currículo base
- **Geração de PDF do CV ajustado:** template HTML que copia o visual do `.docx`, gerado em PDF pelo Chromium headless
- **CLI:** comandos `validate`, `login`, `session`, `collect`, `search`, `jobs`, `apply`, `run`, `pending` e `report`, com `-h` e `--tutorial`. Execução sempre manual.
- **Terminal:** Rich (painéis, barras de progresso, tabelas e log colorido)

### Ciclo de vida da vaga

`coletada → avaliada → (aguardando_cv | aprovada | ignorada) → aplicada | falhou | pendente_pergunta`

No M2, a vaga cortada pelos filtros já na coleta (título, empresa, palavras ou sem Easy Apply) é gravada direto como `ignorada`, com o motivo.

No M3, o `aprovada` não é usado: o `run` escolhe e aplica na mesma execução. Vaga que o LinkedIn já mostra como candidatada vira `aplicada` sem contar no limite. Cada tentativa (`aplicada`, `ja_aplicada`, `pendente`, `falhou`) fica no histórico do banco.

### Dados e privacidade

- O `config.md`, os currículos e o banco ficam só na máquina local e no `.gitignore`. O repositório traz só o `config.example.md`, com dados fictícios.
- Só o texto da vaga e do currículo, os níveis e os anos de experiência são enviados ao LLM. Telefone e e-mail são mascarados antes do envio; endereço e documentos não são enviados.

---

## Fluxos

**Modo busca**

1. `search` → o sistema coleta e pontua as vagas e cria 10 pastas em `vagas/`
2. Você lê o `vaga.md`, adapta o currículo e salva como `cv.docx` (ou `cv.pdf`) na pasta. Se quiser, preenche as informações específicas da vaga.
3. `apply --ready` → o sistema aplica nas vagas que já têm currículo na pasta

**Modo normal**

1. `run` → coleta → match → escolha do CV → ajuste (se ligado) → Easy Apply, até o limite diário
2. O sistema mostra o resumo da execução e as perguntas pendentes (`pending`); com `--interactive`, pergunta no terminal na hora
3. Você responde as pendentes no `config.md`, e a próxima execução retoma essas vagas
4. `report` mostra o histórico do período e exporta CSV

---

## Cronograma

| Marco             | Entrega                                                                        | Semana |
| ----------------- | ------------------------------------------------------------------------------ | ------ |
| M0: Currículo ✔   | Análise do `cv.docx` original, pesquisa de vagas remotas no Brasil, recomendação de focos e **v2 melhorada** em `cv_base/` como padrão | 0 (antes de implementar) |
| M1: Base ✔        | `config.md`, currículos, login persistente (`validate`, `login`, `session`) | 1      |
| M2: Leitura ✔     | Coleta + match + **modo busca** completo (`collect`, `search`, `jobs`)           | 2      |
| M3: Aplicação ✔   | Easy Apply (com CV adaptado e no modo normal) + limite + pendentes + simulação | 3      |
| M4: Ajuste por IA ✔ | Ajuste automático do CV com verificação + relatório                          | 4      |

---

## Riscos e mitigação

| Risco                                                                         | Impacto | Probabilidade | Mitigação                                                                                                             |
| ----------------------------------------------------------------------------- | ------- | ------------- | --------------------------------------------------------------------------------------------------------------------- |
| O LinkedIn restringe ou bloqueia a conta (os Termos de Uso proíbem automação) | Alto    | Média         | Volume baixo, intervalos aleatórios, sessão reaproveitada, parar quando houver verificação, limite diário conservador |
| O layout do LinkedIn muda e quebra a coleta ou o formulário                   | Alto    | Alta          | Seletores centralizados, testes com HTML salvo, screenshot quando falhar                                              |
| A IA inventa informação no currículo                                          | Alto    | Média         | Ajuste restrito ao conteúdo do CV base e verificação automática antes do envio                                        |
| Resposta errada num formulário (ex.: autorização de trabalho)                 | Médio   | Média         | Nunca chutar: pergunta desconhecida vira pendente                                                                     |
| Match ruim gera candidaturas irrelevantes                                     | Médio   | Média         | Score mínimo configurável, justificativa registrada e revisão periódica                                               |
| Custo de LLM                                                                  | Baixo   | Baixa         | Filtros por regra antes e cache por vaga                                                                              |

---

## Premissas

- Você aceita o risco de usar automação na própria conta do LinkedIn.
- A ferramenta roda na sua máquina, com o navegador disponível.
- Você tem o CLI do Claude Code (`claude`) ou do OpenCode (`opencode`) instalado e logado para o match e o ajuste do CV; sem nenhum, o match cai nas palavras-chave e o ajuste é descartado.

---

## Perguntas em aberto

- [x] **Quais buscas iniciais?** Só vagas remotas, em todo o Brasil. Os cargos e palavras-chave saem da análise do CV base (item abaixo).
- [x] **Quantos currículos base e em quais focos?** Recomendação após a análise do CV (M0): 2 currículos, nível Júnior/Pleno. **Decidido: 3 currículos** (`cv_base/dotnet.docx` padrão, `automacao.docx` e `fullstack.docx`).
  1. **Back-end .NET (C#)** — padrão, `cv_base/dotnet.docx`. Buscas: "Desenvolvedor .NET", "Desenvolvedor C#", "Back-end .NET", "ASP.NET Core".
  2. **Automação e integrações** (Python, n8n, APIs, bots) — a criar a partir da v2. Buscas: "Desenvolvedor de Automação", "RPA", "n8n", "Desenvolvedor Python".
  3. **Full Stack TypeScript** — `cv_base/fullstack.docx`, criado junto com os outros dois.
- [x] **Formato do CV ajustado:** template HTML próprio, com o visual do `.docx`, gerado em PDF pelo Chromium (decidido no M4).
- [x] **Score mínimo e limite diário iniciais:** score 70 e 15 candidaturas por dia (configuráveis).
- [x] **Perguntas de texto livre:** usar uma resposta genérica definida no `config.md`.
- [x] **Agendamento:** sem agendamento. Execução manual, com logs ao vivo no terminal (Épico 6).

---

## Glossário

- **Easy Apply:** candidatura simplificada feita dentro do LinkedIn.
- **CV base:** currículo original mantido por você.
- **CV adaptado:** versão que você edita à mão para uma vaga (modo busca).
- **CV ajustado:** versão gerada pela IA a partir do CV base (modo normal).
- **Gap:** requisitos da vaga que o currículo não evidencia.
- **Pendente:** pergunta de formulário sem resposta conhecida.

## Histórico de mudanças

| Versão | Data       | Mudança          |
| ------ | ---------- | ---------------- |
| 0.1    | 2026-10-21 | Rascunho inicial |
| 0.2    | 2026-10-21 | Busca padrão: remoto em todo o Brasil; resposta genérica para texto livre; formato do CV adiado; focos dos currículos a definir pela análise do CV base |
| 0.3    | 2026-10-21 | Score 70 e 15/dia; execução manual com logs Rich (Épico 6); currículos em `cv_base/` aceitando .docx; M0 = análise do CV e v2 antes da implementação |
| 0.4    | 2026-10-21 | M0 e M1 concluídos; 3 currículos base; critérios de aceite das Histórias 1.1, 1.2 e 5.1 atualizados |
| 0.5    | 2026-10-21 | M2 concluído; Histórias 2.1 e 3.1 atendidas; match por Claude Code ou OpenCode com fallback por palavras-chave; privacidade do envio ao LLM detalhada |
| 0.6    | 2026-10-22 | M3 concluído; candidatura pelo Easy Apply no modo busca e no modo normal, com limite, pendentes e simulação |
| 0.7    | 2026-10-22 | M4 concluído; História 4.2 atendida; formato do CV ajustado decidido (HTML → PDF); comando `report`; comandos e flags em inglês, `-h` e `--tutorial`; premissa do LLM corrigida para os CLIs |
