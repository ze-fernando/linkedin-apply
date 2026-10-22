SHELL := /bin/bash
UV := $(shell command -v uv 2>/dev/null || echo $(HOME)/.local/bin/uv)
BROWSERS_DIR := .playwright

.DEFAULT_GOAL := setup
.PHONY: setup confirm uv deps browser config login

setup: confirm uv deps browser config login
	@echo ""
	@echo "✔ Pronto. Falta só você:"
	@echo "  1. Preencher o config.md com seus dados, buscas e respostas padrão."
	@echo "  2. Colocar seus currículos em cv_base/ e marcar um como padrao: true no config.md."
	@echo "  3. Conferir:  uv run autoapply validate"
	@echo "  4. Simular:   uv run autoapply run --simulate"
	@echo "  Passo a passo completo: uv run autoapply --tutorial"
	@echo "  (se o uv acabou de ser instalado, abra um terminal novo para ele entrar no PATH)"

confirm:
	@echo "Este projeto vai instalar e configurar:"
	@echo "  - uv (gerenciador de Python), se ainda não estiver instalado"
	@echo "  - Python e as dependências do projeto (uv sync)"
	@echo "  - Chromium do Playwright em $(BROWSERS_DIR)/"
	@echo "  - config.md a partir do config.example.md (se ainda não existir) e a pasta cv_base/"
	@echo "Depois abre o navegador para você fazer login no LinkedIn (a senha nunca é salva)."
	@read -r -p "Deseja continuar? [y/N] " answer; \
	case "$$answer" in [yYsS]*) ;; *) echo "Cancelado."; exit 1 ;; esac

uv:
	@if command -v uv >/dev/null 2>&1 || [ -x "$(HOME)/.local/bin/uv" ]; then \
		echo "✔ uv já instalado"; \
	else \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi

deps:
	$(UV) sync

browser:
	PLAYWRIGHT_BROWSERS_PATH=$(BROWSERS_DIR) $(UV) run playwright install chromium

config:
	@mkdir -p cv_base
	@if [ -f config.md ]; then \
		echo "✔ config.md já existe (mantido como está)"; \
	else \
		cp config.example.md config.md && echo "✔ config.md criado a partir do config.example.md"; \
	fi

login:
	$(UV) run autoapply login
