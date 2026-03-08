import asyncio
import logging
import os
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import API_KEY, CORS_ORIGINS, validate_config
from src.core.graph import build_graph
from src.core.llm_factory import LLMFactory

logger = logging.getLogger("banco_agil.api")

# Validar configuração na inicialização
validate_config()

# Rate limiter (por IP)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Banco Ágil - API")
app.state.limiter = limiter

# Rotas que não exigem API key
_PUBLIC_PATHS = {"/api/v1/health", "/api/v1/metrics", "/docs", "/openapi.json", "/redoc"}

# CORS restritivo (configurável via env)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "X-Request-ID"],
)

# Timeout para requests (30 segundos)
_REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Limite de requisições excedido. Tente novamente em alguns instantes."},
    )


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Adiciona X-Request-ID a cada request para rastreabilidade."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    """Aborta requests que excedem o timeout configurado."""
    try:
        return await asyncio.wait_for(call_next(request), timeout=_REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error("Request timeout após %ds | path=%s", _REQUEST_TIMEOUT, request.url.path)
        return JSONResponse(status_code=504, content={"detail": "Request timeout."})


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Middleware de autenticação via X-API-Key header.

    Só é ativado quando API_KEY está configurada no .env.
    Rotas públicas (health, docs) são isentas.
    """
    if API_KEY and request.url.path not in _PUBLIC_PATHS:
        key = request.headers.get("X-API-Key", "")
        if key != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "API key inválida ou ausente."},
            )
    return await call_next(request)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    thread_id: Optional[str] = Field(None, max_length=255, pattern=r"^[a-zA-Z0-9\-]+$")


class ResponseMeta(BaseModel):
    compliance_approved: bool = True
    compliance_reason: str | None = None
    route: str = "triage"
    llm_metrics: dict | None = None


class ChatResponse(BaseModel):
    answer: str
    answers: list[str]
    thread_id: str
    current_agent: str
    meta: ResponseMeta | None = None


checkpointer = MemorySaver()
_factory = LLMFactory()
graph = build_graph(_factory, checkpointer=checkpointer)


@app.post("/api/v1/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat_endpoint(request: Request, req: ChatRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "chat_request | request_id=%s | thread_id=%s | msg_len=%d",
        request_id,
        thread_id,
        len(req.message),
    )

    try:
        state_update = {"messages": [HumanMessage(content=req.message)]}
        new_state = graph.invoke(state_update, config=config)

        messages = new_state.get("messages", [])

        # Encontrar todas as mensagens do AI após a última mensagem do usuário (HumanMessage)
        new_ai_messages = []
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                break
            if isinstance(m, AIMessage):
                new_ai_messages.append(m.content)

        # Inverte pois iteramos de trás para frente
        new_ai_messages.reverse()

        fallback = "Desculpe, não consegui gerar uma resposta."
        answers = new_ai_messages if new_ai_messages else [fallback]
        answer = "\n\n".join(answers)

        current_agent = new_state.get("current_agent", "triage")
        meta = ResponseMeta(
            compliance_approved=new_state.get("compliance_approved", True),
            compliance_reason=new_state.get("compliance_reason"),
            route=current_agent,
        )
        return ChatResponse(
            answer=answer,
            answers=answers,
            thread_id=thread_id,
            current_agent=current_agent,
            meta=meta,
        )
    except Exception as e:
        logger.error("chat_error | request_id=%s | error=%s", request_id, e)
        raise HTTPException(status_code=500, detail="Erro interno no processamento.")


@app.get("/api/v1/health")
def health():
    """Health check robusto — verifica dependências críticas."""
    components = {
        "data_files": _check_data_files(),
        "llm_provider": _check_llm_provider(),
    }
    all_healthy = all(c["healthy"] for c in components.values())
    return {
        "status": "ok" if all_healthy else "degraded",
        "components": components,
    }


def _check_data_files() -> dict:
    """Verifica se os arquivos CSV estão acessíveis."""
    from src.config import CLIENTS_CSV, SCORE_LIMIT_CSV

    missing = []
    for f in [CLIENTS_CSV, SCORE_LIMIT_CSV]:
        if not f.exists():
            missing.append(f.name)
    return {"healthy": len(missing) == 0, "missing": missing}


def _check_llm_provider() -> dict:
    """Verifica se as credenciais do LLM provider estão configuradas."""
    provider = _factory.provider
    has_creds = _factory._has_provider_credentials(provider)
    return {"healthy": has_creds, "provider": provider}


@app.get("/api/v1/metrics")
def metrics():
    """Métricas operacionais do LLM (calls, retries, fallbacks, falhas)."""
    return {
        "llm_provider": _factory.provider,
        "llm_metrics": _factory.metrics,
    }
