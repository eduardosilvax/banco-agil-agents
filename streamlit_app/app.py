# Frontend Streamlit — interface alternativa para demonstração e prototipação rápida.
#
# Consome a mesma API REST (/api/v1/chat) que o frontend SvelteKit.
# Foco em simplicidade e rapidez de setup vs o Svelte (produção).

from __future__ import annotations

import os

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

AGENT_LABELS: dict[str, str] = {
    "triage": "Triagem",
    "credit": "Crédito",
    "credit_interview": "Entrevista de Crédito",
    "exchange": "Câmbio",
}

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Banco Ágil — Atendimento Inteligente",
    page_icon="static/favicon.svg",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS — visual alinhado ao SvelteKit (dark/clean banking)
# ---------------------------------------------------------------------------

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* Hide Streamlit default header and footer */
    #MainMenu, header[data-testid="stHeader"], footer { visibility: hidden; height: 0; }

    /* Base light theme — aligned with Svelte design system */
    .stApp {
        background-color: #fafafa;
        color: #09090b;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    }

    /* Custom header bar */
    .header-bar {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        padding: 0.75rem 0;
        border-bottom: 1px solid #e4e4e7;
        margin-bottom: 1rem;
    }
    .header-logo {
        width: 32px; height: 32px;
        background: #09090b;
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 0.72rem; color: #f97316;
        letter-spacing: 0.04em;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .header-brand {
        display: flex; flex-direction: column; line-height: 1.2;
    }
    .header-name {
        font-size: 0.88rem; font-weight: 650; color: #09090b;
    }
    .header-tag {
        font-size: 0.68rem; color: #a1a1aa; font-weight: 500; letter-spacing: 0.02em;
    }

    /* Status pill */
    .status-pill {
        display: flex; align-items: center; gap: 0.35rem;
        padding: 0.25rem 0.65rem; border-radius: 9999px;
        font-size: 0.7rem; font-weight: 500;
        margin-left: auto;
    }
    .status-dot {
        width: 6px; height: 6px; border-radius: 50%;
        display: inline-block;
    }
    .status-online .status-dot {
        background: #22c55e;
        box-shadow: 0 0 6px rgba(34,197,94,0.4);
    }
    .status-online {
        color: #22c55e;
        border: 1px solid rgba(34,197,94,0.2);
        background: rgba(34,197,94,0.06);
    }
    .status-offline .status-dot { background: #ef4444; }
    .status-offline {
        color: #ef4444;
        border: 1px solid rgba(239,68,68,0.2);
        background: rgba(239,68,68,0.06);
    }

    /* Force all text to dark on light background */
    .stApp, .stApp p, .stApp span, .stApp div, .stApp li, .stApp label,
    .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown div {
        color: #09090b !important;
    }

    /* Logo text — orange on dark backgrounds (higher specificity) */
    .stApp .header-logo,
    div.header-logo {
        color: #f97316 !important;
    }
    .stApp [data-logo-mark],
    div[data-logo-mark] {
        color: #f97316 !important;
    }

    /* Chat messages — base */
    .stChatMessage {
        border-radius: 12px !important;
        background: #ffffff !important;
        border: 1px solid #e4e4e7 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }
    .stChatMessage p, .stChatMessage span, .stChatMessage div {
        color: #09090b !important;
    }

    /* User message — dark bubble, light text */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: #09090b !important;
        border-color: #09090b !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p,
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) span,
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) div:not([data-testid]) {
        color: #fafafa !important;
    }

    /* Assistant avatar — orange background */
    [data-testid="chatAvatarIcon-assistant"] {
        background: #f97316 !important;
        border-radius: 8px !important;
    }
    [data-testid="chatAvatarIcon-assistant"] svg {
        color: #ffffff !important;
    }

    /* User avatar — dark bg, orange icon */
    [data-testid="chatAvatarIcon-user"] {
        background: #09090b !important;
        border-radius: 8px !important;
    }
    [data-testid="chatAvatarIcon-user"] svg {
        color: #f97316 !important;
    }

    /* Chat input text */
    .stChatInput, .stChatInput input, .stChatInput textarea,
    [data-testid="stChatInput"] input, [data-testid="stChatInput"] textarea {
        color: #09090b !important;
    }

    /* Expander / details text */
    .streamlit-expanderHeader, .streamlit-expanderContent,
    details summary, details p, details span {
        color: #09090b !important;
    }

    /* Sidebar text */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #09090b !important;
    }

    /* Suggestion buttons */
    .stButton > button {
        background: #ffffff !important;
        border: 1px solid #e4e4e7 !important;
        border-radius: 12px !important;
        color: #3f3f46 !important;
        font-weight: 530 !important;
        font-size: 0.82rem !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
        transition: all 180ms cubic-bezier(0.16,1,0.3,1) !important;
    }
    .stButton > button:hover {
        border-color: #f97316 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06), 0 0 0 3px rgba(249,115,22,0.10) !important;
        transform: translateY(-2px);
        color: #09090b !important;
    }

    /* Tech details accordion */
    .tech-box {
        background: rgba(0,0,0,0.05);
        border-radius: 6px;
        padding: 0.5rem 0.65rem;
        font-size: 0.75rem;
        margin-top: 0.35rem;
    }
    .tech-row {
        display: flex;
        justify-content: space-between;
        padding: 2px 0;
    }
    /* Status pill — override global color */
    .status-online, .status-online span { color: #22c55e !important; }
    .status-offline, .status-offline span { color: #ef4444 !important; }

    /* Header tag subtle color */
    .header-tag { color: #a1a1aa !important; }

    /* Tech details override */
    .tech-label { color: #a1a1aa !important; }
    .tech-value { color: #3f3f46 !important; }
    .tech-ok { color: #22c55e !important; }
    .tech-blocked { color: #ef4444 !important; }

    /* Footer */
    .powered, .powered * { color: #a1a1aa !important; }

    /* Footer powered by */
    .powered {
        text-align: center;
        font-size: 0.68rem;
        color: #a1a1aa;
        padding: 0.75rem 0;
        border-top: 1px solid #e4e4e7;
        margin-top: 1rem;
        letter-spacing: 0.02em;
    }

    /* Sidebar styles */
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e4e4e7;
    }

    /* Empty state subtitle color */
    .empty-sub { color: #71717a !important; }

    /* Spinner text */
    .stSpinner > div { color: #71717a !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "pending_reply" not in st.session_state:
    st.session_state.pending_reply = False

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["X-API-Key"] = API_KEY
    return h


def check_health() -> bool:
    try:
        r = requests.get(f"{API_BASE}/api/v1/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def send_message(message: str, thread_id: str | None) -> dict:
    payload = {"message": message, "thread_id": thread_id}
    r = requests.post(
        f"{API_BASE}/api/v1/chat",
        json=payload,
        headers=_headers(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

api_online = check_health()
status_class = "status-online" if api_online else "status-offline"
status_text = "Online" if api_online else "Offline"

st.markdown(
    f"""
<div class="header-bar">
    <div class="header-logo" data-logo-mark>BA</div>
    <div class="header-brand">
        <span class="header-name">Atendimento Inteligente</span>
        <span class="header-tag">Banco Ágil</span>
    </div>
    <div class="status-pill {status_class}">
        <span class="status-dot"></span>
        <span>{status_text}</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tech_details_html(comp: bool, reason: str | None, route: str) -> str:
    """Build HTML for the tech details expander."""
    label = AGENT_LABELS.get(route, route)
    if comp:
        status = '<span class="tech-value tech-ok">✓ Aprovado</span>'
    else:
        status = f'<span class="tech-value tech-blocked">✗ Bloqueado ({reason})</span>'
    return (
        '<div class="tech-box">'
        '<div class="tech-row">'
        '<span class="tech-label">Compliance</span>'
        f"{status}</div>"
        '<div class="tech-row">'
        '<span class="tech-label">Agente</span>'
        f'<span class="tech-value">{label}</span></div>'
        "</div>"
    )


# ---------------------------------------------------------------------------
# Sidebar — nova conversa + info
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Banco Ágil")
    if st.button("Nova conversa", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = None
        st.rerun()
    st.divider()
    st.markdown(
        "**Clientes de teste:**\n"
        "| CPF | Nascimento |\n"
        "|---|---|\n"
        "| `12345678901` | `15/05/1990` |\n"
        "| `98765432100` | `20/10/1985` |\n"
        "| `55566677788` | `01/12/1988` |\n"
    )
    st.divider()
    st.caption("Multi-Agent RAG · LangGraph · FastAPI")

# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

if not st.session_state.messages:
    st.markdown(
        """
<div style="text-align:center; padding: 3rem 1rem 2rem; position:relative; overflow:hidden;">
    <div style="position:absolute; width:500px; height:500px;
                border-radius:50%;
                background:radial-gradient(circle,
                rgba(249,115,22,0.10) 0%,
                rgba(249,115,22,0.03) 40%,
                transparent 70%);
                top:-50px; left:50%;
                transform:translateX(-50%);
                pointer-events:none;"></div>
    <div data-logo-mark style="width:56px; height:56px;
                margin:0 auto 1.5rem; background:#09090b;
                border-radius:12px; display:flex; align-items:center; justify-content:center;
                font-weight:800; font-size:1.2rem; color:#f97316 !important; letter-spacing:0.04em;
                box-shadow: 0 4px 12px rgba(0,0,0,0.06), 0 0 48px rgba(249,115,22,0.12);
                position:relative;">BA</div>
    <h2 style="color:#09090b; margin:0 0 0.6rem; font-weight:720; letter-spacing:-0.025em;">
        <span style="background:linear-gradient(135deg, #f97316 0%, #ea580c 100%);
                     -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                     background-clip:text;">Olá!</span> Como posso ajudar?
    </h2>
    <p class="empty-sub" style="font-size:0.92rem;
        max-width:400px; margin:0 auto; line-height:1.55;">
        Sou seu assistente do Banco Ágil. Pergunte-me sobre limites,
        empréstimos ou cotações de câmbio. Estou aqui para agilizar seu dia.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    suggestions = [
        ("Aumento de Limite", "Gostaria de ver meu limite atual."),
        ("Empréstimos", "Quais as condições para um empréstimo pessoal?"),
        ("Câmbio", "Qual a cotação do dólar hoje?"),
    ]
    for col, (label, query) in zip(cols, suggestions):
        if col.button(label, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": query})
            st.session_state.pending_reply = True
            st.rerun()

# ---------------------------------------------------------------------------
# Render chat history
# ---------------------------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Tech details
        meta = msg.get("meta")
        if meta and msg["role"] == "assistant":
            with st.expander("Detalhes técnicos", expanded=False):
                comp = meta.get("compliance_approved", True)
                reason = meta.get("compliance_reason")
                route = meta.get("route", "triage")
                st.markdown(
                    _tech_details_html(comp, reason, route),
                    unsafe_allow_html=True,
                )

# ---------------------------------------------------------------------------
# Process pending reply (from suggestion buttons)
# ---------------------------------------------------------------------------

if st.session_state.pending_reply and st.session_state.messages:
    st.session_state.pending_reply = False
    last_user_msg = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                data = send_message(last_user_msg, st.session_state.thread_id)
                st.session_state.thread_id = data.get("thread_id")

                answers = data.get("answers") or [data.get("answer", "Sem resposta.")]
                meta = data.get("meta")

                for answer in answers:
                    st.markdown(answer)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "meta": meta}
                    )

                if meta:
                    with st.expander("Detalhes técnicos", expanded=False):
                        comp = meta.get("compliance_approved", True)
                        reason = meta.get("compliance_reason")
                        route = meta.get("route", "triage")
                        st.markdown(
                            _tech_details_html(comp, reason, route),
                            unsafe_allow_html=True,
                        )

            except requests.HTTPError as e:
                err = f"Erro na API: {e.response.status_code}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
            except requests.ConnectionError:
                err = "Não foi possível conectar ao backend. Verifique se o servidor está rodando."
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Digite sua pergunta aqui…"):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                data = send_message(prompt, st.session_state.thread_id)
                st.session_state.thread_id = data.get("thread_id")

                answers = data.get("answers") or [data.get("answer", "Sem resposta.")]
                meta = data.get("meta")

                for answer in answers:
                    st.markdown(answer)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "meta": meta}
                    )

                # Tech details for last message
                if meta:
                    with st.expander("Detalhes técnicos", expanded=False):
                        comp = meta.get("compliance_approved", True)
                        reason = meta.get("compliance_reason")
                        route = meta.get("route", "triage")
                        st.markdown(
                            _tech_details_html(comp, reason, route),
                            unsafe_allow_html=True,
                        )

            except requests.HTTPError as e:
                err = f"Erro na API: {e.response.status_code}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
            except requests.ConnectionError:
                err = "Não foi possível conectar ao backend. Verifique se o servidor está rodando."
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="powered">Multi-Agent RAG · LangGraph · FastAPI · Streamlit</div>',
    unsafe_allow_html=True,
)
