"""
Sistema de Controle de Sucata
Aplicação principal com autenticação e navegação
"""

import streamlit as st
import os
from dotenv import load_dotenv
from db import init_database

# Carrega variáveis de ambiente
load_dotenv()

# Configurações da aplicação
APP_NAME = os.getenv("APP_NAME", "Sistema de Controle de Sucata")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

# Configuração da página
st.set_page_config(
    page_title=APP_NAME,
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def check_password() -> bool:
    """
    Verifica a senha de acesso ao sistema
    Retorna True se autenticado, False caso contrário
    """
    # Se não houver senha configurada, bloqueia o acesso
    if not APP_PASSWORD:
        st.error("⚠️ Sistema não configurado. Configure APP_PASSWORD no arquivo .env")
        st.info("👉 Copie o arquivo .env.example para .env e defina uma senha")
        st.stop()
        return False

    # Verifica se já está autenticado
    if "authenticated" in st.session_state and st.session_state.authenticated:
        return True

    # Mostra tela de login
    st.markdown(f"# 🔐 {APP_NAME}")
    st.markdown("### Login")

    password = st.text_input("Digite a senha:", type="password", key="password_input")

    if st.button("Entrar", type="primary"):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Senha incorreta")

    return False


def main():
    """Função principal da aplicação"""

    # Verifica autenticação
    if not check_password():
        return

    # Inicializa o banco de dados
    init_database()

    # Cabeçalho
    st.markdown(f"# ♻️ {APP_NAME}")
    st.markdown("---")

    # Menu lateral
    with st.sidebar:
        st.markdown("## 📋 Menu")

        # Botão de logout
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

        st.markdown("---")

        # Informações do sistema
        st.markdown("### ℹ️ Sistema")
        st.caption("Versão 1.0.0")
        st.caption("Desenvolvido com Streamlit")

    # Mensagem de boas-vindas na página inicial
    st.markdown("### 👋 Bem-vindo ao Sistema de Controle de Sucata")

    st.info("""
    **📌 Navegue pelas páginas usando o menu lateral:**

    - 📊 **Dashboard**: Visão geral do negócio
    - 📥 **Entradas**: Registre compras de material
    - 📤 **Saídas**: Registre vendas de material
    - 📦 **Estoque**: Consulte o estoque atual
    - 📝 **Cadastros**: Gerencie materiais e parceiros
    - 📈 **Relatórios**: Análises e exportações
    """)

    # Métricas rápidas na página inicial
    from datetime import datetime
    from services import get_monthly_metrics, get_stock_value_estimate

    today = datetime.now()
    metrics = get_monthly_metrics(today.year, today.month)
    stock_value = get_stock_value_estimate()

    st.markdown("### 📊 Métricas do Mês Atual")

    col1, col2, col3, col4 = st.columns(4)

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

    with col3:
        profit_color = "normal" if metrics['gross_profit'] >= 0 else "inverse"
        st.metric(
            "📈 Lucro Bruto",
            f"R$ {metrics['gross_profit']:,.2f}",
            delta=f"{metrics['gross_profit']:,.2f}"
        )

    with col4:
        st.metric(
            "📦 Estoque (estimado)",
            f"R$ {stock_value:,.2f}"
        )

    st.markdown("---")
    st.markdown("💡 **Dica:** Use as páginas do menu para gerenciar seu negócio de forma completa!")


if __name__ == "__main__":
    main()
