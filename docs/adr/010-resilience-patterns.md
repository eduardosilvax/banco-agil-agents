# ADR-010: Padrões de Resiliência — Circuit Breaker e Cache com Stale Fallback

| Campo      | Valor   |
| ---------- | ------- |
| **Status** | Aceito  |
| **Data**   | 2026-03 |

## Contexto

O sistema depende de dois serviços externos suscetíveis a falhas:

1. **LLM providers** (Gemini, OpenAI) — podem ficar indisponíveis, retornar rate limit (429), ou ter latência alta
2. **API de câmbio** (AwesomeAPI) — pode ficar fora do ar ou retornar dados atrasados

Sem proteção, uma falha em qualquer provider degrada todo o sistema. Precisávamos de resiliência sem complexidade excessiva.

## Decisão

### 1. Circuit Breaker para LLM Providers

Implementamos um circuit breaker por provider no `LLMFactory`:

```
┌─────────┐  5 falhas  ┌─────────┐  60s cooldown  ┌───────────┐
│ CLOSED  │───────────▶│  OPEN   │───────────────▶│ HALF-OPEN │
│ (normal)│            │ (skip)  │                │ (1 retry) │
└─────────┘◀───────────└─────────┘                └───────────┘
               reset                  sucesso ↗         │
                 ▲                                      │ falha
                 └──────────────────────────────────────┘
```

| Parâmetro | Valor | Motivo |
|---|---|---|
| Failure threshold | 5 | Tolera instabilidades momentâneas |
| Recovery timeout | 60s | Dá tempo para rate limits resetarem |
| Recovery mode | half-open | Uma tentativa antes de confiar novamente |

**Arquivo:** `src/core/llm_factory.py` (`_CircuitBreaker`)

### 2. Cache de Câmbio com Stale Fallback

A API de câmbio é consultada frequentemente mas atualiza a cada ~30s. Implementamos cache em memória:

```python
_rate_cache: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 300  # 5 minutos
```

**Comportamento:**
1. **Cache miss / TTL expirado** → Consulta API, armazena resultado
2. **API falha + cache stale disponível** → Retorna dado stale (melhor que erro)
3. **API falha + sem cache** → Retorna `None` (agente informa indisponibilidade)

O TTL de 5 minutos é aceitável para cotações bancárias em contexto de demonstração. Em produção real, seria reduzido para 30-60s com cache distribuído (Redis).

**Arquivo:** `src/tools/exchange_api.py`

## Consequências

- **Positivas**: Sistema resiliente a falhas transitórias de providers. Cache reduz chamadas à API externa em ~90%. Stale fallback garante UX contínua mesmo com serviço degradado.
- **Negativas**: Circuit breaker e cache são in-memory — não persistem entre restarts. Estado não é compartilhado entre múltiplas instâncias.
- **Trade-off aceito**: Simplicidade sobre distribuição. Para o escopo do case, in-memory é suficiente. Em produção, migrar para Redis.
- **Observabilidade**: Falhas de circuit breaker e cache stale são logados, visíveis no trace do LangSmith.
