# ADR-002: Google Gemini Free Tier como LLM Principal

| Campo      | Valor   |
| ---------- | ------- |
| **Status** | Aceito  |
| **Data**   | 2026-03 |

## Contexto

O sistema precisa de um LLM para: conversação natural, classificação de intenções, extração de entidades e geração de respostas. O desafio sugere APIs com free tier (Gemini, Groq, OpenAI).

**Alternativas consideradas:**

| Provider             | Prós                                      | Contras                  |
| -------------------- | ----------------------------------------- | ------------------------ |
| **Gemini 2.5 Flash** | Free tier generoso, qualidade boa, rápido | Menos maduro que GPT-4   |
| OpenAI GPT-4.1-nano  | Via LangChain, boa qualidade              | Custo por token          |
| Groq (Mixtral/LLaMA) | Muito rápido                              | Rate limits no free tier |
| OpenRouter           | Multi-provider                            | Complexidade extra       |

## Decisão

Escolhi **Google Gemini 2.5 Flash** (free tier) como LLM principal, com suporte opcional ao OpenAI via `LLM_PROVIDER`.

## Justificativa e Trade-offs

1. **Trade-off de Preço vs Performance**: O free tier do Gemini é generoso o suficiente para desenvolvimento e demos. O uso da infraestrutura do Google é $0, porém o trade-off é que contas gratuitas podem sofrer de rate limits (limites por minuto) ou picos de latência sob carga, comparado aos rate limits muito mais amplos do modelo pago. Para um ambiente de case, esse custo-benefício é ideal.
2. **Capacidade vs Tamanho do Modelo**: Para o escopo do case (classificação de intenções, extração de CPF/datas, conversação bancária, tool calling estruturado), o Flash resolve extremamente bem. O trade-off é que, em tarefas altamente analíticas de raciocínio profundo, ele pode não ter a mesma precisão do Claude 3.5 Sonnet ou GPT-4o, mas a sua velocidade absurdamente superior e janela de contexto massiva (1M) compensam.
3. **Trade-off vs Alternativas Rápidas (Groq)**: Embora os provedores de APIs Groq com Llama3 cheguem a velocidades altíssimas de inferência, o Flash foi preferido porque suporta nativamente recursos mais complexos e estritos de Tool Calling / Structured Output da forma como o LangChain integra, minimizando o código adicional.
4. **Abstração de provider**: O `LLMFactory` isola completamente o provider. Trocar de Gemini para OpenAI é uma mudança de simples variável de ambiente, o que mitiga o risco de vendor lock-in.

## Evolução: Circuit Breaker no LLMFactory

Além do retry exponencial + fallback, adicionei um **circuit breaker** por provider. Após 5 falhas consecutivas, o provider é marcado como "aberto" e skippado por 60 segundos, evitando desperdício de tempo e tokens com um provider instável.

Após o cooldown, o circuit breaker entra em estado **half-open** — permite uma tentativa de recovery. Se sucesso, reseta; se falha, reabre.

| Parâmetro | Valor |
|---|---|
| Falhas para abrir | 5 consecutivas |
| Cooldown | 60 segundos |
| Recovery | Half-open (1 tentativa) |

**Arquivo:** `src/core/llm_factory.py`

## Consequências

- **Positivas**: Zero custo, setup simples, demonstra abstração de provider. Circuit breaker evita cascading failures.
- **Negativas**: Gemini pode ter rate limits em uso intensivo no free tier.
- **Riscos mitigados**: `LLMFactory` suporta OpenAI como fallback com circuit breaker — provider instável é isolado automaticamente.
