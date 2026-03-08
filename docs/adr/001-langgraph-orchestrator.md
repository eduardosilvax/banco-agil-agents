# ADR-001: LangGraph como Orquestrador Multi-Agente

| Campo      | Valor   |
| ---------- | ------- |
| **Status** | Aceito  |
| **Data**   | 2026-03 |

## Contexto

O desafio exige um sistema **multi-agente** com 4 agentes especializados (Triagem, Crédito, Entrevista de Crédito, Câmbio), cada um com escopo definido e transições transparentes entre si.

**Alternativas consideradas:**

| Framework      | Prós                                                      | Contras                                             |
| -------------- | --------------------------------------------------------- | --------------------------------------------------- |
| **LangGraph**  | StateGraph tipado, conditional edges, roteamento dinâmico | API mais verbosa                                    |
| Google ADK     | Framework oficial Google, boa integração Gemini           | Mais novo, menos controle sobre fluxo               |
| CrewAI         | Sintaxe declarativa, role-based                           | Menos controle sobre o grafo, overhead de abstração |
| LangChain puro | Sem dependência extra                                     | Reinventar state management e roteamento            |

## Decisão

Escolhi **LangGraph** (`StateGraph`) como orquestrador.

## Justificativa

1. **Grafo explícito**: `add_node()` + `add_conditional_edges()` tornam o pipeline visível e testável. Cada agente é um nó isolado com responsabilidade única.
2. **Tipagem de estado**: `TypedDict` (`BankState`) garante que cada nó receba e devolva exatamente os campos esperados.
3. **Conditional edges**: Roteamento dinâmico entre agentes (triage → credit/exchange, credit ↔ interview) é nativo — sem if/else espalhado.
4. **add_messages**: O LangGraph gerencia automaticamente o acúmulo de mensagens no histórico, simplificando o gerenciamento de conversação.
5. **Handoffs bidirecionais**: O campo `current_agent` no state permite que qualquer agente redirecione para outro, suportando fluxos como crédito → entrevista → crédito.

## Evolução: Nó `trim_history` no Grafo

Com conversas longas, o histórico de mensagens crescia sem limite, degradando qualidade e custo. Adicionei um nó `trim_history` como **ponto de entrada** do grafo (`START → trim_history → compliance → ...`). Esse nó aplica uma janela deslizante de 20 mensagens, preservando a primeira mensagem (system context) + as últimas 19.

A decisão de implementar como nó do grafo (e não como utility dentro de cada agente) garante que o trimming é auditável no trace do LangSmith e consistente — nenhum agente precisa se preocupar com tamanho de contexto.

## Consequências

- **Positivas**: Pipeline testável nó a nó, fácil adicionar novos agentes, state visível em logs e na sidebar do Streamlit. O nó `trim_history` protege contra explosão de tokens em conversas longas.
- **Negativas**: Dependência do LangGraph (lock-in leve).
- **Riscos mitigados**: Cada agente é uma classe Python pura — migrar para outro orquestrador exigiria apenas reescrever `graph.py`.
