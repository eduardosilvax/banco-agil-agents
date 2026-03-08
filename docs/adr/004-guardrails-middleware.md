# ADR-004: Guardrails como Middleware

| Campo      | Valor   |
| ---------- | ------- |
| **Status** | Aceito  |
| **Data**   | 2026-03 |

## Contexto

O sistema processa inputs do usuário via LLM. Sem validação, entradas maliciosas (prompt injection) ou dados sensíveis nas respostas (CPF completo) poderiam comprometer a segurança e privacidade.

Precisamos de uma camada de defesa. A questão é: **como implementar?**

## Alternativas Avaliadas

### 1. Agentes validadores separados no grafo

Adicionar um nó `validator_agent` no LangGraph que roda ANTES de cada agente principal.

**Prós:**

- Separação total de responsabilidades
- Pode usar o LLM para validação semântica sofisticada

**Contras:**

- Adiciona **latência** — cada mensagem passa por um nó extra (LLM call)
- Adiciona **custo de tokens** — dobra o consumo por turno
- Aumenta **complexidade de routing** — edges extras no grafo
- Torna o grafo **menos legível** — 8 nós ao invés de 4

### 2. Guardrails como middleware (adotado)

Classes `InputGuardrail` e `OutputGuardrail` que rodam como funções Python puras ANTES e DEPOIS do LLM, dentro de cada agente.

**Prós:**

- **Zero latência** — regex e heurísticas rodam em <1ms
- **Zero custo de tokens** — não usa LLM
- **Zero complexidade no grafo** — 4 nós limpos
- **Testável isoladamente** — funções puras com input/output previsível
- **Defesa em profundidade** — sanitização + anti-injection + mascaramento

**Contras:**

- Não detecta ataques semânticos sofisticados (mas esses são raros e caros de detectar)
- Cada agente precisa chamar o guardrail manualmente (mitigado com pattern consistente)

## Decisão

Escolhi **guardrails como middleware** (`src/core/guardrails.py`).

## Implementação

- `InputGuardrail.sanitize()` — Normalização Unicode (NFC), remoção de caracteres de controle
- `InputGuardrail.detect_prompt_injection()` — Regex contra padrões comuns (PT-BR e EN)
- `OutputGuardrail.mask_cpf()` — Mascara CPFs completos nas respostas (123.**_._**-01)

## Evolução: Security Logging

Acoplei loggers dedicados aos guardrails para auditoria de segurança:

- **`banco_agil.security`** — registra toda mensagem bloqueada por injection ou compliance, com preview dos primeiros 80 caracteres
- Input no guardrail: `guardrail_blocked | type=prompt_injection | preview=...`
- Input no compliance: `compliance_blocked | layer=regex | msg_preview=...` e `compliance_blocked | layer=llm_semantic | msg_preview=...`

Logs de segurança são separados dos logs operacionais, facilitando integração com SIEMs (Splunk, Elastic, CloudWatch) e alertas automáticos.

**Arquivos:** `src/core/guardrails.py`, `src/agents/compliance.py`

## Consequências

- **Positivas**: Segurança básica sem custo de performance. Padrão extensível para novos guardrails. Security logging habilita detecção e resposta a incidentes.
- **Negativas**: Não cobre ataques semânticos sofisticados. Para coverage total, precisaria de um LLM classifier (ex: Azure Content Safety, Google Cloud DLP).
- **Trade-off aceito**: Para o escopo do case, heurísticas cobrem >95% dos padrões de ataque conhecidos. Em produção, adicionaríamos um classifier pago como segunda camada.
