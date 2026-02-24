"""
Sistema de Controle de Sucata
Aplicação principal com autenticação por usuário
"""

import streamlit as st
import os
from dotenv import load_dotenv
from db import init_database

# Carrega variáveis de ambiente
load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Sistema de Controle de Sucata")

# Configuração da página
st.set_page_config(
    page_title=APP_NAME,
    page_icon="♻️",
    layout="centered",
    initial_sidebar_state="auto"
)


def check_login() -> bool:
    """
    Exibe o formulário de login e autentica o usuário.
    Retorna True se autenticado, False caso contrário.
    """
    if st.session_state.get("authenticated"):
        return True

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
            st.session_state.user_id = user['id']
            st.session_state.username = user['username']
            st.session_state.user_name = user['name']
            st.session_state.role = user['role']
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos")

    return False


def main():
    """Função principal da aplicação"""

    # Inicializa o banco e seed
    init_database()
    from services import seed_initial_data
    seed_initial_data()

    # Verifica autenticação
    if not check_login():
        return

    # Menu lateral
    with st.sidebar:
        st.markdown("## ♻️ Menu")
        st.markdown("---")

        # Info do usuário logado
        role_label = "🔑 Admin" if st.session_state.get('role') == 'admin' else "👷 Operador"
        st.markdown(f"👤 **{st.session_state.get('user_name', '')}**")
        st.caption(f"{role_label}  ·  @{st.session_state.get('username', '')}")

        st.markdown("---")

        if st.button("🚪 Sair", use_container_width=True):
            for key in ['authenticated', 'user_id', 'username', 'user_name', 'role']:
                st.session_state.pop(key, None)
            st.rerun()

        st.markdown("---")
        st.caption("Versão 2.0.0")

    # Cabeçalho
    st.markdown(f"# ♻️ {APP_NAME}")
    st.markdown("---")

    # Boas-vindas
    st.markdown(f"### 👋 Olá, {st.session_state.get('user_name', '')}!")

    st.info("""
    **📌 Navegue pelas páginas usando o menu lateral:**

    - 📊 **Dashboard**: Visão geral do negócio
    - 📥 **Entradas**: Registre compras de material
    - 📤 **Saídas**: Registre vendas de material
    - 📦 **Estoque**: Consulte o estoque atual
    - 📝 **Cadastros**: Gerencie materiais e parceiros
    - 📈 **Relatórios**: Análises e exportações
    - 🧾 **Operador**: Atendimento ao cliente (canhotos)
    - 💳 **Pagamentos**: Confirmação de canhotos
    """)

    # Métricas rápidas
    from datetime import datetime
    from services import get_monthly_metrics, get_stock_value_estimate

    today = datetime.now()
    metrics = get_monthly_metrics(today.year, today.month)
    stock_value = get_stock_value_estimate()

    st.markdown("### 📊 Métricas do Mês Atual")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "💰 Compras",
            f"R$ {metrics['total_purchases']:,.2f}",
            delta=f"{metrics['weight_in']:.0f} kg"
        )
    with col2:
        st.metric(
            "💵 Vendas",
            f"R$ {metrics['total_sales']:,.2f}",
            delta=f"{metrics['weight_out']:.0f} kg"
        )

    col3, col4 = st.columns(2)
    with col3:
        st.metric(
            "📈 Lucro Bruto",
            f"R$ {metrics['gross_profit']:,.2f}",
            delta_color="normal" if metrics['gross_profit'] >= 0 else "inverse"
        )
    with col4:
        st.metric(
            "📦 Estoque (estimado)",
            f"R$ {stock_value:,.2f}"
        )

    st.markdown("---")
    st.caption("💡 Use as páginas do menu para gerenciar seu negócio de forma completa!")


if __name__ == "__main__":
    main()
