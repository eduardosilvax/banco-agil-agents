# Testes unitários para a API de câmbio (mocked HTTP).
# Sem dependência de rede — testa rotas de sucesso e falha.

from unittest.mock import MagicMock, patch

from src.tools.exchange_api import (
    SUPPORTED_CURRENCIES,
    format_exchange_rate,
    get_exchange_rate,
)


class TestGetExchangeRate:
    """Testes para a função get_exchange_rate."""

    @patch("src.tools.exchange_api.requests.get")
    def test_successful_usd_query(self, mock_get):
        """Consulta bem-sucedida de USD retorna dados estruturados."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "USDBRL": {
                "name": "Dólar Americano/Real Brasileiro",
                "bid": "5.8500",
                "ask": "5.8600",
                "high": "5.9000",
                "low": "5.8000",
                "pctChange": "0.25",
                "create_date": "2026-03-03 10:00:00",
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_exchange_rate("USD")

        assert result is not None
        assert result["currency"] == "USD"
        assert result["bid"] == 5.85
        assert result["ask"] == 5.86
        assert result["high"] == 5.90
        assert result["low"] == 5.80
        assert result["variation"] == "0.25"
        mock_get.assert_called_once()

    @patch("src.tools.exchange_api.requests.get")
    def test_successful_eur_query(self, mock_get):
        """Consulta bem-sucedida de EUR."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "EURBRL": {
                "name": "Euro/Real Brasileiro",
                "bid": "6.3000",
                "ask": "6.3200",
                "high": "6.4000",
                "low": "6.2500",
                "pctChange": "-0.10",
                "create_date": "2026-03-03 10:00:00",
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_exchange_rate("EUR")

        assert result is not None
        assert result["currency"] == "EUR"
        assert result["bid"] == 6.30

    @patch("src.tools.exchange_api.requests.get")
    def test_timeout_returns_none(self, mock_get):
        """Timeout da API retorna None."""
        import requests

        from src.tools.exchange_api import _rate_cache

        _rate_cache.clear()

        mock_get.side_effect = requests.Timeout("Connection timed out")

        result = get_exchange_rate("USD")
        assert result is None

    @patch("src.tools.exchange_api.requests.get")
    def test_connection_error_returns_none(self, mock_get):
        """Erro de conexão retorna None."""
        import requests

        from src.tools.exchange_api import _rate_cache

        _rate_cache.clear()

        mock_get.side_effect = requests.ConnectionError("DNS failure")

        result = get_exchange_rate("USD")
        assert result is None

    @patch("src.tools.exchange_api.requests.get")
    def test_http_error_returns_none(self, mock_get):
        """Erro HTTP (500, 404, etc.) retorna None."""
        import requests

        from src.tools.exchange_api import _rate_cache

        _rate_cache.clear()

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_response

        result = get_exchange_rate("USD")
        assert result is None

    @patch("src.tools.exchange_api.requests.get")
    def test_currency_not_in_response(self, mock_get):
        """Moeda não encontrada na resposta retorna None."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # resposta vazia
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_exchange_rate("XYZ")
        assert result is None

    def test_currency_uppercased(self):
        """Verifica que a moeda é normalizada para uppercase."""
        with patch("src.tools.exchange_api.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "USDBRL": {
                    "name": "Dólar/Real",
                    "bid": "5.85",
                    "ask": "5.86",
                    "high": "5.90",
                    "low": "5.80",
                    "pctChange": "0",
                    "create_date": "2026-03-03",
                }
            }
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = get_exchange_rate("usd")  # lowercase
            assert result is not None
            assert result["currency"] == "USD"


class TestFormatExchangeRate:
    """Testes para a formatação de cotação."""

    def test_format_complete_rate(self):
        """Formata cotação completa corretamente."""
        rate = {
            "currency": "USD",
            "name": "Dólar Americano/Real Brasileiro",
            "bid": 5.85,
            "ask": 5.86,
            "high": 5.90,
            "low": 5.80,
            "variation": "0.25",
            "timestamp": "2026-03-03 10:00:00",
        }
        formatted = format_exchange_rate(rate)

        assert "Dólar Americano/Real Brasileiro" in formatted
        assert "R$ 5,8500" in formatted
        assert "R$ 5,8600" in formatted
        assert "+0,25%" in formatted
        assert "03/03/2026 às 10:00" in formatted

    def test_format_contains_labels(self):
        """Formatação contém os labels esperados."""
        rate = {
            "currency": "EUR",
            "name": "Euro/Real",
            "bid": 6.30,
            "ask": 6.32,
            "high": 6.40,
            "low": 6.25,
            "variation": "-0.10",
            "timestamp": "2026-03-03",
        }
        formatted = format_exchange_rate(rate)

        assert "Compra" in formatted
        assert "Venda" in formatted
        assert "Máxima" in formatted
        assert "Mínima" in formatted
        assert "Variação" in formatted
        assert "-0,10%" in formatted


class TestSupportedCurrencies:
    """Testes para o dicionário de moedas."""

    def test_major_currencies_present(self):
        """Moedas principais estão no dicionário."""
        assert "USD" in SUPPORTED_CURRENCIES
        assert "EUR" in SUPPORTED_CURRENCIES
        assert "GBP" in SUPPORTED_CURRENCIES
        assert "BTC" in SUPPORTED_CURRENCIES

    def test_currencies_have_names(self):
        """Cada moeda tem um nome descritivo."""
        for code, name in SUPPORTED_CURRENCIES.items():
            assert isinstance(name, str)
            assert len(name) > 0
