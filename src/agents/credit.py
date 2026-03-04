# Agente de Crédito — consulta e aumento de limite.
#
# Responsabilidades:
# 1. Consultar limite de crédito disponível
# 2. Processar solicitação de aumento de limite
# 3. Verificar score vs tabela score_limite.csv
# 4. Registrar pedido em solicitacoes_aumento_limite.csv
# 5. Se rejeitado: oferecer Entrevista de Crédito
# 6. Handoff para credit_interview ou encerramento

from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage, HumanMessage

from src.core.llm_factory import LLMFactory
from src.schemas.state import BankState
from src.tools.csv_tools import (
    check_score_limit,
    get_client_credit,
    register_credit_request,
)

logger = logging.getLogger("banco_agil.credit")

_CREDIT_SYSTEM_PROMPT = """\
Você é o especialista em crédito do Banco Ágil.

Sua função é auxiliar o cliente com questões de limite de crédito.
Seja claro, objetivo e atencioso.

O cliente já foi autenticado. Seus dados são:
- Nome: {nome}
- Score: {score}
- Limite atual: R$ {limite:,.2f}

Responda de forma natural e amigável.
"""

_EXTRACT_VALUE_PROMPT = """\
Extraia o valor monetário que o cliente deseja como novo limite de crédito.
Responda APENAS com o número (sem R$, sem pontos de milhar). Use ponto como separador decimal.
Se não houver valor claro, responda "0".

Mensagem: {message}

Valor:"""


