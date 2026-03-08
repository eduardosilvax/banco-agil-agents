# ADR-006: Context Engineering — Filtragem de Mensagens entre Agentes

| Campo      | Valor   |
| ---------- | ------- |
| **Status** | Aceito  |
| **Data**   | 2026-03 |

## Contexto

O LangGraph acumula todas as mensagens via `add_messages`. Sem filtragem, cada agente recebe o histórico completo — incluindo mensagens irrelevantes de outros agentes. Isso:

1. **Degrada qualidade**: Contexto irrelevante confunde o LLM (ex: exchange recebe histórico de entrevista de crédito)
2. **Aumenta custo**: Mais tokens por invocação sem benefício
3. **Risco de vazamento**: Informações de um fluxo podem influenciar outro

A documentação oficial de Handoffs do LangGraph recomenda explicitamente **filtrar mensagens entre handoffs**.

## Decisão

Implementar trimming como **nó do grafo LangGraph** (`trim_history`), executado automaticamente antes do compliance em cada invocação. Isso garante que o contexto é limpo de forma consistente e auditável.

```python
# graph.py — nó de trimming como entry point
graph.add_node("trim_history", _trim_messages)
graph.set_entry_point("trim_history")
graph.add_edge("trim_history", "compliance")
```

## Parâmetros

- `_MAX_MESSAGES=20`: Janela deslizante de 20 mensagens recentes
- Preserva a primeira mensagem (system context) + últimas 19

## Alternativas Avaliadas

| Opção                          | Prós                              | Contras                                  |
|--------------------------------|-----------------------------------|------------------------------------------|
| **trim_messages (janela)**     | Simples, determinístico, <0.1ms   | Perde contexto antigo em conversas longas |
| **Sumarização via LLM**       | Mantém contexto semântico         | Latência + custo de tokens por turno      |
| **RemoveMessage por agente**  | Filtragem cirúrgica               | Complexo, frágil, acoplado ao fluxo       |

## Evolução: De Função para Nó do Grafo

Inicialmente a filtragem era uma função utilitária chamada dentro de cada agente. Evoluí para um **nó dedicado no grafo** (`trim_history`) que executa antes de qualquer processamento. Vantagens:

1. **Consistência**: Nenhum agente precisa chamar a função manualmente — o grafo garante
2. **Auditabilidade**: O nó aparece no trace do LangSmith, com input/output visíveis
3. **Testabilidade**: `_trim_messages` é testada isoladamente e como parte do pipeline

**Arquivo:** `src/core/graph.py`

## Consequências

- **Positivo**: Cada agente recebe contexto limpo e focado. Menor consumo de tokens. Trimming é automático e auditável.
- **Trade-off**: Conversas com >20 turnos perdem histórico inicial. Aceitável para o escopo bancário (conversas tipicamente têm 5-15 turnos).
