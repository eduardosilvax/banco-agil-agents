# Orquestrador LangGraph — conecta os 4 agentes num grafo de atendimento.
#
# Fluxo:
# START → triage → (credit | credit_interview | exchange)
# credit ↔ credit_interview (handoffs bidirecionais)
# Qualquer agente pode encerrar via should_end → END
#
# O roteamento é controlado pelo campo `current_agent` no state.
# Transições são implícitas — o cliente percebe um único atendente.

from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from src.agents.credit import CreditAgent
from src.agents.credit_interview import CreditInterviewAgent
from src.agents.exchange import ExchangeAgent
from src.agents.triage import TriageAgent
from src.core.llm_factory import LLMFactory
from src.schemas.state import BankState

logger = logging.getLogger("banco_agil.graph")


def _route_after_agent(state: BankState) -> str:
    """Edge condicional: decide para qual nó ir com base no state.

    Lógica:
    1. Se should_end=True → END
    2. Se current_agent mudou → vai pro novo agente
    3. Se permanece no mesmo → END (espera próxima mensagem)
    """
    if state.get("should_end", False):
        logger.info("Conversa encerrada (should_end=True)")
        return END

    agent = state.get("current_agent", "triage")
    logger.info("Roteando para: %s", agent)

    valid_agents = {"triage", "credit", "credit_interview", "exchange"}
    if agent in valid_agents:
        return agent

    return END


def build_graph(llm_factory: LLMFactory | None = None) -> StateGraph:
    """Monta e compila o pipeline multi-agente LangGraph.

    Fluxo:
        START → triage → routing → (credit | credit_interview | exchange | END)
        Cada agente pode redirecionar para outro via current_agent.
    """
    factory = llm_factory or LLMFactory()

    # Instanciar agentes
    triage = TriageAgent(factory)
    credit = CreditAgent(factory)
    credit_interview = CreditInterviewAgent(factory)
    exchange = ExchangeAgent(factory)

    # Construir grafo
    graph = StateGraph(BankState)

    # Adicionar nós
    graph.add_node("triage", triage.run)
    graph.add_node("credit", credit.run)
    graph.add_node("credit_interview", credit_interview.run)
    graph.add_node("exchange", exchange.run)

    # Entry point: sempre começa na triagem
    graph.set_entry_point("triage")

    # Routing condicional após cada agente
    _routing_map = {
        "triage": "triage",
        "credit": "credit",
        "credit_interview": "credit_interview",
        "exchange": "exchange",
        END: END,
    }

    graph.add_conditional_edges("triage", _route_after_agent, _routing_map)
    graph.add_conditional_edges("credit", _route_after_agent, _routing_map)
    graph.add_conditional_edges("credit_interview", _route_after_agent, _routing_map)
    graph.add_conditional_edges("exchange", _route_after_agent, _routing_map)

    compiled = graph.compile()
    logger.info("Pipeline LangGraph compilado com sucesso (4 agentes).")
    return compiled
