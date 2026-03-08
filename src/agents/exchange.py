# Agente de Câmbio — consulta cotação de moedas em tempo real.
#
# Responsabilidades:
# 1. Identificar a moeda solicitada pelo cliente
# 2. Consultar AwesomeAPI para cotação em tempo real
# 3. Apresentar cotação de forma amigável
# 4. Tratar erros (API indisponível, moeda inválida)
# 5. Encerrar atendimento de câmbio com mensagem amigável

from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage, HumanMessage

from src.core.llm_factory import LLMFactory
from src.schemas.state import BankState
from src.tools.exchange_api import (
    SUPPORTED_CURRENCIES,
    format_exchange_rate,
    get_exchange_rate,
)

logger = logging.getLogger("banco_agil.exchange")

# Mapeamento de nomes comuns para códigos
_CURRENCY_ALIASES: dict[str, str] = {
    "dólar": "USD",
    "dolar": "USD",
    "dollar": "USD",
    "euro": "EUR",
    "libra": "GBP",
    "iene": "JPY",
    "yuan": "CNY",
    "peso": "ARS",
    "bitcoin": "BTC",
    "btc": "BTC",
    "usd": "USD",
    "eur": "EUR",
    "gbp": "GBP",
    "jpy": "JPY",
    "cny": "CNY",
    "ars": "ARS",
    "cad": "CAD",
    "aud": "AUD",
    "dólar canadense": "CAD",
    "dolar canadense": "CAD",
    "dólar australiano": "AUD",
    "dolar australiano": "AUD",
}


class ExchangeAgent:
    """Agente de Câmbio — consulta cotação em tempo real via AwesomeAPI.

    Identifica a moeda na mensagem do cliente (ou assume USD),
    consulta a API e retorna cotação formatada.
    """

    def __init__(self, llm_factory: LLMFactory) -> None:
        self._llm = llm_factory.get_llm(temp=0.2)

    def run(self, state: BankState) -> dict:
        """Nó LangGraph: executa consulta de câmbio."""
        messages = state.get("messages", [])
        client_data = state.get("client_data", {})
        nome = client_data.get("nome", "Cliente")
        first_name = nome.split()[0]

        human_messages = [m for m in messages if isinstance(m, HumanMessage)]

        # Verificar se quer encerrar
        if human_messages:
            last_msg = human_messages[-1].content.lower()
            if self._wants_to_end(last_msg):
                farewell = (
                    f"Tudo bem, {first_name}! Se precisar de mais alguma cotação, "
                    f"estou aqui. Obrigado!"
                )
                return {
                    "messages": [AIMessage(content=farewell)],
                    "should_end": True,
                    "current_agent": "exchange",
                }

            # Verificar se quer ir para crédito
            if self._wants_credit(last_msg):
                return {
                    "messages": [
                        AIMessage(content=f"Claro, {first_name}! Vou te ajudar com crédito.")
                    ],
                    "current_agent": "credit",
                }

        # Identificar a moeda
        currency = self._identify_currency(human_messages[-1].content if human_messages else "")

        # Consultar cotação
        rate = get_exchange_rate(currency)

        if rate:
            formatted = format_exchange_rate(rate)
            response = (
                f"{first_name}, aqui está a cotação que você pediu:\n\n"
                f"{formatted}\n\n"
                f"Deseja consultar outra moeda? "
                f"Posso buscar: {', '.join(SUPPORTED_CURRENCIES.keys())}\n\n"
                f"Ou posso te ajudar com outro serviço!"
            )
        else:
            response = (
                f"Desculpe, {first_name}, não consegui obter a cotação de "
                f"**{currency}** no momento.\n\n"
                f"Isso pode ser um problema temporário com o serviço de câmbio. "
                f"Por favor, tente novamente em alguns instantes.\n\n"
                f"Moedas disponíveis: {', '.join(SUPPORTED_CURRENCIES.keys())}"
            )

        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "exchange",
        }

    def _identify_currency(self, text: str) -> str:
        """Identifica a moeda na mensagem do cliente. Padrão: USD."""
        text_lower = text.lower()

        # Busca por aliases conhecidos
        for alias, code in _CURRENCY_ALIASES.items():
            if alias in text_lower:
                logger.info("Moeda identificada: %s (%s)", alias, code)
                return code

        # Busca por códigos de 3 letras
        match = re.search(r"\b([A-Z]{3})\b", text.upper())
        if match and match.group(1) in SUPPORTED_CURRENCIES:
            return match.group(1)

        # Padrão: USD
        logger.info("Moeda não identificada, usando padrão USD")
        return "USD"

    @staticmethod
    def _wants_to_end(message: str) -> bool:
        patterns = [
            r"\b(sair|encerrar|tchau|adeus|finalizar|obrigad[oa])\b",
            r"\b(bye|exit|quit)\b",
        ]
        return any(re.search(p, message.lower()) for p in patterns)

    @staticmethod
    def _wants_credit(message: str) -> bool:
        patterns = [
            r"\b(crédito|credito|limite|aumento)\b",
        ]
        return any(re.search(p, message.lower()) for p in patterns)
