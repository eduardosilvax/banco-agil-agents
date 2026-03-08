# Configuração centralizada. Tudo vem de variáveis de ambiente (.env).
#
# Provider padrão: Google Gemini (free tier, ideal para demos).
# Alternativa: OpenAI (basta trocar LLM_PROVIDER=openai).

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


# ---------- Structured JSON Logging ----------
class _JSONFormatter(logging.Formatter):
    """Formatter que emite logs em JSON (queryável em produção)."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

_handler = logging.StreamHandler()
if ENVIRONMENT == "production":
    _handler.setFormatter(_JSONFormatter())
else:
    _handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
logging.basicConfig(level=LOG_LEVEL, handlers=[_handler], force=True)
logger = logging.getLogger("banco_agil")

# ---------- LLM Provider ----------
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")

# Google Gemini
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# OpenAI (alternativo)
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1-nano")

# ---------- Paths ----------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"

# ---------- API Security ----------
API_KEY: str = os.getenv("API_KEY", "")

# CORS — lista de origens permitidas (CSV no env, default: liberado em dev)
_cors_raw = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS: list[str] = (
    [o.strip() for o in _cors_raw.split(",") if o.strip()]
    if _cors_raw
    else ["*"]  # fallback permissivo para ambiente local
)

CLIENTS_CSV: Path = DATA_DIR / "clientes.csv"
SCORE_LIMIT_CSV: Path = DATA_DIR / "score_limite.csv"
REQUESTS_CSV: Path = DATA_DIR / "solicitacoes_aumento_limite.csv"


def validate_config() -> None:
    """Valida configuração essencial na inicialização."""
    if ENVIRONMENT == "production" and not API_KEY:
        raise RuntimeError("API_KEY é obrigatória em produção. Configure no .env.")

    if not GOOGLE_API_KEY and not OPENAI_API_KEY:
        logger.warning(
            "Nenhuma API key de LLM configurada (GOOGLE_API_KEY / OPENAI_API_KEY). "
            "O sistema vai falhar na primeira chamada ao LLM."
        )

    if not DATA_DIR.exists():
        raise RuntimeError(
            f"Diretório de dados não encontrado: {DATA_DIR}. Verifique a estrutura do projeto."
        )
