# Fábrica de LLMs — abstrai o provider (Google Gemini / OpenAI).
#
# O resto da aplicação é provider-agnostic: chama llm_factory.get_llm()
# e recebe um BaseChatModel do LangChain, sem saber qual provider está por trás.
#
# Trade-off: Gemini Flash é free tier e resolve bem para o escopo deste case.
# Se precisar de mais qualidade, basta trocar LLM_PROVIDER=openai no .env.
#
# Fallback: se o provider primário falhar, tenta o secundário automaticamente.
# Retry: até 2 tentativas por tier com backoff exponencial.
# Circuit breaker: após N falhas consecutivas, pula o provider por T segundos.

from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from src.config import (
    GEMINI_MODEL,
    GOOGLE_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)

logger = logging.getLogger("banco_agil.llm_factory")

_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.0  # seconds, doubles each retry

# Circuit breaker: após N falhas consecutivas, pula o provider por T segundos
_CB_FAILURE_THRESHOLD = 5
_CB_RECOVERY_TIMEOUT = 60.0  # segundos


class _CircuitBreaker:
    """Circuit breaker simples por provider."""

    def __init__(self) -> None:
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}

    def record_failure(self, provider: str) -> None:
        self._failures[provider] = self._failures.get(provider, 0) + 1
        if self._failures[provider] >= _CB_FAILURE_THRESHOLD:
            self._open_until[provider] = time.time() + _CB_RECOVERY_TIMEOUT
            logger.warning(
                "Circuit breaker ABERTO para '%s' (%.0fs cooldown)",
                provider,
                _CB_RECOVERY_TIMEOUT,
            )

    def record_success(self, provider: str) -> None:
        self._failures[provider] = 0
        self._open_until.pop(provider, None)

    def is_open(self, provider: str) -> bool:
        deadline = self._open_until.get(provider)
        if deadline is None:
            return False
        if time.time() >= deadline:
            # Período de recovery — permite uma tentativa
            self._open_until.pop(provider, None)
            self._failures[provider] = _CB_FAILURE_THRESHOLD - 1
            logger.info("Circuit breaker HALF-OPEN para '%s' — tentando recovery", provider)
            return False
        return True


class LLMFactory:
    """Gerenciador de LLMs com fallback entre providers e retry automático.

    Uso:
        factory = LLMFactory()
        llm = factory.get_llm()            # modelo padrão
        response = factory.invoke_with_fallback(messages)  # com fallback + retry
    """

    def __init__(self) -> None:
        self._provider = LLM_PROVIDER.lower()
        self._cb = _CircuitBreaker()
        self._metrics = {
            "total_calls": 0,
            "success": 0,
            "retries": 0,
            "fallbacks": 0,
            "failures": 0,
            "circuit_breaks": 0,
        }
        logger.info("LLMFactory initialized | provider=%s", self._provider)

    def get_llm(self, *, temp: float = 0.0) -> BaseChatModel:
        """Retorna uma instância do LLM no provider configurado.

        Args:
            temp: Temperature do modelo (0.0 = determinístico).
        """
        if self._provider == "google":
            return self._build_gemini(temp)
        elif self._provider == "openai":
            return self._build_openai(temp)
        else:
            raise ValueError(
                f"Provider '{self._provider}' não suportado. Use 'google' ou 'openai'."
            )

    def invoke_with_fallback(self, messages: Any, *, temp: float = 0.0) -> Any:
        """Invoca o LLM com retry + fallback para o provider alternativo.

        Fluxo:
            1. Tenta provider primário (até _MAX_RETRIES)
            2. Se falhar, tenta provider alternativo (até _MAX_RETRIES)
            3. Se ambos falharem, levanta a última exceção
        """
        self._metrics["total_calls"] += 1

        providers = [self._provider]
        alt = "openai" if self._provider == "google" else "google"
        if self._has_provider_credentials(alt):
            providers.append(alt)

        last_error = None
        for i, provider in enumerate(providers):
            # Circuit breaker: pula provider se aberto
            if self._cb.is_open(provider):
                self._metrics["circuit_breaks"] += 1
                logger.info("Circuit breaker aberto — pulando '%s'", provider)
                continue

            if i > 0:
                self._metrics["fallbacks"] += 1
                logger.warning("Fallback para provider '%s'", provider)

            for attempt in range(_MAX_RETRIES):
                try:
                    llm = self._build_for_provider(provider, temp)
                    result = llm.invoke(messages)
                    self._metrics["success"] += 1
                    self._cb.record_success(provider)
                    return result
                except Exception as e:
                    last_error = e
                    self._cb.record_failure(provider)
                    if attempt < _MAX_RETRIES - 1:
                        self._metrics["retries"] += 1
                        wait = _RETRY_BACKOFF * (2**attempt)
                        logger.warning(
                            "Retry %d/%d para '%s': %s (aguardando %.1fs)",
                            attempt + 1,
                            _MAX_RETRIES,
                            provider,
                            e,
                            wait,
                        )
                        time.sleep(wait)

        self._metrics["failures"] += 1
        logger.error("Todos os providers falharam após retries e fallback")
        raise last_error  # type: ignore[misc]

    def _build_for_provider(self, provider: str, temp: float) -> BaseChatModel:
        """Instancia LLM para um provider específico."""
        if provider == "google":
            return self._build_gemini(temp)
        elif provider == "openai":
            return self._build_openai(temp)
        raise ValueError(f"Provider '{provider}' não suportado.")

    @staticmethod
    def _has_provider_credentials(provider: str) -> bool:
        """Verifica se as credenciais do provider alternativo estão configuradas."""
        if provider == "google":
            return bool(GOOGLE_API_KEY)
        elif provider == "openai":
            return bool(OPENAI_API_KEY)
        return False

    def _build_gemini(self, temp: float) -> BaseChatModel:
        """Instancia ChatGoogleGenerativeAI."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY não configurada. Obtenha em https://aistudio.google.com/apikey"
            )

        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=temp,
            convert_system_message_to_human=True,
        )

    def _build_openai(self, temp: float) -> BaseChatModel:
        """Instancia ChatOpenAI."""
        from langchain_openai import ChatOpenAI

        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não configurada.")

        return ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=temp,
        )

    @property
    def provider(self) -> str:
        """Provider configurado."""
        return self._provider

    @property
    def metrics(self) -> dict[str, int]:
        """Métricas de uso do LLM."""
        return dict(self._metrics)
