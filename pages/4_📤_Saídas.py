"""
Página de Saídas (Vendas)
Registra a venda de materiais para clientes
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
    get_current_stock,
    log_action,
)

st.set_page_config(page_title="Saídas", page_icon="📤", layout="centered")

require_auth()

# T3 — Saídas restritas a admin
if st.session_state.get("role") != "admin":
    st.error("🚫 Acesso restrito. Apenas administradores podem registrar saídas.")
    st.stop()

st.title("📤 Saídas (Vendas)")
st.markdown("Registre a venda de materiais")
st.markdown("---")

# ============================================
# FORMULÁRIO DE NOVA SAÍDA
# ============================================

st.markdown("### ➕ Nova Saída")

is_ajuste = st.checkbox(
    "🔧 Ajuste manual (sem comprador)",
    help="Permite remover estoque sem vínculo a comprador. Use apenas para correções administrativas."
)

# Só interrompe se não houver materiais — sem forma de preencher o form
materials = get_all_materials(active_only=True)
if not materials:
    st.error("❌ Nenhum material cadastrado. Cadastre materiais primeiro.")
    st.stop()

# Clientes carregados aqui mas sem st.stop() — erro exibido dentro do form
partners = get_all_partners(active_only=True, partner_type='cliente')
partner_options = {
    p['id']: f"{p['name']} ({p['phone']})" if p['phone'] else p['name']
    for p in partners
}

with st.form("form_saida", clear_on_submit=True):
    saida_date = st.date_input(
        "Data da Saída",
        value=date.today(),
        max_value=date.today(),
        help="Data em que a venda foi realizada"
    )

    material_options = {m['id']: f"{m['name']} ({m['unit']})" for m in materials}
    selected_material = st.selectbox(
        "Material",
        options=list(material_options.keys()),
        format_func=lambda x: material_options[x],
        help="Selecione o material"
    )

    current_stock = get_current_stock(selected_material)
    st.info(f"📦 Estoque disponível: **{current_stock:.2f} kg**")

    selected_partner = None
    if is_ajuste:
        st.warning("🔧 Modo Ajuste Manual — saída sem vínculo a comprador")
    elif not partner_options:
        st.error("❌ Nenhum cliente cadastrado. Cadastre parceiros primeiro ou use o Ajuste Manual.")
    else:
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
        if not is_ajuste and not partner_options:
            st.error("❌ Cadastre um cliente antes de registrar uma saída.")
        elif weight > current_stock:
            st.error(f"❌ Estoque insuficiente. Disponível: {current_stock:.2f} kg")
        else:
            success, message, transaction_id = create_transaction(
                transaction_date=saida_date,
                transaction_type='saida',
                material_id=selected_material,
                partner_id=selected_partner,
                weight_kg=weight,
                price_per_kg=price_per_kg,
                notes=notes,
                role=st.session_state.get("role", "operador")
            )
            if success:
                cliente_label = partner_options.get(selected_partner, "—") if selected_partner else "Ajuste Manual"
                log_action(
                    st.session_state.get('user_id', 0),
                    st.session_state.get('username', '?'),
                    "CREATE", "transaction", transaction_id,
                    {
                        "tipo": "saida",
                        "ajuste_manual": is_ajuste,
                        "material": material_options[selected_material],
                        "cliente": cliente_label,
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
    df_display['partner_name'] = df_display['partner_name'].fillna('— Ajuste Manual')
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
