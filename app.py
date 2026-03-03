# Banco Ágil — Interface Streamlit de Atendimento Bancário
#
# Chat interface que conecta com o pipeline LangGraph multi-agente.
# As transições entre agentes são transparentes para o usuário —
# ele percebe um único atendente inteligente.
#
# Execute com: streamlit run app.py

from __future__ import annotations

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from src.core.graph import build_graph
from src.core.llm_factory import LLMFactory


# ============================================================
# Configuração da página
# ============================================================
st.set_page_config(
    page_title="Banco Ágil — Atendimento Inteligente",
    page_icon="🏦",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS customizado — visual bancário moderno
# ============================================================
st.markdown("""
<style>
    /* Tema geral */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #16213e 100%);
    }

    /* Header */
    .bank-header {
        text-align: center;
        padding: 1.5rem 0 1rem;
        border-bottom: 2px solid rgba(100, 200, 255, 0.15);
        margin-bottom: 1.5rem;
    }
    .bank-header h1 {
        color: #64c8ff;
        font-size: 2rem;
        margin: 0;
        letter-spacing: 0.5px;
    }
    .bank-header p {
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #0f0c29 100%);
    }
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #64c8ff;
    }

    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 4px 2px;
    }
    .badge-auth { background: rgba(46, 204, 113, 0.2); color: #2ecc71; border: 1px solid rgba(46, 204, 113, 0.3); }
    .badge-no-auth { background: rgba(231, 76, 60, 0.2); color: #e74c3c; border: 1px solid rgba(231, 76, 60, 0.3); }
    .badge-agent { background: rgba(100, 200, 255, 0.15); color: #64c8ff; border: 1px solid rgba(100, 200, 255, 0.25); }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: rgba(255, 255, 255, 0.3);
        font-size: 0.75rem;
        padding: 2rem 0 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Header
# ============================================================
st.markdown("""
<div class="bank-header">
    <h1>🏦 Banco Ágil</h1>
    <p>Atendimento inteligente com agentes de IA especializados</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Inicialização do estado da sessão
# ============================================================
def init_session():
    """Inicializa o estado da sessão Streamlit."""
    if "graph" not in st.session_state:
        with st.spinner("🔧 Inicializando sistema de agentes..."):
            factory = LLMFactory()
            st.session_state.graph = build_graph(factory)
            st.session_state.graph_state = {
                "messages": [],
                "authenticated": False,
                "client_data": None,
                "auth_attempts": 0,
                "collected_cpf": None,
                "collected_birth_date": None,
                "current_agent": "triage",
                "credit_request_data": None,
                "interview_data": None,
                "should_end": False,
            }
            st.session_state.chat_history = []
            st.session_state.initialized = True


init_session()


# ============================================================
# Sidebar — informações do sistema
# ============================================================
with st.sidebar:
    st.markdown("### ⚙️ Painel do Sistema")
    st.divider()

    # Status de autenticação
    gs = st.session_state.graph_state
    if gs.get("authenticated"):
        client = gs.get("client_data", {})
        st.markdown(
            f'<span class="status-badge badge-auth">✅ Autenticado</span>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**Cliente:** {client.get('nome', 'N/A')}")
        st.markdown(f"**Score:** {client.get('score', 'N/A')}")
        st.markdown(f"**Limite:** R$ {client.get('limite_credito', 0):,.2f}")
    else:
        st.markdown(
            '<span class="status-badge badge-no-auth">🔒 Não autenticado</span>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Agente ativo
    agent_names = {
        "triage": "🚦 Triagem",
        "credit": "💳 Crédito",
        "credit_interview": "📝 Entrevista de Crédito",
        "exchange": "💱 Câmbio",
    }
    current = gs.get("current_agent", "triage")
    st.markdown(
        f'<span class="status-badge badge-agent">{agent_names.get(current, current)}</span>',
        unsafe_allow_html=True,
    )
    st.caption("Agente ativo (invisível para o cliente)")

    st.divider()

    # Agentes disponíveis
    st.markdown("### 🤖 Agentes")
    st.markdown("""
    - 🚦 **Triagem** — Autenticação e roteamento
    - 💳 **Crédito** — Limites e aumento
    - 📝 **Entrevista** — Recálculo de score
    - 💱 **Câmbio** — Cotação de moedas
    """)

    st.divider()

    # Botão de nova conversa
    if st.button("🔄 Nova Conversa", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ============================================================
# Área de chat
# ============================================================

# Exibir mensagem inicial se não há histórico
if not st.session_state.chat_history:
    # Gerar saudação via agente de triagem
    with st.spinner(""):
        try:
            result = st.session_state.graph.invoke(st.session_state.graph_state)
            st.session_state.graph_state.update(result)

            # Extrair mensagem do AI
            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, AIMessage):
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": msg.content,
                    })
                    break
        except Exception as e:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": (
                    "Olá! 👋 Bem-vindo(a) ao **Banco Ágil**! "
                    "Sou seu assistente virtual. Para começar, "
                    "informe seu **CPF**."
                ),
            })

# Renderizar histórico de chat
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"], avatar="🏦" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# Input do usuário
if prompt := st.chat_input(
    "Digite sua mensagem...",
    disabled=st.session_state.graph_state.get("should_end", False),
):
    # Exibir mensagem do usuário
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # Processar pelo grafo
    with st.spinner("Processando..."):
        try:
            # Adicionar mensagem ao state
            current_state = st.session_state.graph_state.copy()
            current_state["messages"] = current_state.get("messages", []) + [
                HumanMessage(content=prompt)
            ]

            # Invocar grafo
            result = st.session_state.graph.invoke(current_state)

            # Atualizar state
            st.session_state.graph_state.update(result)

            # Extrair resposta do AI
            ai_response = None
            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, AIMessage):
                    ai_response = msg.content
                    break

            if ai_response:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": ai_response,
                })

        except Exception as e:
            error_msg = (
                "Desculpe, ocorreu um erro no processamento. "
                "Por favor, tente novamente. 😕"
            )
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": error_msg,
            })
            st.error(f"Erro interno: {e}")

    st.rerun()

# Mensagem de conversa encerrada
if st.session_state.graph_state.get("should_end", False):
    st.info("💬 Atendimento encerrado. Clique em **Nova Conversa** na barra lateral para iniciar outro.")

# Footer
st.markdown("""
<div class="footer">
    Banco Ágil — Sistema de Atendimento com IA • Case Técnico
</div>
""", unsafe_allow_html=True)
