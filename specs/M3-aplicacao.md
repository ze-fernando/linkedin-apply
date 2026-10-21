# Spec técnica — M3: Aplicação

**Status:** Aprovado · **Atualizado:** 2026-10-21
**PRD:** [../PRD.md](../PRD.md) — História 3.2 (aplicar com o CV adaptado), Histórias 4.1 e 4.3 (modo normal), História 5.2 (simulação), Épico 6 (logs e resumo), FR-007, FR-008, FR-009, FR-012, NFR-001, NFR-002, NFR-004, NFR-005
**Base:** [M1-base.md](M1-base.md) (config, sessão, logs) e [M2-leitura.md](M2-leitura.md) (coleta, avaliação, modo busca)

## 1. Objetivo

1. Motor do Easy Apply: abrir o formulário, percorrer as etapas, responder cada campo com uma origem conhecida, anexar o currículo e enviar.
2. Modo busca: `aplicar <vaga>` e `aplicar --prontas` com o `cv.docx`/`cv.pdf` da pasta e o `respostas.md` da vaga.
3. Modo normal: `rodar` coleta, avalia e aplica sozinho, com o currículo de maior match, até o limite diário.
4. Perguntas pendentes (`pendentes`) e simulação (`--simular`).

**Pronto quando:**

- `aplicar --simular` e `rodar --simular` percorrem formulários reais até a revisão, sem enviar, e mostram as pendentes.
- Uma candidatura real é enviada pelo `aplicar`, numa vaga que **você** escolhe e só depois do seu ok explícito, e aparece como `aplicada`.
- Uma segunda execução nunca aplica de novo na mesma vaga (NFR-004).

**Fora do M3:** ajuste de CV por IA (História 4.2) e o comando `relatorio` (M4). O resumo no fim de cada execução entra no M3.

## 2. Ambiente e achados

Explorado em 2026-10-21 em 7 vagas reais do banco, sem nunca clicar em "Enviar": o script só clicava em botões de avançar e revisar e fechava com "Descartar".

- **Botão de abrir:** `button.jobs-apply-button` com "Candidatura simplificada", no painel da busca (`/jobs/search/?currentJobId=<id>` abre o painel da vaga direto).
- **Modal:** `[role=dialog].jobs-easy-apply-modal`. O título da etapa fica no `h3` ("Informações de contato", "Currículo", "Perguntas adicionais", "Revise sua candidatura"), e o texto acompanha o idioma da vaga ("Resume", "Additional Questions", "Información de contacto", "Currículum").
- **Botões do rodapé** (atributos estáveis, independentes do idioma):

| Ação | Seletor |
|---|---|
| Avançar | `button[data-easy-apply-next-button]` |
| Revisar | `button[data-live-test-easy-apply-review-button]` |
| Enviar | `button[data-live-test-easy-apply-submit-button]` |
| Fechar | `button[data-test-modal-close-btn]` |

- Fechar o modal abre "Salvar esta candidatura?" com **Descartar** e **Salvar**. O sistema sempre descarta.
- **Número de etapas varia:** de 1 (contato + currículo + Enviar na mesma tela) a 5 (contato, currículo, experiência, formação, revisão). As etapas de experiência e formação vêm preenchidas pelo perfil e só têm Editar/Remover.
- **Campos:** cada um fica num `.fb-dash-form-element`. O tipo sai do `id`:

| `id` contém | Tipo | Observação |
|---|---|---|
| `single-line-text-form-component` … `-numeric` | número | validação "inteiro de 0 a 99" ou "decimal maior que 0" |
| `single-line-text-form-component` … `-text` | texto curto | ex.: First name |
| `single-line-text-form-component` … `-phoneNumber-nationalNumber` | telefone | |
| `text-entity-list-form-component` … `-phoneNumber-country` | select do código do país | |
| `text-entity-list-form-component` … `-multipleChoice` | select | ex.: e-mail, nível de inglês, Yes/No |
| `radio-button-form-component` | rádio | `fieldset` com `legend`; cada opção tem `data-test-text-selectable-option__input="<texto>"` |

  O rótulo vem do `label[for=<id>]` ou do `legend`. A legenda do rádio termina com "Obrigatório", que deve ser removido. Não apareceram textarea, checkbox de pergunta nem autocompletar (cidade); eles são tratados na seção 7.4.
