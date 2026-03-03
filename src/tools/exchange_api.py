# Cliente HTTP para consulta de cotação de moedas em tempo real.
#
# Usa a AwesomeAPI (https://economia.awesomeapi.com.br) — pública, sem key.
# Trade-off: API gratuita e confiável vs APIs pagas (Tavily, SerpAPI).
# Para o escopo do case, a AwesomeAPI é ideal: dados reais sem custo.

from __future__ import annotations

import logging

import requests

logger = logging.getLogger("banco_agil.exchange_api")

_BASE_URL = "https://economia.awesomeapi.com.br/json/last"
_TIMEOUT = 10  # segundos

# Moedas suportadas pela AwesomeAPI
SUPPORTED_CURRENCIES = {
    "USD": "Dólar Americano",
    "EUR": "Euro",
    "GBP": "Libra Esterlina",
    "ARS": "Peso Argentino",
    "CAD": "Dólar Canadense",
    "AUD": "Dólar Australiano",
    "JPY": "Iene Japonês",
    "CNY": "Yuan Chinês",
    "BTC": "Bitcoin",
}


def get_exchange_rate(currency: str = "USD") -> dict | None:
    """Consulta cotação de uma moeda em relação ao Real (BRL).

    Args:
        currency: Código da moeda (ex: 'USD', 'EUR', 'GBP').

    Returns:
        Dict com {currency, name, bid, ask, high, low, timestamp} ou None se falhar.
    """
    currency = currency.upper().strip()
    pair = f"{currency}-BRL"

    try:
        logger.info("Consultando cotação: %s", pair)
        response = requests.get(f"{_BASE_URL}/{pair}", timeout=_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        key = f"{currency}BRL"

        if key not in data:
            logger.warning("Moeda não encontrada na resposta: %s", currency)
            return None

        quote = data[key]
        result = {
            "currency": currency,
            "name": quote.get("name", f"{currency}/BRL"),
            "bid": float(quote.get("bid", 0)),       # compra
            "ask": float(quote.get("ask", 0)),       # venda
            "high": float(quote.get("high", 0)),     # máxima do dia
            "low": float(quote.get("low", 0)),       # mínima do dia
            "variation": quote.get("pctChange", "0"),
            "timestamp": quote.get("create_date", ""),
        }

        logger.info(
            "Cotação obtida: %s = R$ %.4f (compra) / R$ %.4f (venda)",
            currency,
            result["bid"],
            result["ask"],
        )
        return result

    except requests.Timeout:
        logger.error("Timeout ao consultar cotação de %s", currency)
        return None
    except requests.ConnectionError:
        logger.error("Erro de conexão ao consultar cotação de %s", currency)
        return None
    except requests.HTTPError as e:
        logger.error("Erro HTTP ao consultar cotação de %s: %s", currency, e)
        return None
    except Exception as e:
        logger.error("Erro inesperado ao consultar cotação de %s: %s", currency, e)
        return None


def format_exchange_rate(rate: dict) -> str:
    """Formata a cotação para exibição amigável."""
    return (
        f"💱 **Cotação {rate['name']}**\n\n"
        f"• **Compra:** R$ {rate['bid']:.4f}\n"
        f"• **Venda:** R$ {rate['ask']:.4f}\n"
        f"• **Máxima do dia:** R$ {rate['high']:.4f}\n"
        f"• **Mínima do dia:** R$ {rate['low']:.4f}\n"
        f"• **Variação:** {rate['variation']}%\n\n"
        f"📅 Atualizado em: {rate['timestamp']}"
    )
