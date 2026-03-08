# Orquestrador LangGraph — conecta os 4 agentes num grafo de atendimento.
#
# Fluxo:
# START → entry_router → (triage | credit | credit_interview | exchange)
# credit ↔ credit_interview (handoffs bidirecionais)
# Qualquer agente pode encerrar via should_end → END
#
# O roteamento é controlado pelo campo `current_agent` no state.
# Transições são implícitas — o cliente percebe um único atendente.

from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from src.agents.compliance import ComplianceAgent
from src.agents.credit import CreditAgent
from src.agents.credit_interview import CreditInterviewAgent
from src.agents.exchange import ExchangeAgent
from src.agents.triage import TriageAgent
from src.core.llm_factory import LLMFactory
from src.schemas.state import BankState

logger = logging.getLogger("banco_agil.graph")

_VALID_AGENTS = {"triage", "credit", "credit_interview", "exchange"}

# Número máximo de mensagens mantidas no contexto (system + últimas N)
_MAX_MESSAGES = 20


def _trim_messages(state: BankState) -> dict:
    """Limita o histórico de mensagens para evitar explosão de tokens.

    Mantém a primeira mensagem (system/context) + as últimas _MAX_MESSAGES-1.
    """
    messages = state.get("messages", [])
    if len(messages) <= _MAX_MESSAGES:
        return {}
    trimmed = messages[:1] + messages[-(_MAX_MESSAGES - 1) :]
    logger.info("Histórico trimmed: %d → %d mensagens", len(messages), len(trimmed))
    return {"messages": trimmed}


def _entry_router(state: BankState) -> str:
    """Router de entrada: direciona para o agente correto baseado no state.

    Na primeira invocação current_agent será 'triage'.
    Nas invocações seguintes, preserva o agente ativo (ex: credit_interview
    durante a entrevista de crédito).
    """
    if state.get("should_end", False):
        return END

    agent = state.get("current_agent", "triage")
    if agent in _VALID_AGENTS:
        logger.info("Entry router → '%s'", agent)
        return agent
    return "triage"


def _make_router(source_node: str):
    """Cria um router condicional específico para cada nó.

    Lógica:
    1. Se should_end=True → END
    2. Se current_agent mudou para outro agente → vai pro novo agente
    3. Se current_agent == source_node (permanece no mesmo) → END (espera próxima mensagem)
    """

    def _router(state: BankState) -> str:
        if state.get("should_end", False):
            logger.info("Conversa encerrada (should_end=True)")
            return END

        agent = state.get("current_agent", "triage")

        # Se o agente quer ficar no mesmo nó, paramos e esperamos
        # a próxima mensagem do usuário.
        if agent == source_node:
            logger.info("Agente '%s' aguardando próxima mensagem → END", agent)
            return END

        if agent in _VALID_AGENTS:
            logger.info("Roteando de '%s' para '%s'", source_node, agent)
            return agent

        return END

    return _router


def _compliance_router(state: BankState) -> str:
    """Router pós-compliance: se bloqueado → END, se aprovado → entry_router."""
    if not state.get("compliance_approved", True):
        logger.info("Compliance bloqueou a mensagem → END")
        return END
    return "entry_router"


def build_graph(llm_factory: LLMFactory | None = None, checkpointer=None) -> StateGraph:
    """Monta e compila o pipeline multi-agente LangGraph.

    Fluxo:
        START → compliance → (entry_router | END)
        entry_router → (triage | credit | credit_interview | exchange)
        Cada agente pode redirecionar para outro via current_agent.
    """
    factory = llm_factory or LLMFactory()

    # Instanciar agentes
    compliance = ComplianceAgent(factory)
    triage = TriageAgent(factory)
    credit = CreditAgent(factory)
    credit_interview = CreditInterviewAgent(factory)
    exchange = ExchangeAgent(factory)

    # Construir grafo
    graph = StateGraph(BankState)

    # Nós
    graph.add_node("trim_history", _trim_messages)
    graph.add_node("compliance", compliance.run)
    graph.add_node("entry_router", lambda state: {})
    graph.add_node("triage", triage.run)
    graph.add_node("credit", credit.run)
    graph.add_node("credit_interview", credit_interview.run)
    graph.add_node("exchange", exchange.run)

    # Entry point → trim_history → compliance (primeiro nó do grafo)
    graph.set_entry_point("trim_history")
    graph.add_edge("trim_history", "compliance")

    # Compliance decide: aprovado → entry_router, bloqueado → END
    graph.add_conditional_edges(
        "compliance",
        _compliance_router,
        {
            "entry_router": "entry_router",
            END: END,
        },
    )

    # Router de entrada decide qual agente recebe a mensagem
    _routing_map = {
        "triage": "triage",
        "credit": "credit",
        "credit_interview": "credit_interview",
        "exchange": "exchange",
        END: END,
    }

    graph.add_conditional_edges("entry_router", _entry_router, _routing_map)

    # Routing condicional após cada agente (cada nó tem seu próprio router
    # para detectar quando o agente quer "ficar" e parar em vez de loopar)
    graph.add_conditional_edges("triage", _make_router("triage"), _routing_map)
    graph.add_conditional_edges("credit", _make_router("credit"), _routing_map)
    graph.add_conditional_edges("credit_interview", _make_router("credit_interview"), _routing_map)
    graph.add_conditional_edges("exchange", _make_router("exchange"), _routing_map)

    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Pipeline LangGraph compilado com sucesso (compliance + 4 agentes + entry router).")
    return compiled
