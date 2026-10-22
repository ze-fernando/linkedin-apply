---
# =====================================================================
#  config.example.md — modelo do config.md do LinkedIn Auto-Apply
#  Copie para config.md (que fica fora do git) e troque pelos seus dados:
#    cp config.example.md config.md
#  Todos os dados abaixo são fictícios.
# =====================================================================

perfil:
  nome: Maria Teste da Silva
  primeiro_nome: Maria
  sobrenome: Teste da Silva
  email: maria.teste@example.com
  telefone: "+55 11 91234-5678"
  ddd: "11"
  celular: "91234-5678"
  cidade: São Paulo
  estado: SP
  pais: Brasil
  linkedin: https://www.linkedin.com/in/maria-teste
  github: https://github.com/maria-teste
  portfolio: null
  autorizado_trabalhar_brasil: true
  precisa_patrocinio_visto: false

disponibilidade:
  inicio: Imediato
  aviso_previo_dias: 0
  aceita_viagens_esporadicas: true
  aceita_mudanca_cidade: false
  modalidades_aceitas: [remoto]

contrato:
  aceita: [CLT, PJ]
  possui_cnpj: false

# Valores em reais por mês. "formulario" é o valor enviado quando a vaga pergunta a pretensão.
pretensao:
  junior:
    clt: { min: 3000, max: 4000, formulario: 3500 }
    pj: { min: 4000, max: 5000, formulario: 4500 }
  pleno:
    clt: { min: 6000, max: 7000, formulario: 6500 }
    pj: { min: 7000, max: 9000, formulario: 8000 }
  padrao_nivel: junior

idiomas:
  portugues: nativo
  ingles: intermediario

formacao:
  curso: Ciência da Computação
  instituicao: Universidade Teste
  status: em andamento
  conclusao_prevista: "2027-12"

# Anos de experiência por tecnologia, usados nas perguntas "quantos anos com X?".
# A chave precisa bater com o nome que a vaga usa: cadastre as variações
# (ex.: "ASP.NET" e "ASP.NET Core", "Spring" e "Spring Boot").
# Tecnologia perguntada que não está aqui vira pendente.
# Chaves com 3+ caracteres e pelo menos 1 ano também entram no pré-score das vagas.
experiencia_anos:
  total_desenvolvimento: 3
  "Python": 3
  "Django": 2
  "FastAPI": 1
  "SQL": 3
  "PostgreSQL": 2
  "JavaScript": 2
  "TypeScript": 1
  "React": 1
  "Docker": 1
  "Git": 3
  "Linux": 2
  "Java": 0

diversidade:
  genero: Prefiro não informar
  orientacao_sexual: Prefiro não informar
  raca_cor: Prefiro não informar
  pcd: false

busca:
  localizacao: Brasil
  modalidade: remoto
  niveis: [junior, pleno]
  publicadas_ha_no_maximo_dias: 7
  somente_easy_apply: true
  termos_bloqueados_no_titulo:
    [Sênior, Senior, Sr, Especialista, Lead, Tech Lead, Principal, Staff, Arquiteto, Gerente, Coordenador, Estágio, Estagiário]
  empresas_bloqueadas: []
  palavras_bloqueadas: []

# Um currículo base por área. Exatamente um tem "padrao: true".
# "buscas" são os termos pesquisados no LinkedIn para esse currículo.
curriculos:
  - arquivo: cv_base/backend.docx
    nome: Back-end Python
    padrao: true
    buscas: ["Desenvolvedor Python", "Desenvolvedor Back-end"]
  - arquivo: cv_base/fullstack.docx
    nome: Full Stack
    buscas: ["Desenvolvedor Full Stack", "Desenvolvedor React"]

regras:
  score_minimo: 70
  limite_diario: 15
  modo_busca_quantidade: 10
  ajuste_cv_ia: false
  analise_llm_max_vagas: 30

llm:
  provedores: [claude, opencode]
  claude:
    modelo: sonnet
  opencode:
    modelo: opencode/deepseek-v4.1-flash-free
  timeout_segundos: 180
---

# Respostas padrão

Respostas usadas no Easy Apply. Uma pergunta **objetiva** que não estiver aqui nem
no bloco acima não é chutada: ela vira pendente e a vaga é tentada de novo depois.

| Pergunta (ou variação)                      | Resposta      |
| ------------------------------------------- | ------------- |
| Aceita trabalhar remotamente?               | Sim           |
| Aceita trabalhar presencialmente / híbrido? | Não           |
| Aceita contratação PJ?                      | Sim           |
| Aceita contratação CLT?                     | Sim           |
| Possui CNPJ?                                | Não           |
| Está empregado atualmente?                  | Sim           |
| Disponibilidade para início                 | Imediato      |
| Disponibilidade para viagens esporádicas?   | Sim           |
| Aceita mudar de cidade?                     | Não           |
| Nível de inglês                             | Intermediário |
| Possui ensino superior completo?            | Não           |
| Possui deficiência (PcD)?                   | Não           |
| Precisa de patrocínio de visto?             | Não           |
| Está autorizado a trabalhar no Brasil?      | Sim           |

<!-- Adicione novas respostas aqui conforme aparecerem em "pendentes". -->

# Resposta genérica

Usada em perguntas de texto livre sem resposta específica
(ex.: "Por que quer trabalhar aqui?", "Fale sobre você").

> Sou desenvolvedora de software com foco em back-end e automação. Tenho interesse
> na vaga porque ela combina com a minha experiência e acredito que posso contribuir
> rápido com a equipe.