- **Erros de validação:** `.artdeco-inline-feedback--error` dentro do modal, por exemplo "Enter a whole number between 0 and 99".
- **Pré-preenchimento:** o LinkedIn reaproveita respostas suas de candidaturas anteriores. Muitos campos vêm preenchidos (inclusive rádios e números) e outros vêm vazios.
- **Os valores atuais não estão no HTML:** `value`, `checked` e a opção selecionada só existem como propriedades do DOM. Antes de ler uma etapa, um JS copia esses valores para `data-autoapply-value` (texto e opção selecionada) e `data-autoapply-checked` (rádio). O parsing é uma função pura sobre esse HTML.
- **Currículo:** a etapa lista os currículos já enviados ao LinkedIn (2 visíveis e "+3 currículos") e tem `input[type=file][name=file]` para upload.
- **Revisão:** `#follow-company-checkbox` ("Siga a empresa…") vem marcado.
- **Ainda não capturado** (será feito na T4 com dump, sem enviar nada além da candidatura autorizada): a tela depois de enviar e o painel de uma vaga já aplicada.

O HTML salvo da exploração está em `debug/explore-easy-apply/` e contém e-mail e telefone pré-preenchidos (no `.gitignore`). As fixtures dos testes são escritas à mão a partir dele, sem dados pessoais.

## 3. Estrutura (novos módulos)

```
src/autoapply/modules/
├── applying/
│   ├── models.py          # FormField, FieldKind, FieldAnswer, AnswerSource, ApplicationOutcome, PendingQuestion
│   ├── form_parsing.py    # HTML da etapa → campos (funções puras, selectolax)
│   ├── job_answers.py     # leitura do respostas.md da pasta da vaga
│   ├── answer_rules.py    # anos de experiência e pretensão em pt/en/es (funções puras)
│   ├── answering.py       # escolhe a resposta de cada campo e a opção certa (funções puras)
│   ├── easy_apply.py      # Playwright: abre o modal, percorre etapas, preenche, anexa, envia ou descarta
│   ├── store.py           # tentativas, pendentes, pastas, contagem do dia
│   ├── runner.py          # fila de vagas, limite diário, ritmo e resumo
│   └── commands.py        # `aplicar`, `rodar`, `pendentes`
└── search_mode/
    └── folders.py         # passa a gravar a pasta no banco e criar o respostas.md
```

As regras continuam: sem comentários, funções em vez de classes de serviço, tipagem de parâmetros e retornos.

## 4. Banco: mudanças

```sql
CREATE TABLE IF NOT EXISTS job_folders (
  job_id TEXT PRIMARY KEY REFERENCES jobs(id),
  folder TEXT NOT NULL              -- caminho da pasta em vagas/
);

CREATE TABLE IF NOT EXISTS application_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL REFERENCES jobs(id),
  mode TEXT NOT NULL,               -- busca | normal
  outcome TEXT NOT NULL,            -- aplicada | pendente | falhou
  reason TEXT,
  resume_file TEXT,
  attempted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL REFERENCES jobs(id),
  question TEXT NOT NULL,
  field_kind TEXT NOT NULL,
  options TEXT NOT NULL,            -- JSON (lista; vazia para texto e número)
  created_at TEXT NOT NULL
);
```

- `JobStatus` ganha `aplicada`, `falhou` e `pendente_pergunta`. O `aprovada` do PRD não é usado: o `rodar` escolhe e aplica na mesma execução.
- Tabelas novas com `CREATE TABLE IF NOT EXISTS`, sem alterar as existentes, então o banco do M2 continua valendo.
- `job_folders` é preenchida pelo `buscar`. Uma vaga com pasta pertence ao modo busca.
- **Limite do dia:** conta as tentativas `aplicada` com `attempted_at` no dia local de hoje, somando `aplicar` e `rodar`. O `--simular` não grava tentativa.
- **Pendentes:** ao tentar de novo uma vaga `pendente_pergunta`, as pendentes antigas dela são apagadas e regravadas se continuarem sem resposta.

