# ADR-009: Production Hardening — Rate Limiting, Validação e Middleware

| Campo      | Valor   |
| ---------- | ------- |
| **Status** | Aceito  |
| **Data**   | 2026-03 |

## Contexto

A API FastAPI servia requisições sem limites de taxa, validação robusta de input, ou proteção contra timeouts. Para produção, esses controles são obrigatórios — protegem contra abuso, garantem qualidade de input e evitam que requisições lentas travem o servidor.

## Decisão

Implementar sete camadas de hardening no `server.py`, todas configuráveis via variáveis de ambiente:

### 1. Rate Limiting (slowapi)

```python
limiter = Limiter(key_func=get_remote_address)
@app.post("/api/v1/chat")
@limiter.limit("30/minute")
```

- **30 requisições/minuto por IP** (padrão, configurável via `RATE_LIMIT`)
- Usa `slowapi` com backend in-memory
- Retorna HTTP 429 com mensagem clara quando excedido

### 2. Input Validation (Pydantic Field)

```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    thread_id: str = Field(default_factory=..., pattern=r"^[a-zA-Z0-9_-]+$")
```

- Mensagem: 1–5000 caracteres (previne payloads vazios ou gigantes)
- thread_id: Apenas alfanumérico, `_` e `-` (previne injection via thread ID)

### 3. CORS Configurável

```python
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8501")
```

- Em desenvolvimento: localhost das duas frontends
- Em produção: configurar para o domínio real via env var

### 4. Request ID Middleware

- Gera UUID para cada request (`X-Request-ID` header)
- Se o cliente enviar um `X-Request-ID`, ecoa o mesmo (rastreabilidade end-to-end)
- Facilita correlação de logs entre frontend → API → LLM

### 5. Timeout Middleware

- Timeout de **30 segundos** por request
- Se excedido, retorna HTTP 504 Gateway Timeout
- Protege contra LLM calls que travam (ex: rate limit do Gemini free tier)

### 6. Config Validation

```python
validate_config()  # chamado no startup do FastAPI
```

- Valida presença de variáveis obrigatórias (`GOOGLE_API_KEY` ou `OPENAI_API_KEY`)
- Valida existência dos arquivos CSV de dados
- Falha fast no startup em vez de falhar na primeira requisição

### 7. Health Check Aprimorado

```
GET /health → { "status": "ok" | "degraded", "data_files": true, "llm_provider": "gemini" }
```

- Verifica existência dos arquivos de dados
- Reporta provider LLM configurado
- Retorna `degraded` se dados faltam (em vez de 500)

## Consequências

- **Positivas**: API pronta para produção com proteções básicas. Todas as configurações via env vars (12-factor app). Request IDs habilitam rastreabilidade end-to-end.
- **Negativas**: Rate limiting in-memory não persiste entre restarts e não funciona com múltiplas instâncias (sem Redis). Aceitável para o escopo do case.
- **Evolução futura**: Em escala, migrar rate limiting para Redis backend. Adicionar API key authentication para clientes externos.
