# Estado conversacional compartilhado entre todos os agentes via LangGraph.
#
# Cada agente lê e escreve campos específicos deste TypedDict.
# O LangGraph garante que o estado é passado corretamente entre nós.

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class BankState(TypedDict):
    """Estado global do grafo de atendimento bancário.

    Campos principais:
    - messages: histórico de mensagens (LangGraph gerencia via add_messages)
    - authenticated: flag de autenticação do cliente
    - client_data: dados completos do cliente autenticado
    - current_agent: identificador do agente ativo
    - auth_attempts: contador de tentativas falhas de autenticação
    - should_end: flag para encerrar a conversa
    """

    # Histórico de mensagens — gerenciado pelo LangGraph (append automático)
    messages: Annotated[list, add_messages]

    # Autenticação
    authenticated: bool
    client_data: dict[str, Any] | None
    auth_attempts: int
    collected_cpf: str | None
    collected_birth_date: str | None

    # Roteamento
    current_agent: str

    # Crédito
    credit_request_data: dict[str, Any] | None

    # Entrevista de crédito
    interview_data: dict[str, Any] | None

    # Compliance
    compliance_approved: bool
    compliance_reason: str | None

    # Controle de fluxo
    should_end: bool
