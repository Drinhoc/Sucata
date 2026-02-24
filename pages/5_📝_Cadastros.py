"""
Página de Cadastros
CRUD de materiais e parceiros (fornecedores e clientes)
"""

import streamlit as st
import pandas as pd
from services import (
    get_all_materials,
    create_material,
    update_material,
    deactivate_material,
    activate_material,
    get_all_partners,
    create_partner,
    update_partner,
    deactivate_partner,
    activate_partner,
    get_current_prices,
    update_price,
)

st.set_page_config(page_title="Cadastros", page_icon="📝", layout="wide")

# Verifica autenticação
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("⚠️ Acesso negado. Faça login na página principal.")
    st.stop()

st.title("📝 Cadastros")
st.markdown("Gerencie materiais e parceiros")
st.markdown("---")

# Seletor de tipo de cadastro
tab_materials, tab_partners, tab_prices = st.tabs(["📦 Materiais", "🤝 Parceiros", "💲 Preços Vigentes"])

# ============================================
# ABA DE MATERIAIS
# ============================================

with tab_materials:
    st.markdown("### 📦 Gerenciamento de Materiais")

    col_mat1, col_mat2 = st.columns([1, 2])

    with col_mat1:
        st.markdown("#### ➕ Novo Material")

        with st.form("form_material", clear_on_submit=True):
            mat_name = st.text_input(
                "Nome do Material *",
                placeholder="Ex: Alumínio, Cobre, Ferro..."
            )

            mat_unit = st.selectbox(
                "Unidade de Medida",
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
                        material_id = create_material(mat_name, mat_unit)
                        st.success(f"✅ Material '{mat_name}' cadastrado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao cadastrar material: {str(e)}")

    with col_mat2:
        st.markdown("#### 📋 Materiais Cadastrados")

        # Filtro de status
        show_inactive_mat = st.checkbox("Mostrar materiais inativos", value=False)

        materials = get_all_materials(active_only=not show_inactive_mat)

        if materials:
            df_mat = pd.DataFrame(materials)

            # Cria colunas para ações
            st.markdown("##### Lista de Materiais")

            for idx, material in enumerate(materials):
                col_name, col_unit, col_status, col_actions = st.columns([3, 1, 1, 2])

                with col_name:
                    st.text(material['name'])

                with col_unit:
                    st.text(material['unit'])

                with col_status:
                    if material['active']:
                        st.success("Ativo", icon="✅")
                    else:
                        st.error("Inativo", icon="❌")

                with col_actions:
                    action_col1, action_col2 = st.columns(2)

                    with action_col1:
                        if material['active']:
                            if st.button("🚫 Desativar", key=f"deact_mat_{material['id']}", use_container_width=True):
                                if deactivate_material(material['id']):
                                    st.success("Material desativado")
                                    st.rerun()

                    with action_col2:
                        if not material['active']:
                            if st.button("✅ Ativar", key=f"act_mat_{material['id']}", use_container_width=True):
                                if activate_material(material['id']):
                                    st.success("Material ativado")
                                    st.rerun()

                if idx < len(materials) - 1:
                    st.divider()
        else:
            st.info("📭 Nenhum material cadastrado ainda")

# ============================================
# ABA DE PARCEIROS
# ============================================

with tab_partners:
    st.markdown("### 🤝 Gerenciamento de Parceiros")

    col_part1, col_part2 = st.columns([1, 2])

    with col_part1:
        st.markdown("#### ➕ Novo Parceiro")

        with st.form("form_partner", clear_on_submit=True):
            part_name = st.text_input(
                "Nome do Parceiro *",
                placeholder="Ex: João da Silva, Metalúrgica XYZ..."
            )

            part_type = st.selectbox(
                "Tipo *",
                ["fornecedor", "cliente", "ambos"],
                format_func=lambda x: {
                    "fornecedor": "🏭 Fornecedor",
                    "cliente": "🛒 Cliente",
                    "ambos": "🔄 Fornecedor e Cliente"
                }[x]
            )

            part_phone = st.text_input(
                "Telefone (opcional)",
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
                        partner_id = create_partner(part_name, part_type, part_phone)
                        st.success(f"✅ Parceiro '{part_name}' cadastrado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao cadastrar parceiro: {str(e)}")

    with col_part2:
        st.markdown("#### 📋 Parceiros Cadastrados")

        # Filtros
        col_filter1, col_filter2 = st.columns(2)

        with col_filter1:
            filter_type = st.selectbox(
                "Filtrar por tipo",
                ["Todos", "Fornecedores", "Clientes"],
                index=0
            )

        with col_filter2:
            show_inactive_part = st.checkbox("Mostrar parceiros inativos", value=False)

        # Busca parceiros
        if filter_type == "Fornecedores":
            partners = get_all_partners(active_only=not show_inactive_part, partner_type='fornecedor')
        elif filter_type == "Clientes":
            partners = get_all_partners(active_only=not show_inactive_part, partner_type='cliente')
        else:
            partners = get_all_partners(active_only=not show_inactive_part)

        if partners:
            st.markdown("##### Lista de Parceiros")

            for idx, partner in enumerate(partners):
                col_name, col_type, col_phone, col_status, col_actions = st.columns([2, 1, 1.5, 1, 2])

                with col_name:
                    st.text(partner['name'])

                with col_type:
                    type_icon = {
                        "fornecedor": "🏭",
                        "cliente": "🛒",
                        "ambos": "🔄"
                    }
                    st.text(f"{type_icon.get(partner['type'], '')} {partner['type'].title()}")

                with col_phone:
                    st.text(partner['phone'] if partner['phone'] else "-")

                with col_status:
                    if partner['active']:
                        st.success("Ativo", icon="✅")
                    else:
                        st.error("Inativo", icon="❌")

                with col_actions:
                    action_col1, action_col2 = st.columns(2)

                    with action_col1:
                        if partner['active']:
                            if st.button("🚫 Desativar", key=f"deact_part_{partner['id']}", use_container_width=True):
                                if deactivate_partner(partner['id']):
                                    st.success("Parceiro desativado")
                                    st.rerun()

                    with action_col2:
                        if not partner['active']:
                            if st.button("✅ Ativar", key=f"act_part_{partner['id']}", use_container_width=True):
                                if activate_partner(partner['id']):
                                    st.success("Parceiro ativado")
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
        col_header1, col_header2, col_header3 = st.columns([3, 2, 2])
        with col_header1:
            st.markdown("**Material**")
        with col_header2:
            st.markdown("**Preço atual (R$/kg)**")
        with col_header3:
            st.markdown("**Última atualização**")

        st.markdown("---")

        for mat in prices_data:
            col1, col2, col3 = st.columns([3, 2, 2])

            with col1:
                st.write(f"**{mat['name']}** ({mat['unit']})")

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
                    st.success(f"✅ Preço de {mat['name']} atualizado!")
                    st.rerun()

            with col3:
                if mat['updated_at']:
                    st.caption(mat['updated_at'])
                else:
                    st.caption("Não definido")

            st.divider()

st.markdown("---")
st.caption("💡 Dica: Desative materiais e parceiros em vez de excluí-los para manter o histórico")
