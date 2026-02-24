"""
Página de Cadastros
CRUD de materiais, parceiros, preços e usuários (admin)
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
    get_all_users,
    create_user,
    update_user,
    reset_user_password,
    log_action,
)

st.set_page_config(page_title="Cadastros", page_icon="📝", layout="centered")

# Verifica autenticação
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("⚠️ Acesso negado. Faça login na página principal.")
    st.stop()

st.title("📝 Cadastros")
st.markdown("Gerencie materiais e parceiros")
st.markdown("---")

# Monta abas dinamicamente — Usuários só aparece para admin
is_admin = st.session_state.get('role') == 'admin'
tab_labels = ["📦 Materiais", "🤝 Parceiros", "💲 Preços Vigentes"]
if is_admin:
    tab_labels.append("👥 Usuários")

tabs = st.tabs(tab_labels)
tab_materials = tabs[0]
tab_partners = tabs[1]
tab_prices = tabs[2]
tab_users = tabs[3] if is_admin else None

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
                    mat_id = create_material(mat_name, mat_unit)
                    log_action(
                        st.session_state.get('user_id', 0),
                        st.session_state.get('username', '?'),
                        "CREATE", "material", mat_id,
                        {"nome": mat_name.strip(), "unidade": mat_unit}
                    )
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
                            log_action(
                                st.session_state.get('user_id', 0),
                                st.session_state.get('username', '?'),
                                "DEACTIVATE", "material", material['id'],
                                {"nome": material['name']}
                            )
                            st.rerun()
                else:
                    if st.button(
                        "Ativar", key=f"act_mat_{material['id']}",
                        use_container_width=True
                    ):
                        if activate_material(material['id']):
                            log_action(
                                st.session_state.get('user_id', 0),
                                st.session_state.get('username', '?'),
                                "ACTIVATE", "material", material['id'],
                                {"nome": material['name']}
                            )
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
                    part_id = create_partner(part_name, part_type, part_phone)
                    log_action(
                        st.session_state.get('user_id', 0),
                        st.session_state.get('username', '?'),
                        "CREATE", "partner", part_id,
                        {"nome": part_name.strip(), "tipo": part_type}
                    )
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
                            log_action(
                                st.session_state.get('user_id', 0),
                                st.session_state.get('username', '?'),
                                "DEACTIVATE", "partner", partner['id'],
                                {"nome": partner['name']}
                            )
                            st.rerun()
                else:
                    if st.button(
                        "Ativar", key=f"act_part_{partner['id']}",
                        use_container_width=True
                    ):
                        if activate_partner(partner['id']):
                            log_action(
                                st.session_state.get('user_id', 0),
                                st.session_state.get('username', '?'),
                                "ACTIVATE", "partner", partner['id'],
                                {"nome": partner['name']}
                            )
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
                    st.caption(f"Atualizado: {mat['updated_at'].strftime('%d/%m/%Y')}")
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
                    old_price = float(mat['price_per_kg'])
                    update_price(mat['id'], new_price)
                    log_action(
                        st.session_state.get('user_id', 0),
                        st.session_state.get('username', '?'),
                        "UPDATE", "price", mat['id'],
                        {
                            "material": mat['name'],
                            "preco_anterior": old_price,
                            "preco_novo": new_price,
                        }
                    )
                    st.success(f"✅ {mat['name']} atualizado!")
                    st.rerun()

            st.divider()

# ============================================
# ABA DE USUÁRIOS (somente admin)
# ============================================

if is_admin and tab_users is not None:
    with tab_users:
        st.markdown("### ➕ Novo Usuário")

        with st.form("form_user", clear_on_submit=True):
            col_un, col_nn = st.columns(2)
            with col_un:
                new_username = st.text_input(
                    "Login (usuário) *",
                    placeholder="ex: joao.silva"
                )
            with col_nn:
                new_name = st.text_input(
                    "Nome completo *",
                    placeholder="ex: João Silva"
                )

            col_ro, col_pw = st.columns(2)
            with col_ro:
                new_role = st.selectbox(
                    "Perfil *",
                    ["operador", "admin"],
                    format_func=lambda x: "👷 Operador" if x == "operador" else "🔑 Admin"
                )
            with col_pw:
                new_password = st.text_input(
                    "Senha *",
                    type="password",
                    placeholder="mínimo 4 caracteres"
                )

            submit_user = st.form_submit_button(
                "💾 Criar Usuário",
                type="primary",
                use_container_width=True
            )

            if submit_user:
                if not new_username.strip() or not new_name.strip() or not new_password:
                    st.error("❌ Preencha todos os campos obrigatórios")
                elif len(new_password) < 4:
                    st.error("❌ A senha deve ter pelo menos 4 caracteres")
                else:
                    ok, msg = create_user(new_username, new_name, new_password, new_role)
                    if ok:
                        log_action(
                            st.session_state.get('user_id', 0),
                            st.session_state.get('username', '?'),
                            "CREATE", "user", None,
                            {"username": new_username.strip().lower(), "role": new_role}
                        )
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        st.markdown("---")
        st.markdown("### 👥 Usuários Cadastrados")

        users = get_all_users()
        current_user_id = st.session_state.get('user_id')

        if not users:
            st.info("Nenhum usuário encontrado.")
        else:
            for user in users:
                is_self = user['id'] == current_user_id
                role_icon = "🔑" if user['role'] == 'admin' else "👷"
                status_icon = "✅" if user['active'] else "⚫"
                last_login_str = (
                    user['last_login'].strftime("%d/%m/%Y %H:%M")
                    if user['last_login'] else "Nunca"
                )

                label = (
                    f"{status_icon} {role_icon} **{user['name']}** "
                    f"— @{user['username']}"
                    + (" *(você)*" if is_self else "")
                )

                with st.expander(label):
                    st.caption(
                        f"Perfil: {user['role'].title()}  |  "
                        f"Último acesso: {last_login_str}"
                    )
                    st.markdown("")

                    col_a, col_b = st.columns(2)

                    with col_a:
                        # Ativar / Desativar (não pode desativar a si mesmo)
                        if not is_self:
                            if user['active']:
                                if st.button(
                                    "⚫ Desativar",
                                    key=f"deact_user_{user['id']}",
                                    use_container_width=True
                                ):
                                    update_user(user['id'], user['name'], user['role'], 0)
                                    log_action(
                                        current_user_id,
                                        st.session_state.get('username', '?'),
                                        "DEACTIVATE", "user", user['id'],
                                        {"username": user['username'], "nome": user['name']}
                                    )
                                    st.rerun()
                            else:
                                if st.button(
                                    "✅ Ativar",
                                    key=f"act_user_{user['id']}",
                                    use_container_width=True
                                ):
                                    update_user(user['id'], user['name'], user['role'], 1)
                                    log_action(
                                        current_user_id,
                                        st.session_state.get('username', '?'),
                                        "ACTIVATE", "user", user['id'],
                                        {"username": user['username'], "nome": user['name']}
                                    )
                                    st.rerun()
                        else:
                            st.caption("Você não pode desativar sua própria conta.")

                    with col_b:
                        # Alternar perfil (não pode mudar o próprio perfil)
                        if not is_self:
                            new_role_val = "admin" if user['role'] == "operador" else "operador"
                            role_btn_label = (
                                "🔑 Promover a Admin"
                                if new_role_val == "admin"
                                else "👷 Rebaixar a Operador"
                            )
                            if st.button(
                                role_btn_label,
                                key=f"role_user_{user['id']}",
                                use_container_width=True
                            ):
                                update_user(user['id'], user['name'], new_role_val, user['active'])
                                log_action(
                                    current_user_id,
                                    st.session_state.get('username', '?'),
                                    "UPDATE", "user", user['id'],
                                    {
                                        "username": user['username'],
                                        "perfil_anterior": user['role'],
                                        "perfil_novo": new_role_val,
                                    }
                                )
                                st.rerun()

                    # Resetar senha
                    st.markdown("")
                    with st.form(f"reset_pw_{user['id']}"):
                        new_pw = st.text_input(
                            "Nova senha",
                            type="password",
                            key=f"npw_{user['id']}",
                            placeholder="mínimo 4 caracteres"
                        )
                        if st.form_submit_button(
                            "🔑 Resetar Senha", use_container_width=True
                        ):
                            if not new_pw or len(new_pw) < 4:
                                st.error("Senha deve ter pelo menos 4 caracteres")
                            else:
                                reset_user_password(user['id'], new_pw)
                                log_action(
                                    current_user_id,
                                    st.session_state.get('username', '?'),
                                    "UPDATE", "user", user['id'],
                                    {"username": user['username'], "acao": "reset_senha"}
                                )
                                st.success("✅ Senha redefinida com sucesso!")

st.markdown("---")
st.caption("💡 Dica: Desative materiais e parceiros em vez de excluí-los para manter o histórico")
