# ADR-003: Estado Conversacional via TypedDict

| Campo      | Valor   |
| ---------- | ------- |
| **Status** | Aceito  |
| **Data**   | 2026-03 |

## Contexto

Com 4 agentes que precisam compartilhar contexto (dados de autenticação, progresso da entrevista, solicitações de crédito), é necessário um mecanismo de estado que:

1. Seja tipado e previsível
2. Suporte acúmulo de mensagens
3. Permita handoffs entre agentes preservando contexto
4. Funcione nativamente com LangGraph

**Alternativas consideradas:**

| Abordagem          | Prós                           | Contras                                |
| ------------------ | ------------------------------ | -------------------------------------- |
| **TypedDict**      | Nativo LangGraph, leve, tipado | Sem validação em runtime               |
| Pydantic BaseModel | Validação forte                | Overhead de serialização com LangGraph |
| Dataclass          | Familiar                       | Não suporta `add_messages` nativamente |
| Dict puro          | Zero overhead                  | Sem tipagem, propenso a bugs           |

## Decisão

Escolhi **`TypedDict`** (`BankState`) com **`Annotated[list, add_messages]`** para o histórico.

## Justificativa

1. **Compatibilidade LangGraph**: `TypedDict` é o tipo nativo do `StateGraph`. Zero overhead de conversão.
2. **`add_messages`**: O LangGraph gerencia automaticamente o acúmulo de mensagens — cada nó retorna apenas as novas mensagens e o framework faz o merge.
3. **Campos tipados**: `authenticated: bool`, `client_data: dict`, `interview_data: dict` etc. dão clareza sobre o que cada agente pode ler/escrever.
4. **Handoffs**: O campo `current_agent: str` controla o roteamento. As conditional edges verificam este campo para decidir o próximo nó.

## Consequências

- **Positivas**: State previsível, handoffs limpos, fácil de debugar (sidebar do Streamlit mostra o state).
- **Negativas**: Sem validação em runtime (tipo do campo não é verificado). Mitigo com type hints e testes.
- **Trade-off aceito**: A simplicidade do TypedDict compensa a falta de validação para o escopo deste case.
