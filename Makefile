# Banco Ágil Agents — Makefile
#
# Interface padronizada para rodar, testar e deployar o projeto.
# Use "make help" para ver todos os comandos disponíveis.

.PHONY: help install run test test-fast lint lint-fix docker docker-down clean setup check-python

# ── Configurações ──────────────────────────────
PYTHON  := python3
VENV    := .venv
BIN     := $(VENV)/bin
PORT    := 8000

# ── Alvo padrão ────────────────────────────────
help: ## Lista todos os comandos disponíveis
	@echo ""
	@echo "  Banco Ágil Agents"
	@echo "  ─────────────────────────────────────"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Setup ──────────────────────────────────────
check-python: ## Verifica se Python 3.11+ está instalado
	@$(PYTHON) -c "import sys; assert sys.version_info >= (3, 11), \
		f'Python 3.11+ necessário (encontrado: {sys.version})'" 2>/dev/null || \
		{ echo "✗ Python 3.11+ não encontrado. Instale em https://python.org"; exit 1; }
	@echo "✓ $$($(PYTHON) --version)"

$(VENV)/bin/activate: requirements.txt
	@echo "→ Criando ambiente virtual..."
	@$(PYTHON) -m venv $(VENV)
	@$(BIN)/pip install --upgrade pip -q
	@echo "→ Instalando dependências..."
	@$(BIN)/pip install -r requirements.txt -q
	@touch $(VENV)/bin/activate

install: check-python $(VENV)/bin/activate ## Cria venv e instala dependências
	@echo "✓ Dependências instaladas."

setup: install ## Primeiro setup completo (venv + .env)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ""; \
		echo "✓ Arquivo .env criado a partir de .env.example."; \
		echo ""; \
		echo "  Próximo passo: abra o .env e preencha sua API key."; \
		echo "  Recomendado: GOOGLE_API_KEY (Gemini, free tier)"; \
		echo "  Obtenha em:  https://aistudio.google.com/apikey"; \
		echo ""; \
	else \
		echo "✓ .env já existe."; \
	fi

# ── Execução ───────────────────────────────────
run: install ## Sobe o backend FastAPI na porta 8000
	@echo "→ Iniciando Banco Ágil em http://localhost:$(PORT)"
	@$(BIN)/uvicorn server:app --reload --host 0.0.0.0 --port $(PORT)

# ── Testes ─────────────────────────────────────
test: install ## Roda todos os testes unitários
	@$(BIN)/pytest tests/ -v --tb=short

# ── Qualidade ──────────────────────────────────
lint: install ## Verifica estilo de código com ruff
	@$(BIN)/ruff check src/ tests/ server.py

lint-fix: install ## Corrige problemas de estilo automaticamente
	@$(BIN)/ruff check src/ tests/ server.py --fix

# ── Docker ─────────────────────────────────────
docker: ## Build e sobe via Docker Compose
	@docker compose up --build -d
	@echo ""
	@echo "✓ Banco Ágil rodando em http://localhost:$(PORT)"
	@echo "  Logs: docker compose logs -f"

docker-down: ## Para e remove containers
	@docker compose down
	@echo "✓ Containers parados."

# ── Limpeza ────────────────────────────────────
clean: ## Remove venv, caches e artefatos
	@rm -rf $(VENV) .pytest_cache .ruff_cache htmlcov .coverage
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Projeto limpo."
