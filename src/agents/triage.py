# Agente de Triagem — porta de entrada do atendimento.
#
# Responsabilidades:
# 1. Saudação inicial
# 2. Coleta de CPF
# 3. Coleta de data de nascimento
# 4. Autenticação contra clientes.csv
# 5. Até 3 tentativas (falha → encerramento amigável)
# 6. Após autenticação: identificação do assunto + handoff
#
# O agente usa LLM para conversação natural, mas a autenticação
# é feita via tools (csv_tools.authenticate_client).

from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents._helpers import wants_to_end
from src.core.llm_factory import LLMFactory
from src.schemas.state import BankState
from src.tools.csv_tools import authenticate_client

logger = logging.getLogger("banco_agil.triage")

_TRIAGE_SYSTEM_PROMPT = """\
Você é o atendente virtual do Banco Ágil, um banco digital moderno e acolhedor.

SUA FUNÇÃO: Recepcionar o cliente, autenticá-lo (CPF + data de nascimento) e \
direcioná-lo para o serviço correto.

## REGRAS DE ATENDIMENTO:

1. **Saudação**: Cumprimente o cliente de forma calorosa e profissional.
2. **Coleta de CPF**: Peça o CPF de forma educada. Aceite com ou sem formatação.
3. **Coleta de data de nascimento**: Após receber o CPF, peça a data de nascimento.
4. **Tom**: Respeitoso, objetivo, sem repetições desnecessárias.
5. **Encerramento**: Se o cliente pedir para encerrar, despeça-se educadamente.

## IDENTIFICAÇÃO DE ASSUNTO (após autenticação):
Identifique o assunto da solicitação e indique uma das opções:
- **credito**: consulta de limite, aumento de limite, questões sobre crédito
- **cambio**: cotação de moedas, câmbio, dólar, euro
- **sair**: cliente quer encerrar

## FORMATO DE RESPOSTA:
Responda de forma natural e amigável. NÃO use JSON nem formatos técnicos.
Fale como um atendente humano faria.
"""

_ROUTE_PROMPT = """\
Com base na mensagem do cliente, identifique o assunto desejado.

Responda com APENAS UMA PALAVRA:
- "credito" se o cliente quer consultar/aumentar limite de crédito
- "cambio" se o cliente quer consultar cotação de moedas
- "sair" se quer encerrar
- "indefinido" se não ficou claro

Mensagem do cliente: {message}

Resposta (uma palavra):"""


def _extract_cpf(text: str) -> str | None:
    """Extrai CPF de uma string (com ou sem formatação)."""
    clean = re.sub(r"[.\-\s]", "", text)
    match = re.search(r"\d{11}", clean)
    return match.group(0) if match else None


