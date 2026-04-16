"""
Sistema de Controle de Sucata
Aplicação principal — autenticação e página inicial
"""

import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Sistema de Controle de Sucata")

st.set_page_config(
    page_title=APP_NAME,
    page_icon="♻️",
    layout="centered",
    initial_sidebar_state="auto"
)

# CSS global: login e home com fonte maior, botões mais fáceis de tocar
st.markdown("""
<style>
/* Botões maiores em toda a aplicação */
.stButton > button {
    min-height: 2.8rem !important;
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
}
.stButton > button[kind="primary"] {
    min-height: 3.5rem !important;
    font-size: 1.15rem !important;
}
/* Login: campos maiores */
div[data-testid="stTextInput"] input {
    font-size: 1.15rem !important;
    height: 3rem !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================
# Bootstrap DB (executa UMA VEZ por ciclo de vida do servidor)
# ============================================

@st.cache_resource
def bootstrap_db():
    """Inicializa o banco e cria o admin padrão — chamado apenas uma vez."""
    from db import init_database
    from services import seed_initial_data
    init_database()
    seed_initial_data()


# ============================================
# Login com sessão persistente via cookie
# ============================================

def check_login(controller) -> bool:
    from auth import _restore_from_token, set_auth_cookie, COOKIE_NAME

    if st.session_state.get("authenticated"):
        return True

    token = controller.get(COOKIE_NAME)
    if token:
        if _restore_from_token(token):
            st.rerun()
        else:
            from auth import clear_auth_cookie
            clear_auth_cookie(controller)

    # ---- Tela de Login ----
    st.markdown(
        "<div style='text-align:center;padding:20px 0 8px 0;'>"
        "<span style='font-size:4rem;'>♻️</span>"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<h2 style='text-align:center;margin-bottom:4px;'>{APP_NAME}</h2>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align:center;color:#666;font-size:1rem;margin-bottom:24px;'>"
        "Faça login para continuar</p>",
        unsafe_allow_html=True
    )

    username = st.text_input("👤  Usuário", placeholder="seu.usuario", key="login_username")
    password = st.text_input("🔑  Senha", type="password", key="login_password")

    st.markdown("")
    if st.button("Entrar", type="primary", use_container_width=True):
        if not username or not password:
            st.error("❌ Preencha usuário e senha")
            return False

        from services import authenticate_user
        user = authenticate_user(username, password)

        if user:
            st.session_state.authenticated = True
            st.session_state.user_id = user["id"]
            st.session_state.username = user["username"]
            st.session_state.user_name = user["name"]
            st.session_state.role = user["role"]
            set_auth_cookie(controller, user)
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos")

    return False


def main():
    bootstrap_db()

    from auth import get_controller, clear_auth_cookie, COOKIE_NAME
    controller = get_controller()

    if not check_login(controller):
        return

    is_admin = st.session_state.get("role") == "admin"

    # ---- Sidebar ----
    with st.sidebar:
        st.markdown("## ♻️ Menu")
        st.markdown("---")

        role_label = "🔑 Admin" if is_admin else "👷 Operador"
        st.markdown(f"👤 **{st.session_state.get('user_name', '')}**")
        st.caption(f"{role_label}  ·  @{st.session_state.get('username', '')}")

        st.markdown("---")

        if st.button("🚪 Sair", use_container_width=True):
            clear_auth_cookie(controller)
            for key in ["authenticated", "user_id", "username", "user_name", "role",
                        "_cookie_checked"]:
                st.session_state.pop(key, None)
            st.rerun()

        st.markdown("---")
        st.caption("Versão 4.0.0")

    # ---- Página inicial ----
    st.markdown(
        f"<h1 style='text-align:center;'>♻️ {APP_NAME}</h1>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<p style='text-align:center;font-size:1.15rem;color:#555;margin-bottom:24px;'>"
        f"Olá, <b>{st.session_state.get('user_name', '')}</b>! O que vai fazer hoje?</p>",
        unsafe_allow_html=True
    )

    # ---- Acesso rápido ----
    st.markdown("### 🚀 Acesso Rápido")

    # Linha 1 — ações mais usadas
    col1, col2 = st.columns(2)
    with col1:
        st.page_link(
            "pages/2_🧾_Operador.py",
            label="🧾  Atender Cliente",
            use_container_width=True,
        )
    with col2:
        st.page_link(
            "pages/8_💳_Pagamentos.py",
            label="💳  Confirmar Pagamento",
            use_container_width=True,
        )

    # Linha 2
    col3, col4 = st.columns(2)
    with col3:
        st.page_link(
            "pages/3_📥_Entradas.py",
            label="📥  Registrar Entrada",
            use_container_width=True,
        )
    with col4:
        st.page_link(
            "pages/5_📦_Estoque.py",
            label="📦  Ver Estoque",
            use_container_width=True,
        )

    # Linha 3 — admin / análise
    if is_admin:
        col5, col6 = st.columns(2)
        with col5:
            st.page_link(
                "pages/4_📤_Saídas.py",
                label="📤  Registrar Saída",
                use_container_width=True,
            )
        with col6:
            st.page_link(
                "pages/7_📈_Relatórios.py",
                label="📈  Relatórios",
                use_container_width=True,
            )
    else:
        st.page_link(
            "pages/7_📈_Relatórios.py",
            label="📈  Ver Relatórios",
            use_container_width=True,
        )

    st.markdown("---")

    # ---- Métricas do mês ----
    st.markdown("### 📊 Resumo do Mês")

    from datetime import datetime
    from services import get_monthly_metrics, get_stock_value_estimate

    today = datetime.now()
    metrics = get_monthly_metrics(today.year, today.month)
    stock_value = get_stock_value_estimate()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Compras", f"R$ {metrics['total_purchases']:,.2f}",
                  delta=f"{metrics['weight_in']:.0f} kg comprados")
    with col2:
        st.metric("💵 Vendas", f"R$ {metrics['total_sales']:,.2f}",
                  delta=f"{metrics['weight_out']:.0f} kg vendidos")

    col3, col4 = st.columns(2)
    with col3:
        st.metric("📈 Lucro Bruto", f"R$ {metrics['gross_profit']:,.2f}")
    with col4:
        st.metric("📦 Estoque (estimado)", f"R$ {stock_value:,.2f}")

    st.markdown("---")
    st.caption("💡 Use o menu lateral para acessar todas as funções do sistema.")


main()
