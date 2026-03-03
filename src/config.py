# Configuração centralizada. Tudo vem de variáveis de ambiente (.env).
#
# Provider padrão: Google Gemini (free tier, ideal para demos).
# Alternativa: OpenAI (basta trocar LLM_PROVIDER=openai).

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format=LOG_FORMAT,
)
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

CLIENTS_CSV: Path = DATA_DIR / "clientes.csv"
SCORE_LIMIT_CSV: Path = DATA_DIR / "score_limite.csv"
REQUESTS_CSV: Path = DATA_DIR / "solicitacoes_aumento_limite.csv"
