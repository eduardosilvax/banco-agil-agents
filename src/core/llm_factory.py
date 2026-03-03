# Fábrica de LLMs — abstrai o provider (Google Gemini / OpenAI).
#
# O resto da aplicação é provider-agnostic: chama llm_factory.get_llm()
# e recebe um BaseChatModel do LangChain, sem saber qual provider está por trás.
#
# Trade-off: Gemini Flash é free tier e resolve bem para o escopo deste case.
# Se precisar de mais qualidade, basta trocar LLM_PROVIDER=openai no .env.

from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel

from src.config import (
    GEMINI_MODEL,
    GOOGLE_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)

logger = logging.getLogger("banco_agil.llm_factory")


class LLMFactory:
    """Gerenciador de LLMs com suporte a múltiplos providers.

    Uso:
        factory = LLMFactory()
        llm = factory.get_llm()            # modelo padrão
        llm = factory.get_llm(temp=0.7)    # com temperature customizada
    """

    def __init__(self) -> None:
        self._provider = LLM_PROVIDER.lower()
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

    def _build_gemini(self, temp: float) -> BaseChatModel:
        """Instancia ChatGoogleGenerativeAI."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY não configurada. "
                "Obtenha em https://aistudio.google.com/apikey"
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
