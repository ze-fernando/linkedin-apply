# Spec técnica — M4: Ajuste por IA e relatório

**Status:** Aprovado · **Atualizado:** 2026-10-22
**PRD:** [../PRD.md](../PRD.md) — História 4.2 (ajuste automático do currículo), FR-010 (histórico e relatório), FR-011 (ajuste sem inventar informação), risco "A IA inventa informação no currículo"
**Base:** [M2-leitura.md](M2-leitura.md) (provedores de LLM, análise) e [M3-aplicacao.md](M3-aplicacao.md) (motor do Easy Apply, `rodar`, histórico de tentativas)

## 1. Objetivo

1. No `rodar`, com `regras.ajuste_cv_ia: true`, gerar para cada vaga um currículo em PDF ajustado à vaga, a partir do currículo base escolhido na análise, e enviar esse PDF.
2. O ajuste só reescreve o Resumo Profissional e reordena bullets e competências. Uma checagem automática descarta o ajuste se aparecer algo que não está no currículo base, e aí vai o currículo base.
3. Comando `relatorio` com o histórico das candidaturas: resumo por período, lista, taxa de conclusão e exportação em CSV.

**Pronto quando:**

- Você aprova o template pela prévia com dados fictícios.
- Um `rodar --simular` com o ajuste ligado gera os PDFs de vagas reais, e o texto deles é legível (extraível) como o de um currículo comum.
- Uma candidatura real é enviada com o PDF ajustado e aparece no `relatorio`.

**Fora do M4:** ajuste no modo busca (você continua adaptando à mão), reescrita do texto dos bullets e agendamento.

## 2. Achados

### 2.1 Estrutura dos currículos base

Os três `.docx` do `cv_base/` têm o mesmo layout, uma coluna, sem tabelas:

| Bloco | Como aparece no `.docx` |
| --- | --- |
| Cabeçalho | 4 primeiros parágrafos: nome (negrito), título profissional, cidade e contatos, links (LinkedIn e GitHub) |
| Título de seção | Parágrafo em negrito com um só texto: "Resumo Profissional", "Experiência Profissional", "Formação", "Competências Técnicas", "Idiomas" |
| Experiência | Cabeçalho em negrito "Cargo`\t`período", depois uma linha "Empresa • descrição" e os bullets no estilo `List Paragraph`, cada um com um trecho inicial em negrito e o resto normal |
| Formação | Linha em negrito "Curso`\t`conclusão" e linha "Instituição — situação" |
| Competências | Uma linha por grupo: rótulo em negrito ("Linguagens:") e os itens separados por vírgula |
| Idiomas | Uma linha com os idiomas e níveis |

O parsing segue essa estrutura e falha com mensagem clara se o arquivo fugir dela (seção desconhecida, experiência sem período). Um `.pdf` no `cv_base/` não pode ser ajustado e vai como está.

### 2.2 Geração de PDF

Não há LibreOffice nem pandoc. O Chromium do Playwright, que já está em `.playwright/`, gera PDF a partir de HTML com `page.pdf()`. O HTML é local (`page.set_content`), sem rede. O PDF sai com texto real, extraível pelo `pypdf`, o que é o que o ATS precisa.

## 3. Estrutura (novos módulos)

```
src/autoapply/modules/
├── tailoring/
│   ├── models.py          # ResumeDocument, ExperienceEntry, SkillLine, TailoringPlan, TailoringResult
│   ├── resume_structure.py # .docx → ResumeDocument (funções puras sobre python-docx)
│   ├── template.py        # ResumeDocument → HTML (template que copia o visual do .docx)
│   ├── pdf.py             # HTML → PDF com o Chromium
│   ├── prompt.py          # monta o prompt e o schema do plano de ajuste
│   ├── plan.py            # aplica o plano ao ResumeDocument
│   ├── verification.py    # checagem "nada novo" contra o currículo base
│   └── tailor.py          # orquestra: estrutura → LLM → plano → checagem → PDF
├── reporting/
│   ├── report.py          # consultas e números do relatório (funções puras sobre o banco)
│   └── commands.py        # `relatorio`
└── matching/
    └── providers.py       # passa a aceitar schema e leitor de resultado por chamada
```

**Provedores de LLM:** hoje `run_provider` e `analyze_with_fallback` só conhecem o schema da análise de vaga. Eles passam a receber o schema e a função que valida o resultado, mantendo o retry, o fallback entre provedores e o desligamento após 3 falhas. A análise de vaga continua igual por fora.

## 4. Banco

