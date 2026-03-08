# Utilitários compartilhados entre os agentes de atendimento.
#
# Funções duplicadas 3-4x nos agentes foram extraídas para cá.
# Cada agente importa o que precisa, sem duplicação de lógica.

from __future__ import annotations

import re

from langchain_core.messages import HumanMessage

# Patterns de encerramento — superset de todos os agentes
_END_PATTERNS = [
    r"\b(sair|encerrar|tchau|adeus|finalizar|fechar|obrigad[oa]|cancelar|desistir|parar)\b",
    r"\b(bye|exit|quit|close)\b",
]


def wants_to_end(message: str) -> bool:
    """Verifica se o usuário quer encerrar o atendimento."""
    msg_lower = message.lower()
    return any(re.search(p, msg_lower) for p in _END_PATTERNS)


# Patterns de saudação / conversa casual
_GREETING_PATTERNS = [
    r"\b(ol[aá]|oi|hey|e\s*a[ií]|bom\s*dia|boa\s*(tarde|noite)|fala|salve)\b",
    r"\b(tudo\s*bem|como\s*vai|como\s*voc[eê]|tudo\s*certo|tudo\s*bom|beleza)\b",
    r"\b(hi|hello|hey\s*there|good\s*(morning|afternoon|evening))\b",
]


def is_greeting(message: str) -> bool:
    """Detecta se a mensagem é uma saudação ou conversa casual."""
    msg_lower = message.lower()
    return any(re.search(p, msg_lower) for p in _GREETING_PATTERNS)


def first_name(full_name: str) -> str:
    """Extrai o primeiro nome de um nome completo."""
    return full_name.split()[0] if full_name.strip() else "Cliente"


def format_brl(value: float) -> str:
    """Formata valor monetário no padrão brasileiro (R$ 5.000,00)."""
    formatted = f"{value:,.2f}"
    # Troca: vírgula→placeholder, ponto→vírgula, placeholder→ponto
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def get_human_messages(messages: list) -> list[HumanMessage]:
    """Filtra apenas mensagens do usuário (HumanMessage)."""
    return [m for m in messages if isinstance(m, HumanMessage)]