## 5. Informações da vaga (`respostas.md`)

- O `buscar` passa a criar `vagas/<pasta>/respostas.md` com o cabeçalho e uma tabela vazia, no mesmo formato da seção "Respostas padrão" do `config.md` (pergunta → resposta). As pastas criadas no M2 não têm o arquivo, e ele é opcional.
- Duas linhas especiais: `pretensão salarial` (substitui a regra da seção 7.2) e `mensagem` (usada em campo de texto livre no lugar da resposta genérica).
- Respostas do `respostas.md` têm prioridade sobre o `config.md` (História 3.2). Erro de formato no arquivo → a vaga não é aplicada e o terminal mostra a linha, como no `validar`.

## 6. Motor do Easy Apply (`easy_apply.py`)

1. **Antes de abrir:** se a vaga já tem tentativa `aplicada` no banco, não abre (NFR-004).
2. Abre `/jobs/search/?currentJobId=<id>`, espera o painel e confere o botão "Candidatura simplificada". Sem o botão, ou com o painel indicando candidatura já enviada, a vaga vira `falhou` com o motivo; nesse último caso, vira `aplicada` sem contar no limite.
3. Clica no botão e espera o modal. Em cada etapa:
   1. Lê o HTML do modal e extrai os campos (seção 2).
   2. Resolve a resposta de cada campo (seção 7). Se algum campo obrigatório ficar sem resposta, junta as pendentes da etapa, descarta o rascunho e devolve `pendente`.
   3. Preenche só o que precisa mudar: número e texto com `fill`, select com `select_option` pelo texto da opção, rádio com clique no `label` da opção.
   4. **Etapa de currículo:** faz upload do arquivo escolhido pelo `input[type=file]`. A conferência de que ele aparece selecionado fica para a T5, com a captura real.
   5. Clica em Avançar ou Revisar. Se aparecer erro de validação, salva o dump e devolve `falhou` com o texto do erro.
4. **Revisão:** desmarca "Siga a empresa".
5. **Envio:** clica em Enviar. Com `--simular`, para aqui: não clica, descarta e devolve `simulada`.
6. **Confirmação:** espera a tela de sucesso (a capturar na T4). Sem confirmação em 15 s, salva o dump e devolve `falhou`; o status `falhou` impede reenvio automático e você confere à mão.
7. **Ritmo (NFR-001):** espera de 3 a 15 s entre etapas e de 1 a 3 min entre candidaturas. As duas esperas são injetáveis.
8. **Segurança:** o clique em Enviar só existe no passo 5 e só quando a execução não é simulação. Checkpoint ou login no meio interrompem tudo (`CheckpointDetected`/`SessionExpired`), como na coleta.

## 7. Respostas (`answering.py`, `answer_rules.py`)

### 7.1 Ordem de busca

Para cada campo, a primeira fonte que responder vence. A fonte vai para o log, e o `--verbose` mostra campo, resposta e origem (História 6.1):

1. **Contato:** e-mail, código do país, telefone, nome e sobrenome já vêm preenchidos e são mantidos. Se vierem vazios, saem do `perfil` (e-mail igual a `perfil.email`; país pelo "+55"; telefone = `ddd` + `celular` só com dígitos).
2. **`respostas.md` da vaga:** pergunta normalizada igual (mesma normalização do M1).
3. **`config.md`:** tabela "Respostas padrão", pela mesma comparação.
4. **Regras:** anos de experiência (7.2) e pretensão salarial (7.3).
5. **Pré-preenchido pelo LinkedIn:** mantém o valor e registra a origem "LinkedIn".
6. **Texto livre** (textarea): `mensagem` do `respostas.md` ou a resposta genérica do `config.md`.
7. **Nada disso:** campo obrigatório vira pendente; campo opcional fica como está.

### 7.2 Anos de experiência

