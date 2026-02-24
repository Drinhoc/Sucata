"""
Página de Saídas (Vendas)
Registra a venda de materiais para clientes
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from services import (
    get_all_materials,
    get_all_partners,
    create_transaction,
    get_transactions,
    get_current_stock
)

st.set_page_config(page_title="Saídas", page_icon="📤", layout="centered")

# Verifica autenticação
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("⚠️ Acesso negado. Faça login na página principal.")
    st.stop()

st.title("📤 Saídas (Vendas)")
st.markdown("Registre a venda de materiais")
st.markdown("---")

# ============================================
# FORMULÁRIO DE NOVA SAÍDA
# ============================================

st.markdown("### ➕ Nova Saída")

with st.form("form_saida", clear_on_submit=True):
    saida_date = st.date_input(
        "Data da Saída",
        value=date.today(),
        max_value=date.today(),
        help="Data em que a venda foi realizada"
    )

    materials = get_all_materials(active_only=True)
    if not materials:
        st.error("❌ Nenhum material cadastrado. Cadastre materiais primeiro.")
        st.stop()

    material_options = {m['id']: f"{m['name']} ({m['unit']})" for m in materials}
    selected_material = st.selectbox(
        "Material",
        options=list(material_options.keys()),
        format_func=lambda x: material_options[x],
        help="Selecione o material vendido"
    )

    current_stock = get_current_stock(selected_material)
    st.info(f"📦 Estoque disponível: **{current_stock:.2f} kg**")

    partners = get_all_partners(active_only=True, partner_type='cliente')
    if not partners:
        st.error("❌ Nenhum cliente cadastrado. Cadastre parceiros primeiro.")
        st.stop()

    partner_options = {
        p['id']: f"{p['name']} ({p['phone']})" if p['phone'] else p['name']
        for p in partners
    }
    selected_partner = st.selectbox(
        "Cliente",
        options=list(partner_options.keys()),
        format_func=lambda x: partner_options[x],
        help="Selecione o cliente"
    )

    col_w, col_p = st.columns(2)
    with col_w:
        weight = st.number_input(
            "Peso (kg)",
            min_value=0.01,
            max_value=float(current_stock) if current_stock > 0 else 0.01,
            value=min(1.0, float(current_stock)) if current_stock > 0 else 0.01,
            step=0.01,
            format="%.2f",
            help="Não pode exceder o estoque disponível"
        )
    with col_p:
        price_per_kg = st.number_input(
            "Preço/kg (R$)",
            min_value=0.0,
            value=0.0,
            step=0.01,
            format="%.2f",
            help="Preço de venda por kg"
        )

    if weight > current_stock:
        st.error(f"⚠️ Peso maior que o estoque disponível ({current_stock:.2f} kg)")

    st.metric("💰 Valor Total", f"R$ {weight * price_per_kg:,.2f}")

    notes = st.text_area(
        "Observações (opcional)",
        help="Informações adicionais sobre esta saída"
    )

    submitted = st.form_submit_button(
        "💾 Registrar Saída",
        type="primary",
        use_container_width=True
    )

    if submitted:
        if weight > current_stock:
            st.error(f"❌ Estoque insuficiente. Disponível: {current_stock:.2f} kg")
        else:
            success, message, transaction_id = create_transaction(
                transaction_date=saida_date,
                transaction_type='saida',
                material_id=selected_material,
                partner_id=selected_partner,
                weight_kg=weight,
                price_per_kg=price_per_kg,
                notes=notes
            )
            if success:
                st.success(f"✅ {message}")
                st.balloons()
            else:
                st.error(f"❌ {message}")

st.markdown("---")

# ============================================
# HISTÓRICO DE SAÍDAS
# ============================================

st.markdown("### 📋 Histórico de Saídas")

col_filter1, col_filter2, col_filter3 = st.columns(3)

with col_filter1:
    filter_days = st.selectbox(
        "Período",
        [7, 15, 30, 60, 90, 365],
        index=2,
        format_func=lambda x: f"Últimos {x} dias"
    )

with col_filter2:
    materials_filter = get_all_materials(active_only=True)
    material_filter_options = {0: "Todos"} | {m['id']: m['name'] for m in materials_filter}
    selected_material_filter = st.selectbox(
        "Material",
        options=list(material_filter_options.keys()),
        format_func=lambda x: material_filter_options[x]
    )

with col_filter3:
    partners_filter = get_all_partners(active_only=True, partner_type='cliente')
    partner_filter_options = {0: "Todos"} | {p['id']: p['name'] for p in partners_filter}
    selected_partner_filter = st.selectbox(
        "Cliente",
        options=list(partner_filter_options.keys()),
        format_func=lambda x: partner_filter_options[x]
    )

start_date = date.today() - timedelta(days=filter_days)

transactions = get_transactions(
    start_date=start_date,
    transaction_type='saida',
    material_id=selected_material_filter if selected_material_filter > 0 else None,
    partner_id=selected_partner_filter if selected_partner_filter > 0 else None
)

if transactions:
    df = pd.DataFrame(transactions)
    total_weight = df['weight_kg'].sum()
    total_value = df['total_value'].sum()

    col_total1, col_total2, col_total3 = st.columns(3)
    with col_total1:
        st.metric("Total de Saídas", len(df))
    with col_total2:
        st.metric("Peso Total", f"{total_weight:.2f} kg")
    with col_total3:
        st.metric("Valor Total", f"R$ {total_value:,.2f}")

    st.markdown("#### Detalhamento")

    df_display = df[[
        'date', 'material_name', 'partner_name',
        'weight_kg', 'price_per_kg', 'total_value', 'notes'
    ]].copy()
    df_display['weight_kg'] = df_display['weight_kg'].apply(lambda x: f"{x:.2f} kg")
    df_display['price_per_kg'] = df_display['price_per_kg'].apply(lambda x: f"R$ {x:.2f}/kg")
    df_display['total_value'] = df_display['total_value'].apply(lambda x: f"R$ {x:,.2f}")
    df_display.columns = [
        'Data', 'Material', 'Cliente', 'Peso', 'Preço/kg', 'Valor Total', 'Observações'
    ]
    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("📭 Nenhuma saída registrada no período selecionado")

st.markdown("---")
st.caption("💡 Dica: O sistema impede vendas maiores que o estoque disponível")
