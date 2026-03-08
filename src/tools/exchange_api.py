# Cliente HTTP para consulta de cotação de moedas em tempo real.
#
# Usa a AwesomeAPI (https://economia.awesomeapi.com.br) — pública, sem key.
# Trade-off: API gratuita e confiável vs APIs pagas (Tavily, SerpAPI).
# Para o escopo do case, a AwesomeAPI é ideal: dados reais sem custo.
#
# Cache em memória com TTL de 5 minutos evita chamadas repetidas.

from __future__ import annotations

import logging
import time
from datetime import datetime

import requests

logger = logging.getLogger("banco_agil.exchange_api")

_BASE_URL = "https://economia.awesomeapi.com.br/json/last"
_TIMEOUT = 10  # segundos
_CACHE_TTL = 300  # 5 minutos

# Cache em memória: {currency: (result_dict, timestamp)}
_rate_cache: dict[str, tuple[dict, float]] = {}

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

    # Verificar cache
    if currency in _rate_cache:
        cached_result, cached_at = _rate_cache[currency]
        if (time.time() - cached_at) < _CACHE_TTL:
            logger.info(
                "Cotação %s retornada do cache (age=%.0fs)",
                currency,
                time.time() - cached_at,
            )
            return cached_result

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
            "bid": float(quote.get("bid", 0)),  # compra
            "ask": float(quote.get("ask", 0)),  # venda
            "high": float(quote.get("high", 0)),  # máxima do dia
            "low": float(quote.get("low", 0)),  # mínima do dia
            "variation": quote.get("pctChange", "0"),
            "timestamp": quote.get("create_date", ""),
        }

        logger.info(
            "Cotação obtida: %s = R$ %.4f (compra) / R$ %.4f (venda)",
            currency,
            result["bid"],
            result["ask"],
        )
        # Armazenar no cache
        _rate_cache[currency] = (result, time.time())
        return result

    except requests.Timeout:
        logger.error("Timeout ao consultar cotação de %s", currency)
    except requests.ConnectionError:
        logger.error("Erro de conexão ao consultar cotação de %s", currency)
    except requests.HTTPError as e:
        logger.error("Erro HTTP ao consultar cotação de %s: %s", currency, e)
    except Exception as e:
        logger.error("Erro inesperado ao consultar cotação de %s: %s", currency, e)

    # Fallback: retorna cache expirado se disponível (melhor que nada)
    if currency in _rate_cache:
        stale, _ = _rate_cache[currency]
        logger.warning("Retornando cotação stale do cache para %s", currency)
        return stale
    return None


def format_exchange_rate(rate: dict) -> str:
    """Formata a cotação para exibição amigável no padrão brasileiro."""

    def _fmt_rate(value: float) -> str:
        formatted = f"{value:,.4f}"
        return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_variation(pct: str) -> str:
        try:
            val = float(pct)
            sign = "+" if val > 0 else ""
            return f"{sign}{val:.2f}%".replace(".", ",")
        except (ValueError, TypeError):
            return f"{pct}%"

    def _fmt_timestamp(ts: str) -> str:
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%d/%m/%Y às %H:%M")
        except (ValueError, TypeError):
            return ts

    return (
        f"**Cotação {rate['name']}**\n\n"
        f"• **Compra:** {_fmt_rate(rate['bid'])}\n"
        f"• **Venda:** {_fmt_rate(rate['ask'])}\n"
        f"• **Máxima do dia:** {_fmt_rate(rate['high'])}\n"
        f"• **Mínima do dia:** {_fmt_rate(rate['low'])}\n"
        f"• **Variação:** {_fmt_variation(rate['variation'])}\n\n"
        f"Atualizado em: {_fmt_timestamp(rate['timestamp'])}"
    )