- Padrões em português, inglês e espanhol, por exemplo "Quantos anos de experiência (você tem) com X", "How many years of (work) experience do you have with X", "Cuántos años de experiencia tienes con X".
- X é comparado às chaves de `experiencia_anos`, sem acento e sem diferença de maiúsculas, inteiro ("ASP.NET Core" não casa com "ASP.NET").
- X fora de `experiencia_anos` → pendente (só quando o campo não veio pré-preenchido; ver 7.1).

### 7.3 Pretensão salarial

- Reconhece "pretensão salarial", "expectativa salarial", "salary expectation", "pretensión salarial", "pretendido" e variações.
- **Nível:** sai do título da vaga (os termos de nível do M2: júnior/jr, pleno); se o título cita os dois, usa pleno; sem nível no título, usa `pretensao.padrao_nivel`.
- **Contrato:** PJ quando a pergunta cita PJ; senão CLT. O valor é o `formulario` da faixa.
- Pergunta com outra moeda (USD, dólar, dollar, euro, EUR) → pendente.

### 7.4 Escolha da opção (select e rádio)

- Compara a resposta com o texto de cada opção, normalizado.
- Sim/não entre idiomas: "sim", "yes", "sí"/"si" e "não", "no".
- Nenhuma opção casa → pendente, guardando as opções do formulário.
- **Campo numérico** com resposta que não é número → pendente.
- **Tipo desconhecido** (autocompletar, checkbox de pergunta, upload de outro documento): se obrigatório, a vaga vira `falhou` com o motivo e o dump em `debug/`, e o rascunho é descartado; se opcional, fica em branco.

## 8. Comandos

### 8.1 `aplicar` (modo busca)

```
autoapply aplicar <vaga> [--simular] [--visivel]   # <vaga> = ID ou nome da pasta em vagas/
autoapply aplicar --prontas [--simular] [--visivel]
```

- `--prontas`: vagas com pasta, em `aguardando_cv` ou `pendente_pergunta`, que já têm `cv.docx` ou `cv.pdf` na pasta.
- Sem currículo na pasta, a vaga não é aplicada e continua `aguardando_cv` (História 3.2).
- Antes de abrir o navegador, confere o arquivo do CV: extensão `.docx` ou `.pdf`, até 2 MB e texto legível (reaproveita a leitura do M1).
- Respeita o limite diário: ao chegar nele, para e avisa quantas ficaram.

### 8.2 `rodar` (modo normal)

```
autoapply rodar [--simular] [--visivel]
```

1. Coleta e avaliação, como no `buscar`.
2. **Candidatas:** vagas sem pasta, em `avaliada` ou `pendente_pergunta`, com score ≥ `regras.score_minimo`, maior score primeiro. Vale o score do LLM ou o da análise por palavras-chave (decisão 2).
3. Vagas `avaliada` abaixo do mínimo → `ignorada`, com o motivo "score X abaixo do mínimo Y" (História 4.1).
4. Currículo: o arquivo do `cv_base/` do currículo escolhido na análise. Com `regras.ajuste_cv_ia: true`, o terminal avisa que o ajuste só chega no M4 e usa o currículo base.
5. Aplica até o limite diário.

### 8.3 `pendentes`

```
autoapply pendentes
```

Tabela com pergunta, tipo, opções do formulário, vagas afetadas e onde responder: `respostas.md` da pasta, para vaga do modo busca, ou `config.md`. Perguntas iguais em várias vagas aparecem uma vez.

### 8.4 Terminal (Épico 6)

- Uma linha colorida por vaga, por exemplo `✔ Aplicada · Empresa X · Dev .NET Pleno · score 82 · cv_base/dotnet.docx`, e as variações para pendente, falha, simulada e ignorada.
- Contadores ao vivo: aplicadas, pendentes, falhas e quanto resta do limite.
- No fim, uma tabela-resumo da execução e a lista das perguntas pendentes novas.
- Códigos de saída: os mesmos do M2 (`0`, `1`, `2`, `3`), mais `2` para `<vaga>` não encontrada.

## 9. Testes

