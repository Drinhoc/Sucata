"""
Página de Pagamentos — Balcão
Confirmação de pagamento dos canhotos pendentes e histórico
"""

import streamlit as st
from auth import require_auth
from services import get_canhotos, get_canhoto_with_items, confirm_canhoto, cancel_canhoto, log_action

st.set_page_config(page_title="Pagamentos", page_icon="💳", layout="centered")

require_auth()

st.title("💳 Pagamentos — Balcão")
st.markdown("Confirme o pagamento dos canhotos emitidos pelo operador.")
st.markdown("---")

tab_pending, tab_history = st.tabs(["⏳ Aguardando Pagamento", "📋 Histórico"])


# ============================================================
# ABA — CANHOTOS PENDENTES
# ============================================================
with tab_pending:

    pending = get_canhotos(status='pendente')

    if not pending:
        st.success("✅ Nenhum canhoto aguardando pagamento no momento.")
    else:
        st.markdown(f"**{len(pending)} canhoto(s) aguardando pagamento:**")
        st.markdown("")

        for canhoto in pending:
            client_label = canhoto['client_name'] if canhoto['client_name'] else "Cliente Anônimo"
            created_str = (
                canhoto['created_at'].strftime("%d/%m/%Y %H:%M")
                if canhoto['created_at'] else ""
            )

            with st.container(border=True):
                st.markdown(
                    f"### Canhoto #{canhoto['number']}  —  R$ {canhoto['total_value']:.2f}"
                )
                st.caption(f"🕐 Emitido: {created_str}  |  👤 {client_label}")

                full = get_canhoto_with_items(canhoto['id'])
                if full and full['items']:
                    for it in full['items']:
                        st.write(
                            f"• **{it['material_name']}**: "
                            f"{it['weight_kg']:.2f} kg = R$ {it['total_value']:.2f}"
                        )

                st.markdown("")
                col_confirm, col_cancel = st.columns(2)

                with col_confirm:
                    if st.button(
                        "✅ Confirmar Pagamento",
                        key=f"confirm_{canhoto['id']}",
                        type="primary",
                        use_container_width=True
                    ):
                        success, msg = confirm_canhoto(canhoto['id'])
                        if success:
                            log_action(
                                st.session_state.get('user_id', 0),
                                st.session_state.get('username', '?'),
                                "CONFIRM", "canhoto", canhoto['id'],
                                {
                                    "numero": canhoto['number'],
                                    "cliente": client_label,
                                    "valor_total": canhoto['total_value'],
                                }
                            )
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

                with col_cancel:
                    if st.button(
                        "❌ Cancelar",
                        key=f"cancel_{canhoto['id']}",
                        use_container_width=True
                    ):
                        cancel_canhoto(canhoto['id'])
                        log_action(
                            st.session_state.get('user_id', 0),
                            st.session_state.get('username', '?'),
                            "CANCEL", "canhoto", canhoto['id'],
                            {
                                "numero": canhoto['number'],
                                "cliente": client_label,
                            }
                        )
                        st.info("Canhoto cancelado.")
                        st.rerun()


# ============================================================
# ABA — HISTÓRICO
# ============================================================
with tab_history:

    all_canhotos = get_canhotos()
    history = [c for c in all_canhotos if c['status'] != 'pendente']

    if not history:
        st.info("Nenhum canhoto no histórico ainda.")
    else:
        confirmados = [c for c in history if c['status'] == 'confirmado']
        cancelados = [c for c in history if c['status'] == 'cancelado']
        total_confirmado = sum(c['total_value'] for c in confirmados)

        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Confirmados", len(confirmados))
        col2.metric("❌ Cancelados", len(cancelados))
        col3.metric("💰 Total Pago", f"R$ {total_confirmado:,.2f}")

        st.markdown("---")

        for canhoto in history:
            client_label = canhoto['client_name'] if canhoto['client_name'] else "Anônimo"
            created_str = (
                canhoto['created_at'].strftime("%d/%m/%Y %H:%M")
                if canhoto['created_at'] else ""
            )
            status_badge = (
                "✅ Confirmado" if canhoto['status'] == 'confirmado' else "❌ Cancelado"
            )

            with st.expander(
                f"{status_badge}  |  #{canhoto['number']}"
                f"  —  R$ {canhoto['total_value']:.2f}"
                f"  —  {client_label}  —  {created_str}"
            ):
                full = get_canhoto_with_items(canhoto['id'])
                if full and full['items']:
                    for it in full['items']:
                        st.write(
                            f"• **{it['material_name']}**: {it['weight_kg']:.2f} kg  "
                            f"@ R$ {it['price_per_kg']:.2f}/kg  =  R$ {it['total_value']:.2f}"
                        )
                    st.markdown(f"**Total: R$ {canhoto['total_value']:.2f}**")
