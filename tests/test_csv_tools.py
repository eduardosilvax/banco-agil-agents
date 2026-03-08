# Testes unitários para as operações CSV.
# Usa arquivos temporários para não afetar os dados reais.


import pandas as pd
import pytest

from src.tools import csv_tools


@pytest.fixture(autouse=True)
def setup_temp_csvs(tmp_path, monkeypatch):
    """Cria CSVs temporários e redireciona os paths do módulo."""
    # clientes.csv
    clients_file = tmp_path / "clientes.csv"
    clients_file.write_text(
        "cpf,nome,data_nascimento,score,limite_credito\n"
        "12345678901,Ana Silva,1990-05-15,750,5000.00\n"
        "98765432100,João Santos,1985-10-20,400,2000.00\n"
    )

    # score_limite.csv
    score_file = tmp_path / "score_limite.csv"
    score_file.write_text(
        "score_minimo,score_maximo,limite_maximo\n"
        "0,299,1000.00\n"
        "300,499,3000.00\n"
        "500,699,5000.00\n"
        "700,849,8000.00\n"
        "850,1000,15000.00\n"
    )

    # solicitacoes.csv (vazio com header)
    requests_file = tmp_path / "solicitacoes_aumento_limite.csv"
    requests_file.write_text(
        "cpf_cliente,data_hora_solicitacao,limite_atual,novo_limite_solicitado,status_pedido\n"
    )

    # Monkeypatch os paths
    monkeypatch.setattr(csv_tools, "CLIENTS_CSV", clients_file)
    monkeypatch.setattr(csv_tools, "SCORE_LIMIT_CSV", score_file)
    monkeypatch.setattr(csv_tools, "REQUESTS_CSV", requests_file)


class TestAuthentication:
    """Testes de autenticação de clientes."""

    def test_valid_auth(self):
        result = csv_tools.authenticate_client("12345678901", "1990-05-15")
        assert result is not None
        assert result["nome"] == "Ana Silva"

    def test_valid_auth_formatted_cpf(self):
        result = csv_tools.authenticate_client("123.456.789-01", "1990-05-15")
        assert result is not None
        assert result["nome"] == "Ana Silva"

    def test_valid_auth_br_date_format(self):
        result = csv_tools.authenticate_client("12345678901", "15/05/1990")
        assert result is not None
        assert result["nome"] == "Ana Silva"

    def test_invalid_cpf(self):
        result = csv_tools.authenticate_client("00000000000", "1990-05-15")
        assert result is None

    def test_wrong_birth_date(self):
        result = csv_tools.authenticate_client("12345678901", "2000-01-01")
        assert result is None

    def test_invalid_date_format(self):
        result = csv_tools.authenticate_client("12345678901", "invalid")
        assert result is None


class TestCreditQuery:
    """Testes de consulta de crédito."""

    def test_get_existing_client(self):
        result = csv_tools.get_client_credit("12345678901")
        assert result is not None
        assert result["score"] == 750
        assert result["limite_credito"] == 5000.00

    def test_get_nonexistent_client(self):
        result = csv_tools.get_client_credit("00000000000")
        assert result is None


class TestScoreLimit:
    """Testes de verificação score → limite."""

    def test_score_750_allows_8000(self):
        result = csv_tools.check_score_limit(750, 8000)
        assert result["approved"] is True

    def test_score_400_denies_5000(self):
        result = csv_tools.check_score_limit(400, 5000)
        assert result["approved"] is False
        assert result["max_allowed"] == 3000.0

    def test_score_850_allows_15000(self):
        result = csv_tools.check_score_limit(850, 15000)
        assert result["approved"] is True

    def test_score_300_denies_4000(self):
        result = csv_tools.check_score_limit(300, 4000)
        assert result["approved"] is False


class TestCreditRequest:
    """Testes de registro e atualização de solicitação."""

    def test_register_pending_then_approve(self):
        """Fluxo completo: registra como pendente, depois atualiza para aprovado."""
        # Passo 1: Registrar como pendente
        success = csv_tools.register_credit_request("12345678901", 5000, 7000, "pendente")
        assert success is True

        df = pd.read_csv(csv_tools.REQUESTS_CSV)
        assert len(df) == 1
        assert df.iloc[0]["status_pedido"] == "pendente"

        # Passo 2: Atualizar para aprovado
        success = csv_tools.update_credit_request_status("12345678901", "aprovado")
        assert success is True

        df = pd.read_csv(csv_tools.REQUESTS_CSV)
        assert df.iloc[0]["status_pedido"] == "aprovado"

    def test_register_pending_then_reject(self):
        """Fluxo completo: registra como pendente, depois atualiza para rejeitado."""
        success = csv_tools.register_credit_request("98765432100", 2000, 5000, "pendente")
        assert success is True

        success = csv_tools.update_credit_request_status("98765432100", "rejeitado")
        assert success is True

        df = pd.read_csv(csv_tools.REQUESTS_CSV)
        assert df.iloc[0]["status_pedido"] == "rejeitado"

    def test_update_nonexistent_request(self):
        """Atualizar status de CPF sem solicitação retorna False."""
        success = csv_tools.update_credit_request_status("00000000000", "aprovado")
        assert success is False

    def test_register_approved_directly(self):
        """Registro direto com status final (backward compat)."""
        success = csv_tools.register_credit_request("12345678901", 5000, 7000, "aprovado")
        assert success is True

        df = pd.read_csv(csv_tools.REQUESTS_CSV)
        assert len(df) == 1
        assert df.iloc[0]["status_pedido"] == "aprovado"


class TestScoreUpdate:
    """Testes de atualização de score."""

    def test_update_valid_client(self):
        success = csv_tools.update_client_score("12345678901", 850)
        assert success is True

        # Verificar que o score foi atualizado
        credit = csv_tools.get_client_credit("12345678901")
        assert credit["score"] == 850

    def test_update_clamped_to_1000(self):
        success = csv_tools.update_client_score("12345678901", 1500)
        assert success is True

        credit = csv_tools.get_client_credit("12345678901")
        assert credit["score"] == 1000

    def test_update_nonexistent_client(self):
        success = csv_tools.update_client_score("00000000000", 500)
        assert success is False


class TestLimitUpdate:
    """Testes de atualização de limite de crédito."""

    def test_update_valid_client(self):
        success = csv_tools.update_client_limit("12345678901", 12000.0)
        assert success is True

        credit = csv_tools.get_client_credit("12345678901")
        assert credit["limite_credito"] == 12000.0

    def test_update_nonexistent_client(self):
        success = csv_tools.update_client_limit("00000000000", 5000.0)
        assert success is False

    def test_update_persists_other_fields(self):
        """Atualizar limite não altera score nem nome."""
        csv_tools.update_client_limit("12345678901", 9000.0)
        credit = csv_tools.get_client_credit("12345678901")
        assert credit["limite_credito"] == 9000.0
        assert credit["score"] == 750
        assert credit["nome"] == "Ana Silva"
