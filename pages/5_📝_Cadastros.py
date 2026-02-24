"""
Página de Cadastros
CRUD de materiais e parceiros (fornecedores e clientes)
"""

import streamlit as st
from services import (
    get_all_materials,
    create_material,
    deactivate_material,
    activate_material,
    get_all_partners,
    create_partner,
    deactivate_partner,
    activate_partner,
    get_current_prices,
    update_price,
)

st.set_page_config(page_title="Cadastros", page_icon="📝", layout="centered")

# Verifica autenticação
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("⚠️ Acesso negado. Faça login na página principal.")
    st.stop()

st.title("📝 Cadastros")
st.markdown("Gerencie materiais e parceiros")
st.markdown("---")

tab_materials, tab_partners, tab_prices = st.tabs(
    ["📦 Materiais", "🤝 Parceiros", "💲 Preços Vigentes"]
)

# ============================================
# ABA DE MATERIAIS
# ============================================

with tab_materials:
    st.markdown("### ➕ Novo Material")

    with st.form("form_material", clear_on_submit=True):
        col_mn, col_mu = st.columns(2)
        with col_mn:
            mat_name = st.text_input(
                "Nome do Material *",
                placeholder="Ex: Alumínio, Cobre..."
            )
        with col_mu:
            mat_unit = st.selectbox(
                "Unidade",
                ["kg", "ton", "unidade", "m²", "m³"],
                index=0
            )

        submit_mat = st.form_submit_button(
            "💾 Cadastrar Material",
            type="primary",
            use_container_width=True
        )

        if submit_mat:
            if not mat_name or not mat_name.strip():
                st.error("❌ O nome do material é obrigatório")
            else:
                try:
                    create_material(mat_name, mat_unit)
                    st.success(f"✅ Material '{mat_name}' cadastrado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao cadastrar material: {str(e)}")

    st.markdown("---")
    st.markdown("### 📋 Materiais Cadastrados")

    show_inactive_mat = st.checkbox("Mostrar materiais inativos", value=False)
    materials = get_all_materials(active_only=not show_inactive_mat)

    if materials:
        for idx, material in enumerate(materials):
            col_info, col_action = st.columns([4, 1])

            with col_info:
                status_icon = "✅" if material['active'] else "⚫"
                st.write(f"{status_icon} **{material['name']}** — {material['unit']}")

            with col_action:
                if material['active']:
                    if st.button(
                        "Desativar", key=f"deact_mat_{material['id']}",
                        use_container_width=True
                    ):
                        if deactivate_material(material['id']):
                            st.rerun()
                else:
                    if st.button(
                        "Ativar", key=f"act_mat_{material['id']}",
                        use_container_width=True
                    ):
                        if activate_material(material['id']):
                            st.rerun()

            if idx < len(materials) - 1:
                st.divider()
    else:
        st.info("📭 Nenhum material cadastrado ainda")

# ============================================
# ABA DE PARCEIROS
# ============================================

with tab_partners:
    st.markdown("### ➕ Novo Parceiro")

    with st.form("form_partner", clear_on_submit=True):
        part_name = st.text_input(
            "Nome do Parceiro *",
            placeholder="Ex: João da Silva, Metalúrgica XYZ..."
        )

        col_pt, col_pp = st.columns(2)
        with col_pt:
            part_type = st.selectbox(
                "Tipo *",
                ["fornecedor", "cliente", "ambos"],
                format_func=lambda x: {
                    "fornecedor": "🏭 Fornecedor",
                    "cliente": "🛒 Cliente",
                    "ambos": "🔄 Ambos"
                }[x]
            )
        with col_pp:
            part_phone = st.text_input(
                "Telefone",
                placeholder="(00) 00000-0000"
            )

        submit_part = st.form_submit_button(
            "💾 Cadastrar Parceiro",
            type="primary",
            use_container_width=True
        )

        if submit_part:
            if not part_name or not part_name.strip():
                st.error("❌ O nome do parceiro é obrigatório")
            else:
                try:
                    create_partner(part_name, part_type, part_phone)
                    st.success(f"✅ Parceiro '{part_name}' cadastrado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao cadastrar parceiro: {str(e)}")

    st.markdown("---")
    st.markdown("### 📋 Parceiros Cadastrados")

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        filter_type = st.selectbox(
            "Filtrar por tipo",
            ["Todos", "Fornecedores", "Clientes"],
            index=0
        )
    with col_filter2:
        show_inactive_part = st.checkbox("Mostrar inativos", value=False)

    if filter_type == "Fornecedores":
        partners = get_all_partners(active_only=not show_inactive_part, partner_type='fornecedor')
    elif filter_type == "Clientes":
        partners = get_all_partners(active_only=not show_inactive_part, partner_type='cliente')
    else:
        partners = get_all_partners(active_only=not show_inactive_part)

    type_icon_map = {"fornecedor": "🏭", "cliente": "🛒", "ambos": "🔄"}

    if partners:
        for idx, partner in enumerate(partners):
            col_info, col_action = st.columns([4, 1])

            with col_info:
                status_icon = "✅" if partner['active'] else "⚫"
                icon = type_icon_map.get(partner['type'], '')
                st.write(f"{status_icon} **{partner['name']}**")
                st.caption(f"{icon} {partner['type'].title()}  |  {partner['phone'] or '—'}")

            with col_action:
                if partner['active']:
                    if st.button(
                        "Desativar", key=f"deact_part_{partner['id']}",
                        use_container_width=True
                    ):
                        if deactivate_partner(partner['id']):
                            st.rerun()
                else:
                    if st.button(
                        "Ativar", key=f"act_part_{partner['id']}",
                        use_container_width=True
                    ):
                        if activate_partner(partner['id']):
                            st.rerun()

            if idx < len(partners) - 1:
                st.divider()
    else:
        st.info("📭 Nenhum parceiro cadastrado ainda")

# ============================================
# ABA DE PREÇOS VIGENTES
# ============================================

with tab_prices:
    st.markdown("### 💲 Tabela de Preços Vigentes")
    st.info(
        "Defina o preço de compra por kg de cada material. "
        "O operador usará esses preços automaticamente ao registrar um atendimento. "
        "Atualize sempre que os preços mudarem."
    )
    st.markdown("---")

    prices_data = get_current_prices()

    if not prices_data:
        st.warning("⚠️ Nenhum material ativo cadastrado. Adicione materiais na aba Materiais.")
    else:
        for mat in prices_data:
            col1, col2 = st.columns([2, 2])

            with col1:
                st.write(f"**{mat['name']}** ({mat['unit']})")
                if mat['updated_at']:
                    st.caption(f"Atualizado: {mat['updated_at'][:10]}")
                else:
                    st.caption("Preço não definido")

            with col2:
                new_price = st.number_input(
                    label=f"Preço {mat['name']}",
                    label_visibility="collapsed",
                    value=float(mat['price_per_kg']),
                    min_value=0.0,
                    step=0.10,
                    format="%.2f",
                    key=f"price_{mat['id']}"
                )
                if st.button("💾 Salvar", key=f"save_price_{mat['id']}", use_container_width=True):
                    update_price(mat['id'], new_price)
                    st.success(f"✅ {mat['name']} atualizado!")
                    st.rerun()

            st.divider()

st.markdown("---")
st.caption("💡 Dica: Desative materiais e parceiros em vez de excluí-los para manter o histórico")
