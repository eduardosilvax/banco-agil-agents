"""Guardrails - camada de validacao ANTES e DEPOIS do LLM.

Implementados como middleware, nao como agentes separados no grafo.
Isso evita latencia extra e complexidade de routing no LangGraph,
enquanto adiciona defesa em profundidade.

Uso:
    from src.core.guardrails import InputGuardrail, OutputGuardrail
    guardrail = InputGuardrail()
    result = guardrail.apply(user_text)
    if result.blocked:
        return result.reason
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

security_logger = logging.getLogger("banco_agil.security")


@dataclass
class GuardrailResult:
    """Resultado da validacao de guardrail."""

    text: str
    blocked: bool = False
    reason: str | None = None


# Padroes de prompt injection (PT-BR e EN)
_INJECTION_PATTERNS = [
    r"ignor[ea]\s+(as\s+)?(suas\s+)?instru",
    r"ignore\s+(previous|all|your)\s+instructions",
    r"forget\s+(previous|all|your)\s+instructions",
    r"you\s+are\s+now\s+a",
    r"agora\s+voc",
    r"act\s+as\s+if\s+you\s+are",
    r"override\s+(system|your)\s+prompt",
    r"system\s*prompt",
    r"jailbreak",
    r"DAN\s+mode",
    r"\[SYSTEM\]",
    r"<\s*system\s*>",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# Padrao para CPF completo (11 digitos seguidos ou formatado)
_CPF_FULL_RE = re.compile(r"\b(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\b")


class InputGuardrail:
    """Validacao de entrada do usuario ANTES do LLM.

    Pipeline: sanitize -> detect injection -> retorna resultado.
    Roda em <1ms, sem custo de tokens.
    """

    @staticmethod
    def sanitize(text: str) -> str:
        """Remove caracteres perigosos e normaliza Unicode."""
        text = unicodedata.normalize("NFC", text)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return text.strip()

    @staticmethod
    def detect_prompt_injection(text: str) -> bool:
        """Detecta tentativas de prompt injection via heuristicas."""
        return bool(_INJECTION_RE.search(text))

    def apply(self, text: str) -> GuardrailResult:
        """Pipeline completo de validacao de input."""
        sanitized = self.sanitize(text)

        if not sanitized:
            return GuardrailResult(
                text="",
                blocked=True,
                reason="Mensagem vazia.",
            )

        if self.detect_prompt_injection(sanitized):
            security_logger.warning(
                "guardrail_blocked | type=prompt_injection | preview=%s",
                sanitized[:50],
            )
            return GuardrailResult(
                text=sanitized,
                blocked=True,
                reason="Mensagem bloqueada por politica de seguranca.",
            )

        return GuardrailResult(text=sanitized)


class OutputGuardrail:
    """Validacao da resposta do LLM ANTES de enviar ao usuario."""

    @staticmethod
    def mask_cpf(text: str) -> str:
        """Mascara CPFs nas respostas do LLM.

        123.456.789-01 -> 123.***.***-01
        """

        def _mask(match: re.Match) -> str:
            g1 = match.group(1)
            g4 = match.group(4)
            return f"{g1}.***.***-{g4}"

        return _CPF_FULL_RE.sub(_mask, text)

    def apply(self, text: str) -> str:
        """Pipeline completo de validacao de output."""
        text = self.mask_cpf(text)
        text = self.escape_currency(text)
        return text

    @staticmethod
    def escape_currency(text: str) -> str:
        """Escapa R$ para R\\$ evitando que Streamlit interprete como LaTeX.

        Streamlit usa $ como delimitador de math inline. Sem o escape,
        'R$ 5.000' vira LaTeX quebrado (texto verde em fundo preto).
        """
        # Só escapa R$ que ainda não está escapado (R\$)
        return re.sub(r"R\$(?!\\)", r"R\\$", text)