| Área | Como |
|---|---|
| Parsing do formulário | HTML de etapa escrito à mão em `tests/fixtures/pages/`, a partir da estrutura real e sem dados pessoais: contato, currículo, perguntas (número, select, rádio, texto), revisão |
| Regras e respostas | Funções puras: ordem das fontes, anos e pretensão em pt/en/es, opção sim/não entre idiomas, moeda estrangeira, pendente |
| `respostas.md` | Arquivo em `tmp_path`: prioridade sobre o config, `pretensão salarial`, `mensagem`, erro de formato |
| Banco | Tentativas, pendentes regravadas, contagem do dia, pastas |
| Motor | Chromium headless com um modal falso em `tests/fakes/` (etapas, validação, descarte, envio). O Enviar falso registra o clique: o teste de `--simular` confere que ele nunca é clicado; vaga com pendente descarta; tipo desconhecido falha com dump; vaga já aplicada não abre; upload chega ao input |
| Runner | Limite diário, ordem por score, score mínimo vira `ignorada`, esperas injetadas |

O LinkedIn real **nunca** é chamado nos testes, e a trava de rede do M1 continua valendo.

## 10. Tarefas

- [x] **T1 — Banco e pastas.** Status novos, tabelas novas, `job_folders` e `respostas.md` no `buscar`.
- [x] **T2 — Parsing do formulário.** Fixtures e `form_parsing.py`.
- [x] **T3 — Respostas.** `job_answers.py`, `answer_rules.py` e `answering.py`.
- [x] **T4 — Motor do Easy Apply.** Modal falso, preenchimento, upload, simulação, descarte e dump. *Pronto:* testes passam e `--simular` percorre 3 vagas reais até a revisão.
- [ ] **T5 — `aplicar` e runner.** Limite, ritmo, linhas e resumo. Migração: registra em `job_folders` as pastas criadas no M2 (ID lido do link no `vaga.md`). *Pronto:* uma candidatura real autorizada por você; a tela de sucesso e a vaga já aplicada são capturadas e viram fixture.
- [ ] **T6 — `rodar`.** Seleção por score, ignoradas por score mínimo.
- [ ] **T7 — `pendentes`.**
- [ ] **T8 — Fechamento.** README e PRD.

Ordem: T1 → T8. TDD, com as seams combinadas antes de cada tarefa, e um commit por tarefa na `develop`.

## 11. Decisões

Confirmadas em 2026-10-21:

1. Escopo do M3 conforme o cronograma do PRD: motor, `aplicar`, `rodar`, limite, pendentes e `--simular`. Ajuste por IA e `relatorio` ficam no M4.
2. O `rodar` aplica também em vagas com análise só por palavras-chave, comparando o score com `score_minimo`.
3. O formulário real foi explorado por script, sem envio, com rascunhos descartados.
4. Informações da vaga num `respostas.md` opcional na pasta, com prioridade sobre o `config.md`.
5. Pendentes no banco e no comando `pendentes`. Você responde no `config.md` ou no `respostas.md`, e a próxima execução tenta de novo.
6. Pré-preenchido pelo LinkedIn: a resposta do config manda; sem ela, mantém o valor pré-preenchido; vazio e sem resposta vira pendente.
7. O currículo sempre vai por upload.
8. "Siga a empresa" é desmarcado.
9. Anos de experiência com tecnologia fora de `experiencia_anos` vira pendente.
10. O limite diário soma `aplicar` e `rodar`; o `--simular` não conta. Espera de 1 a 3 min entre candidaturas.
11. Pretensão: nível pelo título (ou `padrao_nivel`), PJ quando a pergunta cita PJ, senão CLT; outra moeda vira pendente.
12. Campo de tipo desconhecido: se for obrigatório, a vaga vira `falhou` com dump; se for opcional, fica em branco e vai para o log.
13. Texto curto obrigatório sem resposta vira pendente; só textarea recebe a resposta genérica.
14. Sem confirmação depois do Enviar, a vaga fica `falhou` para conferência manual, nunca `aplicada`.
15. O `--simular` não grava nada no banco (nem status nem pendentes); só mostra o resultado no terminal.
