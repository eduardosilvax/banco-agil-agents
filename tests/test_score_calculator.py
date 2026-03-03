# Testes unitários para o calculador de score de crédito.
# Sem dependência de API key — testes puramente lógicos.

from src.tools.score_calculator import calculate_score


class TestScoreCalculator:
    """Testes para a fórmula de score de crédito."""

    def test_high_score_formal_no_debts(self):
        """Empregado formal, boa renda, sem dívidas → score alto."""
        score = calculate_score(
            renda_mensal=8000,
            tipo_emprego="formal",
            despesas_fixas=2000,
            num_dependentes=0,
            tem_dividas="não",
        )
        # (8000 / 2001) * 30 + 300 + 100 + 100 ≈ 619
        assert score > 500
        assert score <= 1000

    def test_low_score_unemployed_with_debts(self):
        """Desempregado, sem renda, com dívidas → score baixo."""
        score = calculate_score(
            renda_mensal=0,
            tipo_emprego="desempregado",
            despesas_fixas=1500,
            num_dependentes=3,
            tem_dividas="sim",
        )
        # (0 / 1501) * 30 + 0 + 30 + (-100) = -70 → clamped to 0
        assert score == 0

    def test_medium_score_autonomous(self):
        """Autônomo, renda moderada → score médio."""
        score = calculate_score(
            renda_mensal=4000,
            tipo_emprego="autônomo",
            despesas_fixas=2000,
            num_dependentes=1,
            tem_dividas="não",
        )
        # (4000 / 2001) * 30 + 200 + 80 + 100 ≈ 439
        assert 300 <= score <= 600

    def test_score_clamped_to_1000(self):
        """Score muito alto é clamped para 1000."""
        score = calculate_score(
            renda_mensal=100000,
            tipo_emprego="formal",
            despesas_fixas=100,
            num_dependentes=0,
            tem_dividas="não",
        )
        assert score == 1000

    def test_score_clamped_to_0(self):
        """Score negativo é clamped para 0."""
        score = calculate_score(
            renda_mensal=0,
            tipo_emprego="desempregado",
            despesas_fixas=5000,
            num_dependentes=4,
            tem_dividas="sim",
        )
        assert score == 0

    def test_accent_insensitive_employment(self):
        """Aceita 'autonomo' sem acento."""
        score = calculate_score(
            renda_mensal=5000,
            tipo_emprego="autonomo",
            despesas_fixas=2000,
            num_dependentes=0,
            tem_dividas="nao",
        )
        assert score > 0

    def test_accent_insensitive_debts(self):
        """Aceita 'nao' sem acento."""
        score = calculate_score(
            renda_mensal=3000,
            tipo_emprego="formal",
            despesas_fixas=1000,
            num_dependentes=2,
            tem_dividas="nao",
        )
        assert score > 0

    def test_three_plus_dependents(self):
        """3+ dependentes usa peso de 30."""
        score_0 = calculate_score(
            renda_mensal=5000,
            tipo_emprego="formal",
            despesas_fixas=2000,
            num_dependentes=0,
            tem_dividas="não",
        )
        score_5 = calculate_score(
            renda_mensal=5000,
            tipo_emprego="formal",
            despesas_fixas=2000,
            num_dependentes=5,
            tem_dividas="não",
        )
        # 0 dependentes dá mais score que 5
        assert score_0 > score_5

    def test_zero_expenses(self):
        """Divisão por (despesas + 1) evita divisão por zero."""
        score = calculate_score(
            renda_mensal=5000,
            tipo_emprego="formal",
            despesas_fixas=0,
            num_dependentes=0,
            tem_dividas="não",
        )
        # (5000 / 1) * 30 + 300 + 100 + 100 = big number → clamped to 1000
        assert score == 1000
