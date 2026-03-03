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

## Justificativa

1. **Custo zero**: Free tier do Gemini é generoso o suficiente para desenvolvimento e demos. Demonstra pragmatismo — resolver o problema sem gastar.
2. **Qualidade suficiente**: Para o escopo do case (classificação de intenções, extração de CPF/datas, conversação bancária), o Flash resolve bem.
3. **Abstração de provider**: O `LLMFactory` isola completamente o provider. Trocar de Gemini para OpenAI é uma mudança de variável de ambiente, zero código.
4. **Facilidade de setup**: Uma API key, sem configuração de endpoint/deployment.

## Consequências

- **Positivas**: Zero custo, setup simples, demonstra abstração de provider.
- **Negativas**: Gemini pode ter rate limits em uso intensivo no free tier.
- **Riscos mitigados**: `LLMFactory` suporta OpenAI como fallback — basta trocar `LLM_PROVIDER=openai`.
