"""
Página de Saídas (Vendas)
Registra a venda de materiais para clientes e permite emitir NF-e
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
from nfe_service import emit_nfe, get_nfe_status, cancel_nfe, download_nfe_file

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
# HISTÓRICO DE SAÍDAS + NF-e
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

    # Tabela resumida
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

    # ============================================
    # PAINEL NF-e por transação
    # ============================================
    st.markdown("---")
    st.markdown("#### 🧾 Notas Fiscais (NF-e)")
    st.caption(
        "Emita, consulte e cancele NF-e para cada saída. "
        "Configure o emitente em Cadastros → Config. Fiscal antes de emitir."
    )

    _NF_STATUS_LABEL = {
        None: ("⬜", "Não emitida"),
        "autorizada": ("✅", "Autorizada"),
        "cancelada": ("❌", "Cancelada"),
        "denegada": ("⛔", "Denegada"),
        "erro": ("🔴", "Erro"),
        "processando": ("🔄", "Processando"),
    }

    for tx in transactions:
        tx_id = tx['id']
        nf_status = tx.get('nf_status')
        nf_numero = tx.get('nf_numero')
        nf_chave = tx.get('nf_chave')
        partner_label = tx.get('partner_name') or "Ajuste Manual"
        mat_label = tx.get('material_name', '?')
        date_label = tx['date'].strftime('%d/%m/%Y') if hasattr(tx['date'], 'strftime') else str(tx['date'])

        icon, status_label = _NF_STATUS_LABEL.get(nf_status, ("❓", nf_status or "—"))
        nf_num_label = f"NF {nf_numero}" if nf_numero else "Sem número"

        expander_label = (
            f"{icon} {date_label} — {mat_label} | {partner_label} | "
            f"{nf_num_label} ({status_label})"
        )

        with st.expander(expander_label):
            col_nf_info, col_nf_act = st.columns([2, 1])

            with col_nf_info:
                st.caption(f"ID Transação: #{tx_id}")
                if nf_numero:
                    st.write(f"**NF-e #{nf_numero}** — Série {tx.get('nf_serie', '1')}")
                if nf_chave:
                    st.code(nf_chave, language=None)
                if tx.get('nf_emitida_em'):
                    em_str = (
                        tx['nf_emitida_em'].strftime('%d/%m/%Y %H:%M')
                        if hasattr(tx['nf_emitida_em'], 'strftime')
                        else str(tx['nf_emitida_em'])
                    )
                    st.caption(f"Emitida em: {em_str}")

            with col_nf_act:
                # Emitir NF-e (só se ainda não emitida ou em erro)
                if nf_status not in ('autorizada', 'cancelada', 'denegada', 'processando'):
                    btn_label = "🔄 Reemitir NF-e" if nf_status == 'erro' else "🧾 Emitir NF-e"
                    if st.button(btn_label, key=f"emit_{tx_id}", use_container_width=True):
                        with st.spinner("Emitindo NF-e..."):
                            ok_e, msg_e, _ = emit_nfe(tx_id)
                        if ok_e:
                            log_action(
                                st.session_state.get('user_id', 0),
                                st.session_state.get('username', '?'),
                                "EMIT_NFE", "transaction", tx_id,
                                {"status": "autorizada"}
                            )
                            st.success(f"✅ {msg_e}")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg_e}")

                # Consultar status
                if nf_chave:
                    if st.button("🔍 Consultar status", key=f"status_{tx_id}", use_container_width=True):
                        with st.spinner("Consultando..."):
                            ok_s, msg_s = get_nfe_status(tx_id)
                        if ok_s:
                            st.success(f"✅ {msg_s}")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ {msg_s}")

            # Downloads DANFE / XML (apenas se autorizada e com chave)
            if nf_status == 'autorizada' and nf_chave:
                st.markdown("")
                col_pdf, col_xml = st.columns(2)

                with col_pdf:
                    if st.button("📄 Download DANFE (PDF)", key=f"danfe_{tx_id}", use_container_width=True):
                        with st.spinner("Baixando DANFE..."):
                            ok_d, content_d, filename_d = download_nfe_file(nf_chave, "pdf")
                        if ok_d:
                            st.download_button(
                                label="💾 Salvar DANFE",
                                data=content_d,
                                file_name=filename_d,
                                mime="application/pdf",
                                key=f"save_danfe_{tx_id}",
                                use_container_width=True
                            )
                        else:
                            st.error(f"❌ {filename_d}")

                with col_xml:
                    if st.button("📋 Download XML", key=f"xml_{tx_id}", use_container_width=True):
                        with st.spinner("Baixando XML..."):
                            ok_x, content_x, filename_x = download_nfe_file(nf_chave, "xml")
                        if ok_x:
                            st.download_button(
                                label="💾 Salvar XML",
                                data=content_x,
                                file_name=filename_x,
                                mime="application/xml",
                                key=f"save_xml_{tx_id}",
                                use_container_width=True
                            )
                        else:
                            st.error(f"❌ {filename_x}")

            # Cancelar NF-e (apenas se autorizada)
            if nf_status == 'autorizada' and nf_chave:
                st.markdown("")
                with st.expander("⚠️ Cancelar esta NF-e"):
                    st.warning(
                        "O cancelamento só é possível dentro do prazo legal (normalmente 24h "
                        "após a autorização). Após cancelada, não pode ser revertida."
                    )
                    with st.form(f"cancel_nfe_{tx_id}"):
                        justificativa = st.text_area(
                            "Justificativa *",
                            placeholder="Mínimo 15 caracteres. Ex: Venda cancelada a pedido do cliente.",
                            help="Obrigatório pela SEFAZ — mínimo 15 caracteres"
                        )
                        if st.form_submit_button(
                            "❌ Confirmar Cancelamento",
                            use_container_width=True
                        ):
                            if not justificativa or len(justificativa.strip()) < 15:
                                st.error("❌ A justificativa deve ter pelo menos 15 caracteres")
                            else:
                                with st.spinner("Cancelando NF-e..."):
                                    ok_c, msg_c = cancel_nfe(tx_id, justificativa.strip())
                                if ok_c:
                                    log_action(
                                        st.session_state.get('user_id', 0),
                                        st.session_state.get('username', '?'),
                                        "CANCEL_NFE", "transaction", tx_id,
                                        {"justificativa": justificativa.strip()}
                                    )
                                    st.success(f"✅ {msg_c}")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg_c}")
else:
    st.info("📭 Nenhuma saída registrada no período selecionado")

st.markdown("---")
st.caption("💡 Dica: Configure emitente e dados fiscais dos parceiros antes de emitir NF-e")