def _extract_date(text: str) -> str | None:
    """Extrai data de nascimento de uma string."""
    # Formatos: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, YYYY-MM-DD e DDMMAAAA
    patterns = [
        r"\d{2}/\d{2}/\d{4}",
        r"\d{2}-\d{2}-\d{4}",
        r"\d{2}\.\d{2}\.\d{4}",
        r"\d{4}-\d{2}-\d{2}",
        r"\b\d{8}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


class TriageAgent:
    """Agente de Triagem — autenticação e roteamento inicial.

    Fluxo:
    1. Saudação
    2. Coleta CPF (se necessário)
    3. Coleta data de nascimento (se necessário)
    4. Autenticação (até 3 tentativas)
    5. Identificação do assunto → handoff
    """

    def __init__(self, llm_factory: LLMFactory) -> None:
        self._llm = llm_factory.get_llm(temp=0.3)

    def run(self, state: BankState) -> dict:
        """Nó LangGraph: executa lógica de triagem."""
        messages = state.get("messages", [])
        authenticated = state.get("authenticated", False)
        auth_attempts = state.get("auth_attempts", 0)
        collected_cpf = state.get("collected_cpf")
        collected_birth_date = state.get("collected_birth_date")

        # Se não tem mensagens do usuário, é a saudação inicial
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        if not human_messages:
            greeting = (
                "Olá! Bem-vindo(a) ao **Banco Ágil**! "
                "Sou seu assistente virtual e estou aqui para te ajudar.\n\n"
                "Para começar, preciso verificar sua identidade. "
                "Poderia me informar seu **CPF**?"
            )
            return {
                "messages": [AIMessage(content=greeting)],
                "current_agent": "triage",
            }

        last_message = human_messages[-1].content

        # Verificar se quer encerrar
        if wants_to_end(last_message):
            farewell = (
                "Tudo bem! Obrigado(a) por entrar em contato com o Banco Ágil. "
                "Volte quando precisar. Tenha um ótimo dia!"
            )
            return {
                "messages": [AIMessage(content=farewell)],
                "should_end": True,
                "current_agent": "triage",
            }

        # --- FLUXO DE AUTENTICAÇÃO ---

        # Se já autenticado, identificar o assunto
        if authenticated:
            return self._identify_subject(state, last_message)

        # Passo 1: Coletar CPF
        if not collected_cpf:
            cpf = _extract_cpf(last_message)
            if cpf:
                response = (
                    "Obrigado! CPF recebido.\n\n"
                    "Agora, por favor, informe sua **data de nascimento**. "
                )
                return {
                    "messages": [AIMessage(content=response)],
                    "collected_cpf": cpf,
                    "current_agent": "triage",
                }
            else:
                # Deixar o LLM responder de forma amigável se o usuário não enviou o CPF
                try:
                    sys_msg = SystemMessage(content=_TRIAGE_SYSTEM_PROMPT)
                    _cpf_reminder = (
                        "ATENÇÃO ESTRITA: O sistema técnico não encontrou "
                        "um CPF válido (11 dígitos) na última mensagem do "
                        "usuário. Você NÃO PODE prosseguir com nenhum "
                        "atendimento, NÃO PODE confirmar identidade, e "
                        "NÃO PODE oferecer serviços. Se o usuário fez uma "
                        "pergunta (por exemplo, 'por que preciso informar "
                        "isso?'), responda de forma educada explicando que "
                        "o CPF é necessário para identificação e garantir "
                        "a segurança da conta. Depois, peça que ele "
                        "digite o CPF."
                    )
                    reminder_msg = SystemMessage(content=_cpf_reminder)
                    llm_response = self._llm.invoke([sys_msg] + messages + [reminder_msg])
                    response = llm_response.content
                except Exception as e:
                    logger.error("Erro ao gerar resposta com LLM: %s", e)
                    response = (
                        "Desculpe, não consegui identificar um CPF válido. "
                        "Por favor, informe seu CPF com 11 dígitos "
                        "(exemplo: 123.456.789-01 ou 12345678901)."
                    )

                return {
                    "messages": [AIMessage(content=response)],
                    "current_agent": "triage",
                }

        # Passo 2: Coletar data de nascimento
        if not collected_birth_date:
            date = _extract_date(last_message)
            if date:
                collected_birth_date = date
            else:
                # Deixar o LLM responder de forma amigável
                # se o usuário não enviou a data de nascimento
                try:
                    sys_msg = SystemMessage(content=_TRIAGE_SYSTEM_PROMPT)
                    _date_reminder = (
                        "ATENÇÃO ESTRITA: O sistema técnico rejeitou a "
                        "última mensagem porque não contém uma data "
                        "válida (ex. DD/MM/AAAA). O usuário já informou "
                        "o CPF, mas FALTA A DATA DE NASCIMENTO. Você "
                        "NÃO PODE oferecer serviços, nem concluir a "
                        "autenticação ainda. Se o usuário fez uma "
                        "pergunta (por exemplo, 'por que preciso "
                        "informar isso?'), responda de forma educada "
                        "explicando que a data de nascimento é "
                        "necessária para confirmar sua identidade e "
                        "garantir a segurança da conta. Depois, peça "
                        "novamente a data de nascimento."
                    )
                    reminder_msg = SystemMessage(content=_date_reminder)
                    llm_response = self._llm.invoke(
                        [sys_msg] + messages[:-1] + [messages[-1], reminder_msg]
                    )
                    response = llm_response.content
                except Exception as e:
                    logger.error("Erro ao gerar resposta com LLM: %s", e)
                    response = (
                        "Desculpe, não consegui identificar a data. "
                        "Por favor, informe no formato **DD/MM/AAAA** "
                        "(exemplo: 15/05/1990)."
                    )

                return {
                    "messages": [AIMessage(content=response)],
                    "current_agent": "triage",
                }

        # Passo 3: Autenticação
        client = authenticate_client(collected_cpf, collected_birth_date)

        if client:
            response = (
                f"Autenticação realizada com sucesso!\n\n"
                f"Olá, **{client['nome'].split()[0]}**! Como posso te ajudar hoje?\n\n"
                f"Nossos serviços disponíveis:\n"
                f"• **Crédito** — Consultar limite ou solicitar aumento\n"
                f"• **Câmbio** — Consultar cotação de moedas\n\n"
                f"O que você gostaria de fazer?"
            )
            return {
                "messages": [AIMessage(content=response)],
                "authenticated": True,
                "client_data": client,
                "current_agent": "triage",
                "collected_cpf": collected_cpf,
                "collected_birth_date": collected_birth_date,
            }
        else:
            # Autenticação falhou
            new_attempts = auth_attempts + 1

            if new_attempts >= 3:
                response = (
                    "Infelizmente não conseguimos validar seus dados após 3 tentativas.\n\n"
                    "Por segurança, precisamos encerrar este atendimento. "
                    "Por favor, entre em contato com nossa central pelo **0800-123-4567** "
                    "ou procure uma de nossas agências.\n\n"
                    "Obrigado(a) pela compreensão!"
                )
                return {
                    "messages": [AIMessage(content=response)],
                    "auth_attempts": new_attempts,
                    "should_end": True,
                    "current_agent": "triage",
                    "collected_cpf": None,
                    "collected_birth_date": None,
                }
            else:
                remaining = 3 - new_attempts
                response = (
                    f"Desculpe, não encontrei um cadastro com esses dados.\n\n"
                    f"Você ainda tem **{remaining}** tentativa(s). "
                    f"Vamos tentar de novo — por favor, informe seu **CPF**."
                )
                return {
                    "messages": [AIMessage(content=response)],
                    "auth_attempts": new_attempts,
                    "collected_cpf": None,
                    "collected_birth_date": None,
                    "current_agent": "triage",
                }

    def _identify_subject(self, state: BankState, message: str) -> dict:
        """Identifica o assunto e redireciona para o agente correto."""
        try:
            prompt = _ROUTE_PROMPT.format(message=message)
            response = self._llm.invoke([HumanMessage(content=prompt)])
            route = response.content.strip().lower()
        except Exception as e:
            logger.error("Erro ao identificar assunto: %s", e)
            route = "indefinido"

        client_name = state.get("client_data", {}).get("nome", "").split()[0]

        if "credito" in route or "crédito" in route:
            response_text = f"Perfeito, {client_name}! Vou te ajudar com questões de crédito."
            return {
                "messages": [AIMessage(content=response_text)],
                "current_agent": "credit",
            }
        elif "cambio" in route or "câmbio" in route:
            response_text = f"Claro, {client_name}! Vou consultar a cotação para você."
            return {
                "messages": [AIMessage(content=response_text)],
                "current_agent": "exchange",
            }
        elif "sair" in route:
            farewell = (
                f"Tudo bem, {client_name}! Obrigado(a) por usar o Banco Ágil. "
                f"Volte quando precisar. Tenha um ótimo dia!"
            )
            return {
                "messages": [AIMessage(content=farewell)],
                "should_end": True,
                "current_agent": "triage",
            }
        else:
            response_text = (
                f"{client_name}, não entendi bem o que você precisa. "
                f"Posso te ajudar com:\n\n"
                f"• **Crédito** — Consultar limite ou solicitar aumento\n"
                f"• **Câmbio** — Consultar cotação de moedas\n\n"
                f"O que deseja?"
            )
            return {
                "messages": [AIMessage(content=response_text)],
                "current_agent": "triage",
            }
