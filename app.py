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


# ============================================
# T1 — Bootstrap DB (executa UMA VEZ por ciclo de vida do servidor)
# ============================================

@st.cache_resource
def bootstrap_db():
    """Inicializa o banco e cria o admin padrão — chamado apenas uma vez."""
    from db import init_database
    from services import seed_initial_data
    init_database()
    seed_initial_data()


# ============================================
# T2 — Login com sessão persistente via cookie
# ============================================

def check_login(controller) -> bool:
    """
    Verifica autenticação.
    1. Já autenticado no session_state → True.
    2. Cookie válido → restaura sessão → True.
    3. Sem autenticação → exibe formulário → False.
    """
    from auth import _restore_from_token, set_auth_cookie, COOKIE_NAME

    # Sessão ativa
    if st.session_state.get("authenticated"):
        return True

    # Tenta restaurar do cookie
    token = controller.get(COOKIE_NAME)
    if token:
        if _restore_from_token(token):
            st.rerun()
        else:
            from auth import clear_auth_cookie
            clear_auth_cookie(controller)

    # Formulário de login
    st.markdown(f"# ♻️ {APP_NAME}")
    st.markdown("### 🔐 Login")
    st.markdown("---")

    username = st.text_input("Usuário", placeholder="seu.usuario", key="login_username")
    password = st.text_input("Senha", type="password", key="login_password")

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
    # T1: init banco (cacheado — roda uma única vez)
    bootstrap_db()

    # T2: cookie controller para sessão persistente
    from auth import get_controller, clear_auth_cookie, COOKIE_NAME
    controller = get_controller()

    if not check_login(controller):
        return

    # ---- Sidebar ----
    with st.sidebar:
        st.markdown("## ♻️ Menu")
        st.markdown("---")

        role_label = "🔑 Admin" if st.session_state.get("role") == "admin" else "👷 Operador"
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
        st.caption("Versão 2.0.0")

    # ---- Página inicial ----
    st.markdown(f"# ♻️ {APP_NAME}")
    st.markdown("---")
    st.markdown(f"### 👋 Olá, {st.session_state.get('user_name', '')}!")

    st.info("""
    **📌 Navegue pelas páginas usando o menu lateral:**

    - 📊 **Dashboard**: Visão geral do negócio
    - 📥 **Entradas**: Registre compras de material
    - 📤 **Saídas**: Registre vendas de material *(admin)*
    - 📦 **Estoque**: Consulte o estoque atual
    - 📝 **Cadastros**: Gerencie materiais e parceiros
    - 📈 **Relatórios**: Análises e exportações
    - 🧾 **Operador**: Atendimento ao cliente (canhotos)
    - 💳 **Pagamentos**: Confirmação de canhotos
    - 🔄 **Processamento**: Conversão interna de materiais
    """)

    from datetime import datetime
    from services import get_monthly_metrics, get_stock_value_estimate

    today = datetime.now()
    metrics = get_monthly_metrics(today.year, today.month)
    stock_value = get_stock_value_estimate()

    st.markdown("### 📊 Métricas do Mês Atual")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Compras", f"R$ {metrics['total_purchases']:,.2f}",
                  delta=f"{metrics['weight_in']:.0f} kg")
    with col2:
        st.metric("💵 Vendas", f"R$ {metrics['total_sales']:,.2f}",
                  delta=f"{metrics['weight_out']:.0f} kg")

    col3, col4 = st.columns(2)
    with col3:
        st.metric("📈 Lucro Bruto", f"R$ {metrics['gross_profit']:,.2f}",
                  delta_color="normal" if metrics["gross_profit"] >= 0 else "inverse")
    with col4:
        st.metric("📦 Estoque (estimado)", f"R$ {stock_value:,.2f}")

    st.markdown("---")
    st.caption("💡 Use as páginas do menu para gerenciar seu negócio de forma completa!")


main()
