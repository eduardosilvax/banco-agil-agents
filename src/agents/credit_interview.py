# Agente de Entrevista de Crédito — recalcula score via entrevista conversacional.
#
# Fluxo:
# 1. Coleta renda mensal
# 2. Coleta tipo de emprego (formal, autônomo, desempregado)
# 3. Coleta despesas fixas mensais
# 4. Coleta número de dependentes
# 5. Coleta existência de dívidas ativas
# 6. Calcula novo score com fórmula ponderada
# 7. Atualiza score no clientes.csv
# 8. Redireciona de volta para o Agente de Crédito

from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage, HumanMessage

from src.core.llm_factory import LLMFactory
from src.schemas.state import BankState
from src.tools.csv_tools import update_client_score
from src.tools.score_calculator import calculate_score

logger = logging.getLogger("banco_agil.credit_interview")

# Perguntas da entrevista (em ordem)
_INTERVIEW_QUESTIONS = [
    {
        "field": "renda_mensal",
        "question": (
            "Vamos começar a entrevista! 📝\n\n"
            "**Pergunta 1/5:** Qual é sua **renda mensal** bruta (em R$)?"
        ),
        "type": "float",
    },
    {
        "field": "tipo_emprego",
        "question": (
            "**Pergunta 2/5:** Qual é seu **tipo de emprego** atual?\n\n"
            "• **Formal** (CLT, servidor público)\n"
            "• **Autônomo** (freelancer, MEI, profissional liberal)\n"
            "• **Desempregado**"
        ),
        "type": "employment",
    },
    {
        "field": "despesas_fixas",
        "question": (
            "**Pergunta 3/5:** Qual o valor total das suas **despesas fixas mensais** (em R$)?\n\n"
            "Inclua: aluguel, contas, parcelas, etc."
        ),
        "type": "float",
    },
    {
        "field": "num_dependentes",
        "question": (
            "**Pergunta 4/5:** Quantos **dependentes** você possui?\n\n"
            "(filhos, cônjuge, etc. Informe o número: 0, 1, 2, 3 ou mais)"
        ),
        "type": "int",
    },
    {
        "field": "tem_dividas",
        "question": (
            "**Pergunta 5/5:** Você possui **dívidas ativas** no momento?\n\n"
            "(empréstimos em aberto, cartão atrasado, etc.)\n"
            "Responda: **sim** ou **não**"
        ),
        "type": "boolean",
    },
]


