# ADR-005: Observabilidade com LangSmith

| Campo      | Valor   |
| ---------- | ------- |
| **Status** | Aceito  |
| **Data**   | 2026-03 |

## Contexto

Agentes de IA são não-determinísticos — a mesma entrada pode gerar respostas diferentes. Sem visibilidade sobre cada step do grafo (qual agente rodou, quanto tempo levou, quantos tokens consumiu), debugar problemas em produção é como voar às cegas.

O survey "State of Agent Engineering" (LangChain, 1.300+ profissionais) aponta que **89% das organizações com agentes em produção têm observabilidade implementada**.

## Decisão

Integrar **LangSmith** como plataforma de tracing. O LangGraph detecta automaticamente as variáveis de ambiente `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` e envia traces de cada invocação — **zero código adicional** no pipeline.

## Alternativas Avaliadas

| Opção               | Prós                                       | Contras                               |
|----------------------|--------------------------------------------|---------------------------------------|
| **LangSmith (adotado)** | Zero config, free tier, integração nativa  | Vendor lock-in (LangChain ecosystem)  |
| **OpenTelemetry**    | Padrão aberto, multi-vendor               | Mais setup, precisa de backend (Jaeger/Grafana) |
| **Logging manual**   | Sem dependência externa                    | Sem visualização, sem métricas de tokens |

## Evolução: Structured Logging, Audit Trail e Security Logging

Além do LangSmith para tracing, implementei três camadas adicionais de observabilidade:

### 1. Structured JSON Logging (Produção)

Quando `ENVIRONMENT=production`, todos os logs são emitidos em **JSON estruturado** — cada linha é um objeto JSON parseável por ferramentas de log aggregation (ELK, CloudWatch, Datadog).

Em desenvolvimento, o formato textual legível é mantido.

**Arquivo:** `src/config.py` (`_JSONFormatter`)

### 2. Audit Trail para Decisões de Crédito

Logger dedicado `banco_agil.audit.credit` registra cada decisão de aprovação ou rejeição de crédito:

- `limit_increase_approved | cpf=123*** | old_limit=5000.00 | new_limit=7000.00 | score=750`
- `limit_increase_rejected | cpf=987*** | requested=5000.00 | score=400 | max_allowed=3000.00`

CPFs são parcialmente mascarados nos logs (apenas primeiros 3 dígitos). Facilita compliance regulatório em auditorias do Banco Central.

**Arquivo:** `src/agents/credit.py`

### 3. Security Logging

Logger dedicado `banco_agil.security` para eventos de bloqueio em guardrails e compliance (detalhes no ADR-004).

## Consequências

- **Positivo**: Tracing completo de cada step do grafo (agente, duração, tokens, input/output) sem alterar código de agentes.
- **Positivo**: Free tier do LangSmith é suficiente para demo e primeiros testes em produção.
- **Positivo**: Structured logging + audit trail habilitam compliance regulatório e detecção de anomalias.
- **Trade-off**: LangSmith é opt-in via env vars — se não configurado, o sistema funciona normalmente sem overhead. JSON logging ativa automaticamente em produção.