```sql
CREATE TABLE IF NOT EXISTS tailored_resumes (
  job_id TEXT PRIMARY KEY REFERENCES jobs(id),
  base_resume TEXT NOT NULL,        -- arquivo do cv_base/ usado como base
  pdf_path TEXT,                    -- curriculos-enviados/...pdf (vazio se descartado antes do PDF)
  status TEXT NOT NULL,             -- usado | descartado
  reason TEXT,                      -- motivo do descarte
  provider TEXT,
  model TEXT,
  created_at TEXT NOT NULL
);
```

- Tabela nova com `CREATE TABLE IF NOT EXISTS`, sem alterar as existentes.
- A tentativa em `application_attempts` continua gravando em `resume_file` o arquivo que foi enviado de fato: o PDF ajustado ou o `.docx` base.

## 5. Ajuste

### 5.1 O que vai para o LLM

- Descrição da vaga, requisitos e gap da análise.
- Do currículo base: o Resumo Profissional, os bullets numerados de cada experiência (com cargo e período) e as linhas de competências com os itens numerados.
- **Não vão:** o cabeçalho (nome, telefone, e-mail, cidade, links). O texto enviado passa pelo mesmo mascaramento de e-mail e telefone do M2.

### 5.2 O que volta (schema)

```json
{
  "resumo": "texto do novo Resumo Profissional",
  "ordem_bullets": [[2, 0, 1, 3], [0, 3, 1, 2, 4]],
  "ordem_competencias": [1, 0, 4, 2, 3, 5, 6, 7],
  "ordem_itens": [[0, 2, 1], [3, 0, 1, 2]]
}
```

- `ordem_bullets`: uma permutação por experiência, na ordem das experiências.
- `ordem_competencias`: permutação das linhas de competências.
- `ordem_itens`: uma permutação dos itens de cada linha, na ordem original das linhas.
- Cargos, empresas, períodos, formação e idiomas não mudam e não fazem parte da resposta.

### 5.3 Checagem "nada novo" (antes de gerar o PDF)

O ajuste é descartado, com o motivo, se:

1. Alguma ordem não é uma permutação exata (índice faltando, repetido ou fora da faixa).
2. O resumo cita uma tecnologia do vocabulário (o mesmo do pré-score: `TECH_VOCABULARY` mais as chaves de `experiencia_anos`) que não aparece em nenhum lugar do currículo base.
3. O resumo tem um número (anos, porcentagem, quantidade) que não aparece no currículo base.
4. O resumo tem uma palavra com inicial maiúscula fora do começo de frase que não aparece no currículo base (pega nome de empresa, cargo ou certificação inventados).
5. O resumo fica vazio ou passa de 2 vezes o tamanho do resumo original.

Descartado o ajuste, a vaga é aplicada com o currículo base, e a linha do terminal avisa o motivo (decisão 3). Sem provedor de LLM disponível, acontece o mesmo.

### 5.4 Template e PDF

- O HTML reproduz o visual do `.docx`: nome em destaque, título, contatos e links, seções com título em negrito, cargo e período na mesma linha (período à direita), empresa, bullets com o trecho inicial em negrito e competências com o rótulo em negrito. Uma coluna, A4, margens e fontes próximas das do `.docx`.
- O HTML é gerado com escape de todo texto e sem recursos externos.
- Antes de usar, a prévia é gerada com dados fictícios e mostrada para a sua aprovação. Ela nunca é publicada com os seus dados.
- Depois de gerar o PDF, o texto é extraído com `pypdf` e passa pela mesma checagem de "texto insuficiente" do M1. Se falhar, vai o currículo base.

### 5.5 Arquivos

- PDF enviado: `curriculos-enviados/AAAA-MM-DD-empresa-cargo.pdf` (mesmo slug das pastas do modo busca), fora do git.
- No `--simular`: o PDF é gerado em `debug/simulacao-cv/` e nada é gravado no banco, como no resto da simulação (decisão 7).

## 6. Integração com o `rodar`

1. Para cada candidata, antes de abrir o formulário: com `ajuste_cv_ia: true` e currículo base `.docx`, roda o ajuste (seção 5). O currículo enviado é o PDF ajustado ou o base.
2. A linha da vaga mostra qual foi: `cv ajustado (curriculos-enviados/...pdf)` ou `cv_base/dotnet.docx · ajuste descartado: <motivo>`.
3. O aviso "o ajuste só chega no M4" sai.
4. O ajuste roda só para vagas que vão ser tentadas: respeita o limite diário e não gasta LLM em vaga já aplicada.
5. Vaga `pendente_pergunta` que volta na próxima execução reaproveita o PDF já gerado (`tailored_resumes` com status `usado`).