class CreditInterviewAgent:
    """Agente de Entrevista de Crédito — coleta dados e recalcula score.

    Conduz 5 perguntas de forma conversacional, calcula score e
    redireciona de volta ao Agente de Crédito.
    """

    def __init__(self, llm_factory: LLMFactory) -> None:
        self._llm = llm_factory.get_llm(temp=0.2)

    def run(self, state: BankState) -> dict:
        """Nó LangGraph: executa entrevista de crédito."""
        messages = state.get("messages", [])
        client_data = state.get("client_data", {})
        interview_data = state.get("interview_data") or {}

        nome = client_data.get("nome", "Cliente")
        first_name = nome.split()[0]
        cpf = client_data.get("cpf", "")

        human_messages = [m for m in messages if isinstance(m, HumanMessage)]

        # Verificar se quer encerrar
        if human_messages:
            last_msg = human_messages[-1].content.lower()
            if self._wants_to_end(last_msg):
                farewell = (
                    f"Tudo bem, {first_name}! A entrevista foi cancelada. "
                    f"Se mudar de ideia, estou aqui. 😊\n\n"
                    f"Posso te ajudar com mais alguma coisa?"
                )
                return {
                    "messages": [AIMessage(content=farewell)],
                    "current_agent": "triage",
                    "interview_data": None,
                }

        # Determinar em qual pergunta estamos
        current_step = len(interview_data)

        # Se temos uma resposta pendente para processar
        if human_messages and current_step > 0 and current_step <= len(_INTERVIEW_QUESTIONS):
            prev_question = _INTERVIEW_QUESTIONS[current_step - 1]
            last_answer = human_messages[-1].content

            parsed_value = self._parse_answer(last_answer, prev_question["type"])

            if parsed_value is None:
                # Resposta inválida — pedir novamente
                error_msg = self._get_error_message(prev_question["type"])
                return {
                    "messages": [AIMessage(content=error_msg)],
                    "current_agent": "credit_interview",
                }

            interview_data[prev_question["field"]] = parsed_value

        # Verificar se completou todas as perguntas
        if len(interview_data) >= len(_INTERVIEW_QUESTIONS):
            return self._finalize_interview(cpf, first_name, interview_data, client_data)

        # Fazer a próxima pergunta
        next_question = _INTERVIEW_QUESTIONS[len(interview_data)]
        return {
            "messages": [AIMessage(content=next_question["question"])],
            "current_agent": "credit_interview",
            "interview_data": interview_data,
        }

    def _finalize_interview(
        self,
        cpf: str,
        name: str,
        data: dict,
        client_data: dict,
    ) -> dict:
        """Calcula novo score e redireciona para o Agente de Crédito."""
        old_score = client_data.get("score", 0)

        # Calcular novo score
        new_score = calculate_score(
            renda_mensal=data["renda_mensal"],
            tipo_emprego=data["tipo_emprego"],
            despesas_fixas=data["despesas_fixas"],
            num_dependentes=data["num_dependentes"],
            tem_dividas=data["tem_dividas"],
        )

        # Atualizar no CSV
        updated = update_client_score(cpf, new_score)

        # Atualizar score no client_data em memória
        updated_client = {**client_data, "score": new_score}

        if updated:
            diff = new_score - old_score
            diff_emoji = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
            diff_text = f"+{diff}" if diff > 0 else str(diff)

            response = (
                f"✅ **Entrevista finalizada!**\n\n"
                f"Aqui está o resultado da sua reavaliação, {name}:\n\n"
                f"• Score anterior: **{old_score}** pontos\n"
                f"• Score atualizado: **{new_score}** pontos {diff_emoji} ({diff_text})\n\n"
                f"{'Ótimas notícias! Seu score melhorou! 🎉' if diff > 0 else ''}"
                f"\n\nVou verificar novamente suas opções de crédito com o score atualizado..."
            )
            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "credit",
                "client_data": updated_client,
                "interview_data": None,
            }
        else:
            response = (
                f"Ocorreu um erro ao atualizar seu score, {name}. "
                f"Por favor, tente novamente mais tarde."
            )
            return {
                "messages": [AIMessage(content=response)],
                "current_agent": "triage",
                "interview_data": None,
            }

    def _parse_answer(self, text: str, answer_type: str) -> any:
        """Parseia a resposta do usuário conforme o tipo esperado."""
        text = text.strip()

        if answer_type == "float":
            # Extrai número (aceita 5000, 5.000, 5.000,00, R$ 5000)
            clean = text.lower().replace("r$", "").replace("reais", "").strip()
            clean = re.sub(r"[^\d.,]", "", clean)
            if not clean:
                return None

            # Formato brasileiro: 5.000,50
            if "," in clean:
                clean = clean.replace(".", "").replace(",", ".")

            try:
                value = float(clean)
                return value if value >= 0 else None
            except ValueError:
                return None

        elif answer_type == "employment":
            text_lower = text.lower()
            if any(w in text_lower for w in ["formal", "clt", "servidor", "registrad"]):
                return "formal"
            elif any(w in text_lower for w in ["autônom", "autonom", "freelanc", "mei", "liberal"]):
                return "autônomo"
            elif any(w in text_lower for w in ["desempreg", "sem emprego", "não trabalh", "nao trabalh"]):
                return "desempregado"
            return None

        elif answer_type == "int":
            match = re.search(r"\d+", text)
            if match:
                return int(match.group(0))
            text_lower = text.lower()
            if any(w in text_lower for w in ["nenhum", "zero", "não", "nao"]):
                return 0
            return None

        elif answer_type == "boolean":
            text_lower = text.lower()
            if any(w in text_lower for w in ["sim", "tenho", "possuo", "yes", "s"]):
                return "sim"
            elif any(w in text_lower for w in ["não", "nao", "no", "n", "nenhuma"]):
                return "não"
            return None

        return None

    @staticmethod
    def _get_error_message(answer_type: str) -> str:
        """Retorna mensagem de erro adequada para cada tipo."""
        errors = {
            "float": "Não consegui entender o valor. Por favor, informe um número (ex: 5000 ou 5.000,00).",
            "employment": (
                "Não entendi. Por favor, responda com uma das opções:\n"
                "• **Formal** (CLT, servidor)\n"
                "• **Autônomo** (freelancer, MEI)\n"
                "• **Desempregado**"
            ),
            "int": "Não entendi. Por favor, informe um número (ex: 0, 1, 2, 3).",
            "boolean": "Não entendi. Por favor, responda **sim** ou **não**.",
        }
        return errors.get(answer_type, "Desculpe, não entendi. Pode repetir?")

    @staticmethod
    def _wants_to_end(message: str) -> bool:
        patterns = [
            r"\b(sair|encerrar|cancelar|desistir|parar)\b",
        ]
        return any(re.search(p, message.lower()) for p in patterns)
