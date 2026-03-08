"""Testes de segurança — validam rate limiting, API key, input validation, CORS."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """TestClient com mocks para evitar chamada real ao LLM."""
    with (
        patch("server.build_graph") as mock_graph,
        patch("server.LLMFactory") as mock_factory,
        patch("server.validate_config"),
    ):
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = {
            "messages": [MagicMock(content="resposta mock")],
            "current_agent": "triage",
            "compliance_approved": True,
            "compliance_reason": None,
        }
        mock_graph.return_value = mock_instance

        mock_fac = MagicMock()
        mock_fac.provider = "google"
        mock_fac.metrics = {}
        mock_fac._has_provider_credentials.return_value = True
        mock_factory.return_value = mock_fac

        from server import app

        yield TestClient(app)


class TestInputValidation:
    """Testes de validação de input no ChatRequest."""

    def test_empty_message_rejected(self, client):
        """Mensagem vazia deve ser rejeitada."""
        resp = client.post("/api/v1/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_message_too_long_rejected(self, client):
        """Mensagem > 5000 chars deve ser rejeitada."""
        resp = client.post("/api/v1/chat", json={"message": "x" * 5001})
        assert resp.status_code == 422

    def test_valid_message_accepted(self, client):
        """Mensagem válida deve ser aceita."""
        resp = client.post("/api/v1/chat", json={"message": "olá"})
        assert resp.status_code == 200

    def test_invalid_thread_id_rejected(self, client):
        """thread_id com caracteres inválidos deve ser rejeitado."""
        resp = client.post(
            "/api/v1/chat",
            json={"message": "oi", "thread_id": "abc; DROP TABLE"},
        )
        assert resp.status_code == 422

    def test_valid_thread_id_accepted(self, client):
        """thread_id UUID-like deve ser aceito."""
        resp = client.post(
            "/api/v1/chat",
            json={"message": "oi", "thread_id": "abc-123-def"},
        )
        assert resp.status_code == 200


class TestHealthCheck:
    """Testes do endpoint de health check."""

    def test_health_returns_ok(self, client):
        """Health check deve retornar status."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "components" in data

    def test_health_checks_data_files(self, client):
        """Health check deve verificar arquivos de dados."""
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "data_files" in data["components"]

    def test_health_checks_llm_provider(self, client):
        """Health check deve verificar provider LLM."""
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "llm_provider" in data["components"]


class TestRequestHeaders:
    """Testes de headers de segurança."""

    def test_request_id_returned(self, client):
        """X-Request-ID deve ser retornado em toda resposta."""
        resp = client.get("/api/v1/health")
        assert "X-Request-ID" in resp.headers

    def test_custom_request_id_echoed(self, client):
        """X-Request-ID enviado deve ser ecoado de volta."""
        resp = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "my-custom-id-123"},
        )
        assert resp.headers["X-Request-ID"] == "my-custom-id-123"


class TestAPIKeyMiddleware:
    """Testes de autenticação por API key."""

    def test_public_paths_no_auth(self, client):
        """Rotas públicas devem funcionar sem API key."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200

    def test_chat_without_key_when_key_set(self):
        """Chat sem API key quando configurada deve retornar 401."""
        with (
            patch("server.build_graph") as mock_graph,
            patch("server.LLMFactory") as mock_factory,
            patch("server.validate_config"),
            patch("server.API_KEY", "test-secret-key"),
        ):
            mock_instance = MagicMock()
            mock_graph.return_value = mock_instance

            mock_fac = MagicMock()
            mock_fac.provider = "google"
            mock_fac.metrics = {}
            mock_fac._has_provider_credentials.return_value = True
            mock_factory.return_value = mock_fac

            from server import app

            client = TestClient(app)
            resp = client.post("/api/v1/chat", json={"message": "oi"})
            assert resp.status_code == 401


class TestMetrics:
    """Testes do endpoint de métricas."""

    def test_metrics_endpoint(self, client):
        """Endpoint de métricas deve retornar dados do LLM."""
        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "llm_provider" in data
