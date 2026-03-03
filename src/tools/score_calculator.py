# Calculadora de score de crédito com fórmula ponderada.
#
# A fórmula combina renda, tipo de emprego, dependentes e dívidas
# para gerar um score de 0 a 1000. Os pesos são configuráveis.

from __future__ import annotations

import logging

logger = logging.getLogger("banco_agil.score_calculator")

# Pesos da fórmula (ajustáveis)
PESO_RENDA: int = 30

PESO_EMPREGO: dict[str, int] = {
    "formal": 300,
    "autônomo": 200,
    "autonomo": 200,   # sem acento, para robustez
    "desempregado": 0,
}

PESO_DEPENDENTES: dict[int | str, int] = {
    0: 100,
    1: 80,
    2: 60,
    "3+": 30,
}

PESO_DIVIDAS: dict[str, int] = {
    "sim": -100,
    "não": 100,
    "nao": 100,  # sem acento
}


def calculate_score(
    renda_mensal: float,
    tipo_emprego: str,
    despesas_fixas: float,
    num_dependentes: int,
    tem_dividas: str,
) -> int:
    """Calcula o score de crédito com base nos dados financeiros.

    Fórmula:
        score = (renda / (despesas + 1)) * peso_renda
              + peso_emprego[tipo_emprego]
              + peso_dependentes[num_dependentes]
              + peso_dividas[tem_dividas]

    Args:
        renda_mensal: Renda mensal em R$.
        tipo_emprego: 'formal', 'autônomo' ou 'desempregado'.
        despesas_fixas: Despesas fixas mensais em R$.
        num_dependentes: Número de dependentes (0, 1, 2, 3+).
        tem_dividas: 'sim' ou 'não'.

    Returns:
        Score entre 0 e 1000.
    """
    # Componente de renda
    componente_renda = (renda_mensal / (despesas_fixas + 1)) * PESO_RENDA

    # Componente de emprego
    tipo_emprego_lower = tipo_emprego.lower().strip()
    componente_emprego = PESO_EMPREGO.get(tipo_emprego_lower, 0)

    # Componente de dependentes
    if num_dependentes >= 3:
        componente_dependentes = PESO_DEPENDENTES["3+"]
    else:
        componente_dependentes = PESO_DEPENDENTES.get(num_dependentes, 30)

    # Componente de dívidas
    tem_dividas_lower = tem_dividas.lower().strip()
    componente_dividas = PESO_DIVIDAS.get(tem_dividas_lower, 0)

    # Score bruto
    score_bruto = (
        componente_renda
        + componente_emprego
        + componente_dependentes
        + componente_dividas
    )

    # Clamp 0-1000
    score_final = max(0, min(1000, int(score_bruto)))

    logger.info(
        "Score calculado: renda=%.0f desp=%.0f emprego=%s dep=%d div=%s → %d "
        "(bruto=%.1f = %.1f + %d + %d + %d)",
        renda_mensal,
        despesas_fixas,
        tipo_emprego,
        num_dependentes,
        tem_dividas,
        score_final,
        score_bruto,
        componente_renda,
        componente_emprego,
        componente_dependentes,
        componente_dividas,
    )
    return score_final