class CreditAgent:
    """Agente de Crédito — consulta de limite e processamento de aumento.

    Fluxo:
    1. Mostra informações de crédito do cliente
    2. Cliente pode solicitar aumento de limite
    3. Sistema verifica score e aprova/rejeita
    4. Se rejeitado, oferece Entrevista de Crédito
    """

    def __init__(self, llm_factory: LLMFactory) -> None:
        self._llm = llm_factory.get_llm(temp=0.3)
        self._llm_factory = llm_factory

    def run(self, state: BankState) -> dict:
        """Nó LangGraph: executa lógica de crédito."""
        messages = state.get("messages", [])
        client_data = state.get("client_data", {})
        credit_request_data = state.get("credit_request_data")

        cpf = client_data.get("cpf", "")
        nome = client_data.get("nome", "Cliente")
        first_name = nome.split()[0]

        # Buscar dados atualizados de crédito
        credit_info = get_client_credit(cpf)
        if not credit_info:
            error_msg = (
                "Desculpe, não consegui acessar suas informações de crédito no momento. "
                "Por favor, tente novamente mais tarde ou entre em contato com nossa central."
            )
            return {
                "messages": [AIMessage(content=error_msg)],
                "current_agent": "triage",
            }

        score = credit_info["score"]
        current_limit = credit_info["limite_credito"]

        # Se a última mensagem adicionada é uma resposta do agente (ex: vinda da entrevista)
        # e o agente atual mudou para 'credit', nós não processamos a mensagem do usuário novamente.
        if messages and isinstance(messages[-1], AIMessage):
             # Isso garante que se acabamos de retornar de outro agente de forma assíncrona/handoff
             # nós não reprocessamos a resposta anterior do usuário.
             return {"current_agent": "credit"}

        # Verificar a última mensagem do usuário
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        if not human_messages:
            return self._show_credit_info(first_name, score, current_limit)

        last_message = human_messages[-1].content.lower()

        # Verificar se quer encerrar
        if self._wants_to_end(last_message):
            farewell = (
                f"Certo, {first_name}! 😊 Se precisar de algo mais, estou aqui. "
                f"Obrigado por usar o Banco Ágil! 👋"
            )
            return {
                "messages": [AIMessage(content=farewell)],
                "should_end": True,
                "current_agent": "credit",
            }

        # Verificar se quer ir para outro serviço
        if self._wants_exchange(last_message):
            return {
                "messages": [AIMessage(content=f"Claro, {first_name}! Vou consultar a cotação para você. 💱")],
                "current_agent": "exchange",
            }

        # Verificar se mencionou entrevista de crédito
        if self._wants_interview(last_message, credit_request_data):
            response = (
                f"Ótima escolha, {first_name}! 📝 Vamos iniciar uma breve entrevista "
                f"para reavaliar seu perfil de crédito.\n\n"
                f"Isso pode melhorar seu score e, consequentemente, seu limite disponível."
            )
            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "credit_interview",
            }

        # Verificar se solicitou aumento ou se menciona um valor
        requested_value = self._extract_value(human_messages[-1].content)

        if requested_value and requested_value > 0:
            return self._process_limit_increase(
                cpf, first_name, score, current_limit, requested_value
            )

        # Checar intenção geral
        if self._wants_increase(last_message, credit_request_data):
            response = (
                f"{first_name}, para solicitar um aumento de limite, "
                f"me informe o **valor desejado** para seu novo limite.\n\n"
                f"Seu limite atual é de **R$ {current_limit:,.2f}**.\n"
                f"Qual valor gostaria de solicitar?"
            )
            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "credit",
            }

        # Se quer apenas consultar ou é a primeira interação
        if self._wants_credit_info(last_message) or not credit_request_data:
            return self._show_credit_info(first_name, score, current_limit)

        # Resposta genérica
        response = (
            f"{first_name}, posso te ajudar com:\n\n"
            f"• 📊 **Consultar** seu limite e score de crédito\n"
            f"• 📈 **Solicitar aumento** de limite (informe o valor desejado)\n"
            f"• 💱 **Câmbio** — Consultar cotação de moedas\n\n"
            f"O que deseja?"
        )
        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "credit",
        }

    def _show_credit_info(self, name: str, score: int, limit: float) -> dict:
        """Exibe informações de crédito do cliente."""
        response = (
            f"Aqui estão suas informações de crédito, {name}:\n\n"
            f"• **Score de crédito:** {score} pontos\n"
            f"• **Limite atual:** R$ {limit:,.2f}\n\n"
            f"Deseja **solicitar um aumento de limite**? "
            f"Se sim, me informe o valor desejado. 😊"
        )
        return {
            "messages": [AIMessage(content=response)],
            "current_agent": "credit",
            "credit_request_data": {"status": "info_shown"},
        }

    def _process_limit_increase(
        self,
        cpf: str,
        name: str,
        score: int,
        current_limit: float,
        requested_limit: float,
    ) -> dict:
        """Processa uma solicitação de aumento de limite."""

        if requested_limit <= current_limit:
            response = (
                f"{name}, o valor solicitado (R$ {requested_limit:,.2f}) é igual ou inferior "
                f"ao seu limite atual (R$ {current_limit:,.2f}).\n\n"
                f"Por favor, informe um valor **maior** que o limite atual."
            )
            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "credit",
            }

        # Verificar se o score permite
        result = check_score_limit(score, requested_limit)

        if result["approved"]:
            # Aprovado — registrar
            register_credit_request(cpf, current_limit, requested_limit, "aprovado")

            response = (
                f"🎉 **Solicitação aprovada!**\n\n"
                f"Seu pedido de aumento de limite foi **aprovado**:\n\n"
                f"• Limite anterior: R$ {current_limit:,.2f}\n"
                f"• Novo limite: R$ {requested_limit:,.2f}\n"
                f"• Score atual: {score} pontos\n\n"
                f"O novo limite já está disponível, {name}! "
                f"Posso te ajudar com mais alguma coisa?"
            )
            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "credit",
                "credit_request_data": {
                    "requested": requested_limit,
                    "status": "aprovado",
                },
            }
        else:
            # Rejeitado — registrar e oferecer entrevista
            register_credit_request(cpf, current_limit, requested_limit, "rejeitado")

            response = (
                f"😔 **Solicitação não aprovada**\n\n"
                f"{result['reason']}\n\n"
                f"Mas não se preocupe, {name}! Temos uma alternativa:\n\n"
                f"📝 Posso te direcionar para uma **entrevista de crédito** rápida. "
                f"Nela coletamos alguns dados financeiros atualizados e recalculamos "
                f"seu score, o que pode aumentar seu limite disponível.\n\n"
                f"**Deseja fazer a entrevista de crédito?** (sim/não)"
            )
            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "credit",
                "credit_request_data": {
                    "requested": requested_limit,
                    "status": "rejeitado",
                },
            }

    def _extract_value(self, text: str) -> float | None:
        """Extrai valor monetário de uma mensagem."""
        text_clean = text.lower().replace("r$", "").strip()

        # Tratar os 'k' (ex: 30k)
        k_match = re.search(r"(\d+(?:[.,]\d+)?)\s*k\b", text_clean)
        if k_match:
            val_str = k_match.group(1).replace(",", ".")
            return float(val_str) * 1000

        # Pega qualquer sequencia de digitos com possiveis pontos ou virgulas
        number_match = re.search(r"\b(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\b", text_clean)
        if number_match:
            raw = number_match.group(1)
            # conta quantos digitos apos ultimo delimitador
            if ',' in raw and '.' in raw:
                # ex 5.000,00
                val_str = raw.replace('.', '').replace(',', '.')
                return float(val_str)
            elif ',' in raw:
                parts = raw.split(',')
                if len(parts[-1]) in [1, 2]:
                    return float(raw.replace(',', '.'))
                else:
                    return float(raw.replace(',', ''))
            elif '.' in raw:
                parts = raw.split('.')
                if len(parts[-1]) in [1, 2]:
                    return float(raw)
                else:
                    return float(raw.replace('.', ''))
            else:
                return float(raw)

        # Tenta via LLM como fallback
        try:
            prompt = _EXTRACT_VALUE_PROMPT.format(message=text)
            response = self._llm.invoke([HumanMessage(content=prompt)])
            value_str = response.content.strip().replace(",", ".")
            value = float(value_str)
            return value if value > 0 else None
        except Exception:
            return None

    @staticmethod
    def _wants_to_end(message: str) -> bool:
        end_patterns = [
            r"\b(sair|encerrar|tchau|adeus|finalizar|obrigad[oa])\b",
            r"\b(bye|exit|quit)\b",
        ]
        return any(re.search(p, message.lower()) for p in end_patterns)

    @staticmethod
    def _wants_increase(message: str, credit_request_data: dict | None = None) -> bool:
        msg_lower = message.lower().strip()
        
        # Se exibimos a info de crédito e perguntamos "Deseja solicitar aumento?", e o usuário diz sim
        if credit_request_data and credit_request_data.get("status") in ["info_shown"]:
            # Aceita apenas respostas curtas afirmativas, pois se ele descrever a intenção as regras normais pegam.
            if re.match(r"^(sim|isso|exato|positivo|com certeza|quero|gostaria|pode ser|bora|vamos)[!\.,\s]*$", msg_lower):
                return True
                
        patterns = [
            r"\b(aument|subi|elev|altera|muda|alter|mais|maior|novo)\w*\b.*\b(limit|cr[eé]dit)\w*\b",
            r"\b(limit|cr[eé]dit)\w*\b.*\b(aument|subi|elev|maior|alter|mais|novo)\w*\b",
            r"\b(quero|gostaria|preciso|queria)\b.*\b(aumenta|mais limite|limite maior)\b",
        ]
        return any(re.search(p, msg_lower) for p in patterns)

    @staticmethod
    def _wants_credit_info(message: str) -> bool:
        patterns = [
            r"\b(consult|ver|mostr|inform|saber|qual)\w*\b.*\b(limit|crédit|score)\w*\b",
            r"\b(limit|crédit|score)\b",
            r"\b(meu limite|meu score)\b",
        ]
        msg_lower = message.lower()
        return any(re.search(p, msg_lower) for p in patterns)

    @staticmethod
    def _wants_exchange(message: str) -> bool:
        patterns = [r"\b(câmbio|cambio|cotação|cotacao|dólar|dolar|euro|moeda)\b"]
        return any(re.search(p, message.lower()) for p in patterns)

    @staticmethod
    def _wants_interview(message: str, credit_request_data: dict | None = None) -> bool:
        msg_lower = message.lower()
        
        # Se um aumento foi rejeitado recentemente e a entrevista foi oferecida
        if credit_request_data and credit_request_data.get("status") == "rejeitado":
            patterns = [
                r"\b(sim|quero|aceito|bora|vamos|pode|claro|ok)\b",
                r"\b(entrevista|entr)\w*\b",
            ]
        else:
            # Caso contrário, exige que o usuário cite 'entrevista' explicitamente
            patterns = [
                r"\b(entrevista|entr)\w*\b",
            ]
            
        return any(re.search(p, msg_lower) for p in patterns)
