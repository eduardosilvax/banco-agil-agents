# Testes unitários para os agentes (mocked, sem API key).
# Testa extração de CPF, datas, lógica de tentativas, parsing de respostas.


class TestTriageHelpers:
    """Testes para funções auxiliares do Agente de Triagem."""

    def test_extract_cpf_plain(self):
        from src.agents.triage import _extract_cpf

        assert _extract_cpf("Meu CPF é 12345678901") == "12345678901"

    def test_extract_cpf_formatted(self):
        from src.agents.triage import _extract_cpf

        assert _extract_cpf("CPF: 123.456.789-01") == "12345678901"

    def test_extract_cpf_no_match(self):
        from src.agents.triage import _extract_cpf

        assert _extract_cpf("Olá, tudo bem?") is None

    def test_extract_cpf_short_number(self):
        from src.agents.triage import _extract_cpf

        assert _extract_cpf("123456") is None

    def test_extract_date_dd_mm_yyyy(self):
        from src.agents.triage import _extract_date

        assert _extract_date("15/05/1990") == "15/05/1990"

    def test_extract_date_yyyy_mm_dd(self):
        from src.agents.triage import _extract_date

        assert _extract_date("1990-05-15") == "1990-05-15"

    def test_extract_date_with_text(self):
        from src.agents.triage import _extract_date

        result = _extract_date("minha data é 15/05/1990 ok")
        assert result == "15/05/1990"

    def test_extract_date_no_match(self):
        from src.agents.triage import _extract_date

        assert _extract_date("não tem data aqui") is None


class TestCreditHelpers:
    """Testes para funções auxiliares do Agente de Crédito."""

    def test_wants_increase_simple(self):
        from src.agents.credit import CreditAgent

        assert CreditAgent._wants_increase("quero aumentar meu limite") is True

    def test_wants_increase_with_value(self):
        from src.agents.credit import CreditAgent

        assert CreditAgent._wants_increase("aumentar limite de crédito") is True

    def test_wants_increase_unrelated(self):
        from src.agents.credit import CreditAgent

        assert CreditAgent._wants_increase("qual a cotação do dólar") is False

    def test_wants_credit_info(self):
        from src.agents.credit import CreditAgent

        assert CreditAgent._wants_credit_info("ver meu limite") is True

    def test_wants_credit_info_score(self):
        from src.agents.credit import CreditAgent

        assert CreditAgent._wants_credit_info("meu score") is True

    def test_wants_exchange(self):
        from src.agents.credit import CreditAgent

        assert CreditAgent._wants_exchange("cotação do dólar") is True


class TestCreditInterviewHelpers:
    """Testes para o parser de respostas da entrevista."""

    def test_parse_float_simple(self):
        from src.agents.credit_interview import CreditInterviewAgent

        agent = CreditInterviewAgent.__new__(CreditInterviewAgent)
        assert agent._parse_answer("5000", "float") == 5000.0

    def test_parse_float_with_currency(self):
        from src.agents.credit_interview import CreditInterviewAgent

        agent = CreditInterviewAgent.__new__(CreditInterviewAgent)
        assert agent._parse_answer("R$ 5.000,50", "float") == 5000.50

    def test_parse_float_invalid(self):
        from src.agents.credit_interview import CreditInterviewAgent

        agent = CreditInterviewAgent.__new__(CreditInterviewAgent)
        assert agent._parse_answer("não sei", "float") is None

    def test_parse_employment_formal(self):
        from src.agents.credit_interview import CreditInterviewAgent

        agent = CreditInterviewAgent.__new__(CreditInterviewAgent)
        assert agent._parse_answer("formal, CLT", "employment") == "formal"

    def test_parse_employment_autonomous(self):
        from src.agents.credit_interview import CreditInterviewAgent

        agent = CreditInterviewAgent.__new__(CreditInterviewAgent)
        assert agent._parse_answer("sou freelancer", "employment") == "autônomo"

    def test_parse_employment_unemployed(self):
        from src.agents.credit_interview import CreditInterviewAgent

        agent = CreditInterviewAgent.__new__(CreditInterviewAgent)
        assert agent._parse_answer("estou desempregado", "employment") == "desempregado"

    def test_parse_int(self):
        from src.agents.credit_interview import CreditInterviewAgent

        agent = CreditInterviewAgent.__new__(CreditInterviewAgent)
        assert agent._parse_answer("2 filhos", "int") == 2

    def test_parse_int_zero(self):
        from src.agents.credit_interview import CreditInterviewAgent

        agent = CreditInterviewAgent.__new__(CreditInterviewAgent)
        assert agent._parse_answer("nenhum", "int") == 0

    def test_parse_boolean_sim(self):
        from src.agents.credit_interview import CreditInterviewAgent

        agent = CreditInterviewAgent.__new__(CreditInterviewAgent)
        assert agent._parse_answer("sim, tenho", "boolean") == "sim"

    def test_parse_boolean_nao(self):
        from src.agents.credit_interview import CreditInterviewAgent

        agent = CreditInterviewAgent.__new__(CreditInterviewAgent)
        assert agent._parse_answer("não, nenhuma", "boolean") == "não"


class TestExchangeHelpers:
    """Testes para identificação de moedas."""

    def test_identify_usd(self):
        from src.agents.exchange import ExchangeAgent

        agent = ExchangeAgent.__new__(ExchangeAgent)
        assert agent._identify_currency("cotação do dólar") == "USD"

    def test_identify_eur(self):
        from src.agents.exchange import ExchangeAgent

        agent = ExchangeAgent.__new__(ExchangeAgent)
        assert agent._identify_currency("quanto está o euro?") == "EUR"

    def test_identify_default_usd(self):
        from src.agents.exchange import ExchangeAgent

        agent = ExchangeAgent.__new__(ExchangeAgent)
        assert agent._identify_currency("cotação de moeda") == "USD"

    def test_identify_bitcoin(self):
        from src.agents.exchange import ExchangeAgent

        agent = ExchangeAgent.__new__(ExchangeAgent)
        assert agent._identify_currency("quanto custa o bitcoin?") == "BTC"
