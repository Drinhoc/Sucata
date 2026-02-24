"""
Página de Logs de Auditoria
Acesso exclusivo para administradores
"""

import json
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from services import get_audit_logs, get_all_users

st.set_page_config(page_title="Logs de Auditoria", page_icon="🔐", layout="centered")

# Verifica autenticação
if not st.session_state.get("authenticated"):
    st.error("⚠️ Acesso negado. Faça login na página principal.")
    st.stop()

# Exclusivo para admins — a aba não aparece no menu para operadores
# (Streamlit 1.32 não suporta ocultar páginas dinamicamente;
#  a restrição é feita aqui no conteúdo da página)
if st.session_state.get("role") != "admin":
    st.error("🚫 Acesso restrito a administradores.")
    st.stop()

st.title("🔐 Logs de Auditoria")
st.markdown("Registro completo de todas as operações realizadas no sistema.")
st.markdown("---")

# ============================================
# FILTROS
# ============================================

col1, col2 = st.columns(2)

with col1:
    period = st.selectbox(
        "Período",
        ["Hoje", "Últimos 7 dias", "Últimos 30 dias", "Todo o período"],
        index=1
    )

with col2:
    users = get_all_users()
    user_opts = {0: "Todos os usuários"} | {u['id']: f"{u['name']} (@{u['username']})" for u in users}
    selected_user = st.selectbox(
        "Usuário",
        options=list(user_opts.keys()),
        format_func=lambda x: user_opts[x]
    )

col3, col4 = st.columns(2)

with col3:
    action_opts = ["Todas", "CREATE", "UPDATE", "DELETE", "CONFIRM", "CANCEL", "ACTIVATE", "DEACTIVATE"]
    selected_action = st.selectbox("Ação", action_opts)

with col4:
    entity_opts = ["Todas", "transaction", "canhoto", "material", "partner", "price", "user"]
    selected_entity = st.selectbox("Entidade", entity_opts)

# Monta start_date conforme período
today = date.today()
if period == "Hoje":
    start_date = today
elif period == "Últimos 7 dias":
    start_date = today - timedelta(days=7)
elif period == "Últimos 30 dias":
    start_date = today - timedelta(days=30)
else:
    start_date = None

logs = get_audit_logs(
    start_date=start_date,
    user_id_filter=selected_user if selected_user > 0 else None,
    action_filter=selected_action if selected_action != "Todas" else None,
    entity_filter=selected_entity if selected_entity != "Todas" else None,
)

st.markdown("---")
st.markdown(f"**{len(logs)} registro(s) encontrado(s)**")

# ============================================
# TABELA DE LOGS
# ============================================

if not logs:
    st.info("📭 Nenhum log encontrado com os filtros selecionados.")
else:
    ACTION_LABELS = {
        "CREATE": "➕ Criar",
        "UPDATE": "✏️ Editar",
        "DELETE": "🗑️ Deletar",
        "CONFIRM": "✅ Confirmar",
        "CANCEL": "❌ Cancelar",
        "ACTIVATE": "✅ Ativar",
        "DEACTIVATE": "⚫ Desativar",
    }

    ENTITY_LABELS = {
        "transaction": "Transação",
        "canhoto": "Canhoto",
        "material": "Material",
        "partner": "Parceiro",
        "price": "Preço",
        "user": "Usuário",
    }

    def _fmt_details(details_str):
        """Formata o JSON de detalhes em texto legível"""
        if not details_str:
            return ""
        try:
            d = json.loads(details_str)
            return "  |  ".join(f"{k}: {v}" for k, v in d.items())
        except Exception:
            return str(details_str)

    rows = []
    for log in logs:
        rows.append({
            "Data/Hora": (
                log['created_at'].strftime("%d/%m/%Y %H:%M:%S")
                if log['created_at'] else ""
            ),
            "Usuário": f"@{log['username']}",
            "Ação": ACTION_LABELS.get(log['action'], log['action']),
            "Entidade": ENTITY_LABELS.get(log['entity'], log['entity']),
            "ID": log['entity_id'] or "—",
            "Detalhes": _fmt_details(log['details']),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Exportação
    st.markdown("---")
    csv_data = pd.DataFrame(logs).to_csv(index=False, encoding='utf-8-sig', sep=';')
    st.download_button(
        label="⬇️ Exportar CSV completo",
        data=csv_data,
        file_name=f"logs_auditoria_{today}.csv",
        mime="text/csv",
        use_container_width=True
    )
