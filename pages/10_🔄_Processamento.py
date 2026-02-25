"""
Página de Processamento Interno
Converte material de origem em material de destino sem impacto financeiro.
Acessível a administradores e operadores.
"""

import streamlit as st
from auth import require_auth
from services import get_all_materials, get_current_stock, process_internal

st.set_page_config(page_title="Processamento", page_icon="🔄", layout="centered")

require_auth()

st.title("🔄 Processamento Interno")
st.markdown(
    "Converta material de origem em material de destino "
    "(ex: latinhas soltas → latinha prensada) sem movimentação financeira."
)
st.markdown("---")

# ============================================
# CARREGA MATERIAIS COM ESTOQUE
# ============================================

materials = get_all_materials(active_only=True)

if not materials:
    st.warning("⚠️ Nenhum material cadastrado. Vá em Cadastros para adicionar.")
    st.stop()

# Pré-carrega estoques para exibição reativa
stocks = {m["id"]: get_current_stock(m["id"]) for m in materials}

mat_ids = [m["id"] for m in materials]
mat_names = {m["id"]: m["name"] for m in materials}


def label(mid):
    return f"{mat_names[mid]}  ({stocks[mid]:.2f} kg disponíveis)"


# ============================================
# FORMULÁRIO DE PROCESSAMENTO
# ============================================

col1, col2 = st.columns(2)

with col1:
    mat_from = st.selectbox(
        "Material de Origem *",
        options=mat_ids,
        format_func=label,
        key="proc_from"
    )

with col2:
    destino_ids = [m for m in mat_ids if m != mat_from]
    if not destino_ids:
        st.error("❌ É necessário pelo menos 2 materiais cadastrados.")
        st.stop()
    mat_to = st.selectbox(
        "Material de Destino *",
        options=destino_ids,
        format_func=label,
        key="proc_to"
    )

stock_from = stocks[mat_from]

if stock_from <= 0:
    st.error(f"❌ Sem estoque disponível de **{mat_names[mat_from]}**.")
    st.stop()

st.info(f"📦 Estoque disponível: **{stock_from:.2f} kg** de {mat_names[mat_from]}")

weight = st.number_input(
    "Peso a processar (kg) *",
    min_value=0.01,
    max_value=float(stock_from),
    step=0.01,
    format="%.2f",
    key="proc_weight"
)

st.markdown("")

if st.button("⚙️ Processar", type="primary", use_container_width=True):
    ok, msg, proc_code = process_internal(
        material_from_id=mat_from,
        material_to_id=mat_to,
        weight_kg=weight,
        user_id=st.session_state.get("user_id", 0),
        username=st.session_state.get("username", "?"),
    )
    if ok:
        st.success(f"✅ {msg}")
        st.info(f"🔖 Código de rastreio: **{proc_code}**")
        st.markdown(
            f"**{weight:.2f} kg** de _{mat_names[mat_from]}_ "
            f"→ _{mat_names[mat_to]}_"
        )
        st.balloons()
        # Força atualização dos estoques no próximo rerun
        stocks[mat_from] = get_current_stock(mat_from)
        stocks[mat_to] = get_current_stock(mat_to)
    else:
        st.error(f"❌ {msg}")

st.markdown("---")
st.caption(
    "💡 O processamento não gera movimentação financeira. "
    "Ambas as transações são registradas com valor R$ 0,00 "
    "e aparecem no histórico com o código PROC#."
)
