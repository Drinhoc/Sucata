"""
Página de Cadastros
CRUD de materiais, parceiros, preços, usuários (admin) e configuração fiscal (admin)
"""

import streamlit as st
from auth import require_auth
from services import (
    get_all_materials,
    create_material,
    update_material_fiscal,
    deactivate_material,
    activate_material,
    get_all_partners,
    create_partner,
    update_partner_fiscal,
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
from nfe_service import get_fiscal_config, save_fiscal_config, test_connection

st.set_page_config(page_title="Cadastros", page_icon="📝", layout="centered")

require_auth()

st.title("📝 Cadastros")
st.markdown("Gerencie materiais e parceiros")
st.markdown("---")

# Monta abas dinamicamente — Usuários e Config. Fiscal só aparecem para admin
is_admin = st.session_state.get('role') == 'admin'
tab_labels = ["📦 Materiais", "🤝 Parceiros", "💲 Preços Vigentes"]
if is_admin:
    tab_labels.append("👥 Usuários")
    tab_labels.append("🧾 Config. Fiscal")

tabs = st.tabs(tab_labels)
tab_materials = tabs[0]
tab_partners = tabs[1]
tab_prices = tabs[2]
tab_users = tabs[3] if is_admin else None
tab_fiscal = tabs[4] if is_admin else None

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

        mat_sku = st.text_input(
            "SKU / Código",
            placeholder="Ex: ALU-001, CU-FINO... (opcional)",
            help="Código interno de identificação. Deixe em branco para preencher depois."
        )

        st.markdown("**Dados Fiscais** *(opcional — preencha para emitir NF-e)*")
        col_ncm, col_cfop = st.columns(2)
        with col_ncm:
            mat_ncm = st.text_input(
                "NCM",
                placeholder="Ex: 72042900",
                help="Nomenclatura Comum do Mercosul (8 dígitos)"
            )
        with col_cfop:
            mat_cfop = st.text_input(
                "CFOP",
                placeholder="Ex: 5151",
                help="Código Fiscal de Operações e Prestações"
            )

        col_csosn, col_uf = st.columns(2)
        with col_csosn:
            mat_csosn = st.text_input(
                "CSOSN",
                placeholder="Ex: 400",
                help="Código de Situação da Operação do Simples Nacional"
            )
        with col_uf:
            mat_unidade_fiscal = st.selectbox(
                "Unidade Fiscal",
                ["KG", "TON", "UN", "M2", "M3"],
                index=0,
                help="Unidade utilizada na NF-e"
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
                    mat_id = create_material(
                        mat_name, mat_unit, mat_sku,
                        mat_ncm, mat_cfop, mat_csosn, mat_unidade_fiscal
                    )
                    log_action(
                        st.session_state.get('user_id', 0),
                        st.session_state.get('username', '?'),
                        "CREATE", "material", mat_id,
                        {"nome": mat_name.strip(), "unidade": mat_unit, "sku": mat_sku.strip().upper() or None}
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
                sku_badge = f"`{material['sku']}`  " if material.get('sku') else "*(sem SKU)*  "

                # Indicador fiscal
                has_fiscal = all([
                    material.get('ncm'),
                    material.get('cfop'),
                    material.get('csosn'),
                ])
                fiscal_icon = "🟢" if has_fiscal else "🔴"

                st.write(f"{status_icon} **{material['name']}** — {material['unit']}  {fiscal_icon}")
                st.caption(f"SKU: {sku_badge}  |  NF-e: {'configurada' if has_fiscal else 'pendente'}")

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

            # Editor fiscal inline
            with st.expander(f"🧾 Dados fiscais — {material['name']}"):
                with st.form(f"fiscal_mat_{material['id']}"):
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        f_ncm = st.text_input(
                            "NCM", value=material.get('ncm') or "",
                            key=f"ncm_{material['id']}"
                        )
                        f_cfop = st.text_input(
                            "CFOP", value=material.get('cfop') or "",
                            key=f"cfop_{material['id']}"
                        )
                    with fc2:
                        f_csosn = st.text_input(
                            "CSOSN", value=material.get('csosn') or "",
                            key=f"csosn_{material['id']}"
                        )
                        uf_options = ["KG", "TON", "UN", "M2", "M3"]
                        current_uf = material.get('unidade_fiscal') or "KG"
                        uf_idx = uf_options.index(current_uf) if current_uf in uf_options else 0
                        f_uf = st.selectbox(
                            "Unidade Fiscal", uf_options, index=uf_idx,
                            key=f"uf_{material['id']}"
                        )

                    if st.form_submit_button("💾 Salvar dados fiscais", use_container_width=True):
                        ok = update_material_fiscal(
                            material['id'], f_ncm, f_cfop, f_csosn, f_uf
                        )
                        if ok:
                            log_action(
                                st.session_state.get('user_id', 0),
                                st.session_state.get('username', '?'),
                                "UPDATE", "material_fiscal", material['id'],
                                {"nome": material['name'], "ncm": f_ncm, "cfop": f_cfop, "csosn": f_csosn}
                            )
                            st.success("✅ Dados fiscais atualizados!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao atualizar dados fiscais")

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

        st.markdown("**Dados Fiscais / Endereço** *(opcional — necessário para NF-e)*")

        col_cnpj, col_ie = st.columns(2)
        with col_cnpj:
            part_cnpj_cpf = st.text_input(
                "CNPJ / CPF",
                placeholder="00.000.000/0001-00"
            )
        with col_ie:
            part_ie = st.text_input(
                "Inscrição Estadual",
                placeholder="Deixe em branco se isento"
            )

        col_log, col_num = st.columns([3, 1])
        with col_log:
            part_logradouro = st.text_input("Logradouro", placeholder="Rua, Av., Travessa...")
        with col_num:
            part_numero = st.text_input("Número", placeholder="123")

        col_comp, col_bairro = st.columns(2)
        with col_comp:
            part_complemento = st.text_input("Complemento", placeholder="Sala, Bloco... (opcional)")
        with col_bairro:
            part_bairro = st.text_input("Bairro")

        col_mun, col_ibge = st.columns(2)
        with col_mun:
            part_municipio = st.text_input("Município", placeholder="Ex: São Paulo")
        with col_ibge:
            part_municipio_ibge = st.text_input(
                "Cód. IBGE",
                placeholder="Ex: 3550308",
                help="Código IBGE do município (7 dígitos)"
            )

        col_uf2, col_cep = st.columns(2)
        with col_uf2:
            part_uf = st.text_input("UF", placeholder="SP", max_chars=2)
        with col_cep:
            part_cep = st.text_input("CEP", placeholder="00000-000")

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
                    part_id = create_partner(
                        part_name, part_type, part_phone,
                        part_cnpj_cpf, part_ie,
                        part_logradouro, part_numero, part_complemento,
                        part_bairro, part_municipio, part_municipio_ibge,
                        part_uf, part_cep,
                    )
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

                # Indicador fiscal
                has_fiscal_p = all([
                    partner.get('cnpj_cpf'),
                    partner.get('municipio'),
                    partner.get('uf'),
                    partner.get('cep'),
                ])
                fiscal_icon_p = "🟢" if has_fiscal_p else "🔴"

                st.write(f"{status_icon} **{partner['name']}**  {fiscal_icon_p}")
                st.caption(
                    f"{icon} {partner['type'].title()}  |  "
                    f"{partner['phone'] or '—'}  |  "
                    f"NF-e: {'configurada' if has_fiscal_p else 'pendente'}"
                )

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

            # Editor fiscal inline
            with st.expander(f"🧾 Dados fiscais/endereço — {partner['name']}"):
                with st.form(f"fiscal_part_{partner['id']}"):
                    pf1, pf2 = st.columns(2)
                    with pf1:
                        p_cnpj = st.text_input(
                            "CNPJ / CPF",
                            value=partner.get('cnpj_cpf') or "",
                            key=f"p_cnpj_{partner['id']}"
                        )
                        p_logradouro = st.text_input(
                            "Logradouro",
                            value=partner.get('logradouro') or "",
                            key=f"p_log_{partner['id']}"
                        )
                        p_complemento = st.text_input(
                            "Complemento",
                            value=partner.get('complemento') or "",
                            key=f"p_comp_{partner['id']}"
                        )
                        p_municipio = st.text_input(
                            "Município",
                            value=partner.get('municipio') or "",
                            key=f"p_mun_{partner['id']}"
                        )
                        p_uf = st.text_input(
                            "UF", value=partner.get('uf') or "",
                            max_chars=2,
                            key=f"p_uf_{partner['id']}"
                        )
                    with pf2:
                        p_ie = st.text_input(
                            "Inscrição Estadual",
                            value=partner.get('ie') or "",
                            key=f"p_ie_{partner['id']}"
                        )
                        p_numero = st.text_input(
                            "Número",
                            value=partner.get('numero') or "",
                            key=f"p_num_{partner['id']}"
                        )
                        p_bairro = st.text_input(
                            "Bairro",
                            value=partner.get('bairro') or "",
                            key=f"p_bairro_{partner['id']}"
                        )
                        p_ibge = st.text_input(
                            "Cód. IBGE",
                            value=partner.get('municipio_ibge') or "",
                            key=f"p_ibge_{partner['id']}"
                        )
                        p_cep = st.text_input(
                            "CEP",
                            value=partner.get('cep') or "",
                            key=f"p_cep_{partner['id']}"
                        )

                    if st.form_submit_button("💾 Salvar dados fiscais", use_container_width=True):
                        ok = update_partner_fiscal(
                            partner['id'], p_cnpj, p_ie,
                            p_logradouro, p_numero, p_complemento,
                            p_bairro, p_municipio, p_ibge, p_uf, p_cep,
                        )
                        if ok:
                            log_action(
                                st.session_state.get('user_id', 0),
                                st.session_state.get('username', '?'),
                                "UPDATE", "partner_fiscal", partner['id'],
                                {"nome": partner['name'], "cnpj_cpf": p_cnpj}
                            )
                            st.success("✅ Dados fiscais atualizados!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao atualizar dados fiscais")

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
                if st.button(
                    "💾 Salvar" if is_admin else "🔒 Sem permissão",
                    key=f"save_price_{mat['id']}",
                    use_container_width=True,
                    disabled=not is_admin
                ):
                    old_price = float(mat['price_per_kg'])
                    update_price(mat['id'], new_price, role=st.session_state.get('role', 'operador'))
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

# ============================================
# ABA DE CONFIGURAÇÃO FISCAL (somente admin)
# ============================================

if is_admin and tab_fiscal is not None:
    with tab_fiscal:
        st.markdown("### 🏢 Dados do Emitente (Empresa)")
        st.info(
            "Configure os dados da empresa para emissão de NF-e. "
            "Esses dados são usados como emitente em todas as notas fiscais."
        )

        # Carregar config atual
        cfg = get_fiscal_config() or {}

        with st.form("form_fiscal_config"):
            st.markdown("**Identificação**")
            col_cnpj_e, col_ie_e = st.columns(2)
            with col_cnpj_e:
                cfg_cnpj = st.text_input(
                    "CNPJ *",
                    value=cfg.get('cnpj', ''),
                    placeholder="00.000.000/0001-00"
                )
            with col_ie_e:
                cfg_ie = st.text_input(
                    "Inscrição Estadual",
                    value=cfg.get('ie', ''),
                    placeholder="Número ou ISENTO"
                )

            col_rs, col_fn = st.columns(2)
            with col_rs:
                cfg_razao = st.text_input(
                    "Razão Social *",
                    value=cfg.get('razao_social', ''),
                    placeholder="Nome jurídico da empresa"
                )
            with col_fn:
                cfg_fantasia = st.text_input(
                    "Nome Fantasia",
                    value=cfg.get('nome_fantasia', ''),
                    placeholder="Nome comercial (opcional)"
                )

            col_tel, col_email = st.columns(2)
            with col_tel:
                cfg_tel = st.text_input(
                    "Telefone",
                    value=cfg.get('telefone', ''),
                    placeholder="(00) 00000-0000"
                )
            with col_email:
                cfg_email = st.text_input(
                    "E-mail",
                    value=cfg.get('email', ''),
                    placeholder="nfe@empresa.com.br"
                )

            cfg_crt = st.selectbox(
                "Regime Tributário (CRT) *",
                options=["1", "3"],
                index=0 if cfg.get('crt', '1') == '1' else 1,
                format_func=lambda x: (
                    "1 — Simples Nacional" if x == '1'
                    else "3 — Regime Normal (Lucro Presumido / Real)"
                ),
                help="CRT 1 = Simples Nacional (usa CSOSN). CRT 3 = Regime Normal (usa CST)."
            )

            st.markdown("**Endereço**")
            col_log_e, col_num_e = st.columns([3, 1])
            with col_log_e:
                cfg_log = st.text_input(
                    "Logradouro *",
                    value=cfg.get('logradouro', ''),
                    placeholder="Rua, Av...."
                )
            with col_num_e:
                cfg_num = st.text_input(
                    "Número *",
                    value=cfg.get('numero', ''),
                    placeholder="123"
                )

            col_comp_e, col_bairro_e = st.columns(2)
            with col_comp_e:
                cfg_comp = st.text_input(
                    "Complemento",
                    value=cfg.get('complemento', ''),
                    placeholder="Sala, Galpão... (opcional)"
                )
            with col_bairro_e:
                cfg_bairro = st.text_input(
                    "Bairro *",
                    value=cfg.get('bairro', ''),
                )

            col_mun_e, col_ibge_e = st.columns(2)
            with col_mun_e:
                cfg_mun = st.text_input(
                    "Município *",
                    value=cfg.get('municipio', ''),
                    placeholder="Ex: São Paulo"
                )
            with col_ibge_e:
                cfg_ibge = st.text_input(
                    "Cód. IBGE *",
                    value=cfg.get('municipio_ibge', ''),
                    placeholder="Ex: 3550308",
                    help="Código IBGE de 7 dígitos do município"
                )

            col_uf_e, col_cep_e = st.columns(2)
            with col_uf_e:
                cfg_uf = st.text_input(
                    "UF *",
                    value=cfg.get('uf', ''),
                    placeholder="SP",
                    max_chars=2
                )
            with col_cep_e:
                cfg_cep = st.text_input(
                    "CEP *",
                    value=cfg.get('cep', ''),
                    placeholder="00000-000"
                )

            st.markdown("**Ambiente NF-e**")
            cfg_ambiente = st.radio(
                "Ambiente de emissão",
                options=["homologacao", "producao"],
                index=0 if cfg.get('ambiente', 'homologacao') == 'homologacao' else 1,
                format_func=lambda x: (
                    "🧪 Homologação (testes — NF-e não tem validade fiscal)"
                    if x == 'homologacao'
                    else "🚀 Produção (notas com validade fiscal real)"
                ),
                horizontal=True
            )

            if cfg_ambiente == 'producao':
                st.warning(
                    "⚠️ **Ambiente de Produção**: as notas emitidas terão validade fiscal real. "
                    "Certifique-se de que todos os dados estão corretos."
                )

            save_btn = st.form_submit_button(
                "💾 Salvar Configuração Fiscal",
                type="primary",
                use_container_width=True
            )

            if save_btn:
                required = {
                    "CNPJ": cfg_cnpj,
                    "Razão Social": cfg_razao,
                    "Logradouro": cfg_log,
                    "Número": cfg_num,
                    "Bairro": cfg_bairro,
                    "Município": cfg_mun,
                    "Cód. IBGE": cfg_ibge,
                    "UF": cfg_uf,
                    "CEP": cfg_cep,
                }
                missing = [k for k, v in required.items() if not v or not v.strip()]
                if missing:
                    st.error(f"❌ Campos obrigatórios faltando: {', '.join(missing)}")
                else:
                    ok = save_fiscal_config({
                        'cnpj': cfg_cnpj.strip(),
                        'razao_social': cfg_razao.strip(),
                        'nome_fantasia': cfg_fantasia.strip() or None,
                        'ie': cfg_ie.strip() or None,
                        'crt': cfg_crt,
                        'telefone': cfg_tel.strip() or None,
                        'email': cfg_email.strip() or None,
                        'logradouro': cfg_log.strip(),
                        'numero': cfg_num.strip(),
                        'complemento': cfg_comp.strip() or None,
                        'bairro': cfg_bairro.strip(),
                        'municipio': cfg_mun.strip(),
                        'municipio_ibge': cfg_ibge.strip(),
                        'uf': cfg_uf.strip().upper(),
                        'cep': cfg_cep.strip(),
                        'ambiente': cfg_ambiente,
                    })
                    if ok:
                        log_action(
                            st.session_state.get('user_id', 0),
                            st.session_state.get('username', '?'),
                            "UPDATE", "fiscal_config", None,
                            {"cnpj": cfg_cnpj.strip(), "ambiente": cfg_ambiente}
                        )
                        st.success("✅ Configuração fiscal salva com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao salvar configuração fiscal")

        # Botão de teste de conexão (fora do form)
        st.markdown("---")
        st.markdown("### 🔌 Testar Conexão com Nuvem Fiscal")
        st.caption(
            "Verifica se as credenciais da API (NUVEM_FISCAL_CLIENT_ID / CLIENT_SECRET) "
            "estão corretas e se a conexão com a Nuvem Fiscal está funcionando."
        )

        if st.button("🔌 Testar conexão agora", use_container_width=True):
            with st.spinner("Conectando à API da Nuvem Fiscal..."):
                ok_conn, msg_conn = test_connection()
            if ok_conn:
                st.success(f"✅ {msg_conn}")
            else:
                st.error(f"❌ {msg_conn}")

st.markdown("---")
st.caption("💡 Dica: Desative materiais e parceiros em vez de excluí-los para manter o histórico")
