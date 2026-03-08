# ADR-007: Structured Output com Pydantic

| Campo      | Valor   |
| ---------- | ------- |
| **Status** | Aceito  |
| **Data**   | 2026-03 |

## Contexto

A classificação de intenção no Agente de Triagem usava `_ROUTE_PROMPT` (prompt textual) + parsing manual da resposta como string. Isso é frágil — o LLM pode retornar "Crédito" vs "credito" vs "crédito ", e o parsing precisa cobrir todas as variações.

## Decisão

Usar `with_structured_output(IntentClassification)` com Pydantic model. O LLM retorna diretamente um objeto tipado — sem parsing de strings.

```python
class IntentClassification(BaseModel):
    intent: str = Field(description="'credito', 'cambio', 'sair' ou 'indefinido'")

result = llm.with_structured_output(IntentClassification).invoke(messages)
route = result.intent  # já é string limpa
```

## Fallback

Se `with_structured_output()` falhar (provider sem suporte), o sistema faz fallback para o prompt textual original. Isso garante retrocompatibilidade.

## Consequências

- **Positivo**: Parsing mais robusto, elimina ambiguidade de formato.
- **Positivo**: Gemini e OpenAI suportam structured output nativamente.
- **Trade-off**: Pydantic vira dependência explícita (já era transitiva via LangChain).