## 7. Comando `relatorio`

```
autoapply relatorio [--dias N] [--csv <arquivo>]
```

- Período: últimos `N` dias, padrão 7; `--dias 0` mostra tudo.
- **Resumo:** tabela com aplicadas, já aplicadas, pendentes, falhas e simuladas não entram (não ficam no banco), separadas por modo (busca e normal), mais as vagas ignoradas no período (pela data de coleta).
- **Taxa de conclusão:** aplicadas ÷ (aplicadas + falhas + pendentes), e os 3 motivos de falha mais comuns.
- **Lista:** data, modo, resultado, empresa, cargo, score, currículo enviado (base ou ajustado) e link da vaga, mais recentes primeiro.
- **CSV:** `--csv arquivo.csv` grava a lista com as mesmas colunas, separador `;` e UTF-8 com BOM (abre direto no Excel/LibreOffice).
- Usa só a última tentativa de cada vaga na lista; os números do resumo contam todas as tentativas do período.

## 8. Terminal

- Durante o ajuste, o status mostra "Ajustando currículo para <empresa>...".
- A tabela-resumo do `rodar` ganha a linha "Currículos ajustados: X usados, Y descartados".

## 9. Testes

| Área | Como |
| --- | --- |
| Estrutura do CV | `.docx` gerado no teste com o mesmo layout e dados fictícios: cabeçalho, seções, experiências, competências; erro de estrutura |
| Plano e checagem | Funções puras: permutações válidas e inválidas, tecnologia nova, número novo, nome próprio novo, resumo vazio ou longo |
| Template | HTML com escape, todas as seções e a ordem do plano aplicada |
| PDF | Chromium headless gera o PDF de um currículo fictício, e o texto extraído contém nome, seções e bullets |
| Provedores | Os executáveis `claude` e `opencode` falsos do M2 com o schema do plano |
| Integração | Runner com ajuste falso: PDF usado, ajuste descartado volta ao base, `--simular` não grava, reaproveitamento do PDF |
| Relatório | Banco temporário: contagens por período e modo, taxa, motivos, última tentativa por vaga e CSV |

Nenhum teste chama um LLM real ou o LinkedIn.

## 10. Tarefas

- [x] **T1 — Estrutura do CV.** `models.py` e `resume_structure.py`. *Pronto:* os três `.docx` do `cv_base/` são lidos sem erro.
- [x] **T2 — Template e PDF.** `template.py` e `pdf.py`. *Pronto:* você aprova a prévia com dados fictícios.
- [x] **T3 — Plano e checagem.** Provedores com schema por chamada, `prompt.py`, `plan.py` e `verification.py`.
- [ ] **T4 — Ajuste no `rodar`.** `tailor.py`, tabela `tailored_resumes`, pasta `curriculos-enviados/`, linhas e resumo. *Pronto:* `rodar --simular` gera PDFs de vagas reais e uma candidatura real vai com o PDF ajustado.
- [ ] **T5 — `relatorio`.**
- [ ] **T6 — Fechamento.** README, PRD e `config.example.md`.

Ordem: T1 → T6. TDD, com as seams combinadas antes de cada tarefa, e um commit por tarefa na `develop`.

## 11. Decisões

Confirmadas em 2026-10-22:

1. Formato do currículo ajustado: template HTML que copia o visual do `.docx`, gerado em PDF pelo Chromium. Responde a questão em aberto do PRD.
2. A IA só reescreve o Resumo Profissional e reordena bullets e competências. Cargos, empresas, datas e o texto dos bullets não mudam.
3. Se a checagem acha algo novo, o ajuste é descartado e vai o currículo base, com aviso na linha da vaga.
4. O ajuste roda só no `rodar`, com `regras.ajuste_cv_ia: true`. O modo busca continua manual.
5. O `relatorio` tem resumo por período (`--dias`, padrão 7), lista das candidaturas, taxa de conclusão com os motivos de falha e exportação `--csv`.
6. Os PDFs enviados ficam em `curriculos-enviados/`, fora do git.
7. No `--simular`, o PDF é gerado em `debug/simulacao-cv/` e nada vai para o banco.
8. Vaga que volta (pendente respondida) reaproveita o PDF já gerado, sem nova chamada ao LLM.
9. Currículo base em `.pdf` não é ajustado e vai como está.
