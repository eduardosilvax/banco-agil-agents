# ADR-008: Command API para Roteamento (LangGraph >=0.4)

| Campo      | Valor     |
| ---------- | --------- |
| **Status** | Proposto  |
| **Data**   | 2026-03   |

## Contexto

O grafo atualmente usa `conditional_edges` + `_make_router` para rotear entre agentes. Esse padrão funciona bem, mas o routing é desacoplado dos agentes — vive em funções externas no `graph.py`.

O LangGraph >=0.4 introduziu a **Command API**, que combina atualização de state + roteamento numa única operação.

## Proposta

Migrar de `conditional_edges` para **Command API** via wrapper `_with_command`.

### Atual (conditional_edges):
```python
# conditional_edges + routing map por agente
graph.add_conditional_edges("triage", _make_router("triage"), _routing_map)
```

### Proposta (Command API):
```python
# Wrapper converte dict → Command com goto explícito
graph.add_node("triage", _with_command("triage", triage.run))
# Sem conditional_edges necessárias
```

## Abordagem

Os agentes continuariam retornando dicts simples (separação de responsabilidades). Um wrapper `_with_command` no `graph.py` converteria o dict em `Command(update={...}, goto=target)` com a mesma lógica de routing:

- `should_end=True` → `goto=END`
- `current_agent` mudou → `goto=novo_agente` (handoff)
- `current_agent` não mudou → `goto=END` (espera input)

## Consequências Esperadas

- **Positivo**: Simplificação do `graph.py` — sem routing map, sem conditional_edges repetitivas.
- **Positivo**: Demonstra conhecimento da API moderna do LangGraph.
- **Trade-off**: Requer LangGraph >=0.4. Os agentes não retornariam Commands diretamente (wrapper faz a conversão).

## Nota

Esta migração ainda não foi implementada. O sistema atual funciona corretamente com `conditional_edges` + `_make_router`.
