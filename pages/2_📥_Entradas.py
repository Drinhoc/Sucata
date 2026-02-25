"""
Página de Entradas (Compras)
Registra a compra de materiais de fornecedores
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from auth import require_auth
from services import (
    get_all_materials,
    get_all_partners,
    create_transaction,
    get_transactions,
    log_action,
)

st.set_page_config(page_title="Entradas", page_icon="📥", layout="centered")

require_auth()

st.title("📥 Entradas (Compras)")
st.markdown("Registre a compra de materiais")
st.markdown("---")

# ============================================
# FORMULÁRIO DE NOVA ENTRADA
# ============================================

st.markdown("### ➕ Nova Entrada")

with st.form("form_entrada", clear_on_submit=True):
    entrada_date = st.date_input(
        "Data da Entrada",
        value=date.today(),
        max_value=date.today(),
        help="Data em que a compra foi realizada"
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
        help="Selecione o material comprado"
    )

    partners = get_all_partners(active_only=True, partner_type='fornecedor')
    if not partners:
        st.error("❌ Nenhum fornecedor cadastrado. Cadastre parceiros primeiro.")
        st.stop()

    partner_options = {
        p['id']: f"{p['name']} ({p['phone']})" if p['phone'] else p['name']
        for p in partners
    }
    selected_partner = st.selectbox(
        "Fornecedor",
        options=list(partner_options.keys()),
        format_func=lambda x: partner_options[x],
        help="Selecione o fornecedor"
    )

    col_w, col_p = st.columns(2)
    with col_w:
        weight = st.number_input(
            "Peso (kg)",
            min_value=0.01,
            value=1.0,
            step=0.01,
            format="%.2f",
            help="Quantidade em kg"
        )
    with col_p:
        price_per_kg = st.number_input(
            "Preço/kg (R$)",
            min_value=0.0,
            value=0.0,
            step=0.01,
            format="%.2f",
            help="Preço pago por kg"
        )

    st.metric("💰 Valor Total", f"R$ {weight * price_per_kg:,.2f}")

    notes = st.text_area(
        "Observações (opcional)",
        help="Informações adicionais sobre esta entrada"
    )

    submitted = st.form_submit_button(
        "💾 Registrar Entrada",
        type="primary",
        use_container_width=True
    )

    if submitted:
        success, message, transaction_id = create_transaction(
            transaction_date=entrada_date,
            transaction_type='entrada',
            material_id=selected_material,
            partner_id=selected_partner,
            weight_kg=weight,
            price_per_kg=price_per_kg,
            notes=notes
        )
        if success:
            log_action(
                st.session_state.get('user_id', 0),
                st.session_state.get('username', '?'),
                "CREATE", "transaction", transaction_id,
                {
                    "tipo": "entrada",
                    "material": material_options[selected_material],
                    "parceiro": partner_options[selected_partner],
                    "peso_kg": weight,
                    "preco_kg": price_per_kg,
                    "valor_total": round(weight * price_per_kg, 2),
                }
            )
            st.success(f"✅ {message}")
            st.balloons()
        else:
            st.error(f"❌ {message}")

st.markdown("---")

# ============================================
# HISTÓRICO DE ENTRADAS
# ============================================

st.markdown("### 📋 Histórico de Entradas")

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
    partners_filter = get_all_partners(active_only=True, partner_type='fornecedor')
    partner_filter_options = {0: "Todos"} | {p['id']: p['name'] for p in partners_filter}
    selected_partner_filter = st.selectbox(
        "Fornecedor",
        options=list(partner_filter_options.keys()),
        format_func=lambda x: partner_filter_options[x]
    )

start_date = date.today() - timedelta(days=filter_days)

transactions = get_transactions(
    start_date=start_date,
    transaction_type='entrada',
    material_id=selected_material_filter if selected_material_filter > 0 else None,
    partner_id=selected_partner_filter if selected_partner_filter > 0 else None
)

if transactions:
    df = pd.DataFrame(transactions)
    total_weight = df['weight_kg'].sum()
    total_value = df['total_value'].sum()

    col_total1, col_total2, col_total3 = st.columns(3)
    with col_total1:
        st.metric("Total de Entradas", len(df))
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
        'Data', 'Material', 'Fornecedor', 'Peso', 'Preço/kg', 'Valor Total', 'Observações'
    ]
    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("📭 Nenhuma entrada registrada no período selecionado")

st.markdown("---")
st.caption("💡 Dica: Mantenha o cadastro de fornecedores atualizado para facilitar o registro de entradas")
