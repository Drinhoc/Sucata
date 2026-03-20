"""
Página do Operador — Atendimento ao Cliente
Interface otimizada para mobile: registra materiais e gera canhotos
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from auth import require_auth
from services import get_current_prices, create_canhoto, get_canhoto_with_items, log_action

st.set_page_config(page_title="Operador", page_icon="🧾", layout="centered")

require_auth()


# Inicializa estado da sessão
if "cart_items" not in st.session_state:
    st.session_state.cart_items = []
if "operator_stage" not in st.session_state:
    st.session_state.operator_stage = "collecting"
if "current_canhoto_id" not in st.session_state:
    st.session_state.current_canhoto_id = None


# ============================================================
# ESTADO 1 — COLETANDO ITENS
# ============================================================
if st.session_state.operator_stage == "collecting":

    st.title("🧾 Novo Atendimento")
    st.markdown("---")

    prices_data = get_current_prices()

    if not prices_data:
        st.warning("⚠️ Nenhum material cadastrado. Vá em Cadastros para adicionar materiais.")
        st.stop()

    material_options = {p['name']: p for p in prices_data}

    selected_name = st.selectbox(
        "Material",
        list(material_options.keys()),
        key="sel_material"
    )
    selected_material = material_options[selected_name]
    price = float(selected_material['price_per_kg'])

    if price > 0:
        st.info(f"💲 Preço atual: **R$ {price:.2f}/kg**")
    else:
        st.warning("⚠️ Material sem preço definido. Configure em **Cadastros > Preços Vigentes**.")

    weight = st.number_input(
        "Peso (kg)",
        min_value=0.01,
        step=0.1,
        format="%.2f",
        key="input_weight"
    )

    if price > 0 and weight > 0:
        st.metric("Valor calculado", f"R$ {price * weight:.2f}")

    if st.button(
        "➕  ADICIONAR AO CANHOTO",
        type="primary",
        use_container_width=True,
        disabled=(price <= 0)
    ):
        st.session_state.cart_items.append({
            'material_id': selected_material['id'],
            'material_name': selected_material['name'],
            'weight_kg': weight,
            'price_per_kg': price,
            'total_value': round(price * weight, 2),
        })
        st.rerun()

    st.markdown("---")

    # ---- Carrinho de itens ----
    st.markdown("### 🛒 Itens do Atendimento")

    if not st.session_state.cart_items:
        st.info("Nenhum item adicionado ainda.")
    else:
        total = 0.0

        for i, item in enumerate(st.session_state.cart_items):
            col_info, col_rm = st.columns([5, 1])
            with col_info:
                st.write(f"**{item['material_name']}**")
                st.caption(
                    f"{item['weight_kg']:.2f} kg  ×  R$ {item['price_per_kg']:.2f}/kg"
                    f"  =  **R$ {item['total_value']:.2f}**"
                )
            with col_rm:
                if st.button("✕", key=f"rm_{i}", help="Remover item"):
                    st.session_state.cart_items.pop(i)
                    st.rerun()
            total += item['total_value']

        st.divider()
        st.markdown(f"## 💰 TOTAL: R$ {total:.2f}")
        st.divider()

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🗑️ Limpar tudo", use_container_width=True):
                st.session_state.cart_items = []
                st.rerun()
        with col_btn2:
            if st.button("🖨️  GERAR CANHOTO", type="primary", use_container_width=True):
                st.session_state.operator_stage = "reviewing"
                st.rerun()


# ============================================================
# ESTADO 2 — REVISÃO E CONFIRMAÇÃO
# ============================================================
elif st.session_state.operator_stage == "reviewing":

    st.title("🧾 Revisão do Canhoto")
    st.markdown("---")

    st.markdown("### 📋 Itens a serem registrados")

    total = 0.0
    for item in st.session_state.cart_items:
        st.write(f"**{item['material_name']}**")
        st.caption(
            f"{item['weight_kg']:.2f} kg  ×  R$ {item['price_per_kg']:.2f}/kg"
            f"  =  **R$ {item['total_value']:.2f}**"
        )
        total += item['total_value']

    st.divider()
    st.markdown(f"## 💰 TOTAL: R$ {total:.2f}")
    st.divider()

    client_name = st.text_input(
        "Nome / identificação do cliente (opcional)",
        placeholder="Ex: João Silva, CPF 123...",
        key="client_name_input"
    )

    st.markdown("")
    col_back, col_confirm = st.columns(2)

    with col_back:
        if st.button("⬅️ Voltar", use_container_width=True):
            st.session_state.operator_stage = "collecting"
            st.rerun()

    with col_confirm:
        if st.button("✅ Confirmar e Gerar", type="primary", use_container_width=True):
            items_count = len(st.session_state.cart_items)
            total_val = sum(i['total_value'] for i in st.session_state.cart_items)
            canhoto_id = create_canhoto(
                st.session_state.cart_items,
                client_name=client_name
            )
            log_action(
                st.session_state.get('user_id', 0),
                st.session_state.get('username', '?'),
                "CREATE", "canhoto", canhoto_id,
                {
                    "cliente": client_name.strip() or "Anônimo",
                    "itens": items_count,
                    "valor_total": round(total_val, 2),
                }
            )
            st.session_state.current_canhoto_id = canhoto_id
            st.session_state.cart_items = []
            st.session_state.operator_stage = "printing"
            st.rerun()


# ============================================================
# ESTADO 3 — CANHOTO PARA IMPRESSÃO
# ============================================================
elif st.session_state.operator_stage == "printing":

    canhoto = get_canhoto_with_items(st.session_state.current_canhoto_id)

    if not canhoto:
        st.error("Erro ao carregar o canhoto. Tente novamente.")
        if st.button("Voltar"):
            st.session_state.operator_stage = "collecting"
            st.rerun()
    else:
        now_str = datetime.now().strftime("%d/%m/%Y  %H:%M")
        client_display = canhoto['client_name'] if canhoto['client_name'] else "Cliente"

        rows_html = ""
        for item in canhoto['items']:
            rows_html += f"""
            <tr>
                <td>{item['material_name']}</td>
                <td class="right">{item['weight_kg']:.2f} kg</td>
                <td class="right">R$ {item['price_per_kg']:.2f}</td>
                <td class="right">R$ {item['total_value']:.2f}</td>
            </tr>"""

        canhoto_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ background: #f0f2f6; font-family: 'Courier New', monospace; padding: 12px; }}
            .canhoto-box {{
                max-width: 400px;
                margin: 0 auto;
                border: 2px solid #333;
                padding: 20px;
                background: white;
                color: black;
                border-radius: 4px;
            }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{
                border-bottom: 1px solid #333;
                padding: 4px 2px;
                text-align: left;
                font-size: 13px;
            }}
            td {{ padding: 4px 2px; font-size: 13px; }}
            .right {{ text-align: right; }}
            .center {{ text-align: center; }}
            .sep {{ border-top: 1px dashed #555; margin: 10px 0; }}
            .btn-print {{
                display: block;
                width: 100%;
                margin-top: 14px;
                padding: 12px;
                font-size: 15px;
                cursor: pointer;
                background: #1976D2;
                color: white;
                border: none;
                border-radius: 8px;
            }}
            @media print {{
                body {{ background: white; padding: 0; }}
                .btn-print {{ display: none; }}
            }}
        </style>
        </head>
        <body>
        <div class="canhoto-box">
            <div class="center">
                <strong style="font-size:16px">DEPÓSITO DE SUCATA</strong><br>
                <span>Canhoto Nº <strong>{canhoto['number']}</strong></span><br>
                <span>{now_str}</span><br>
                <span>Cliente: <strong>{client_display}</strong></span>
            </div>
            <div class="sep"></div>
            <table>
                <thead>
                    <tr>
                        <th>Material</th>
                        <th class="right">Peso</th>
                        <th class="right">R$/kg</th>
                        <th class="right">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <div class="sep"></div>
            <div class="right">
                <strong style="font-size:15px">TOTAL: R$ {canhoto['total_value']:.2f}</strong>
            </div>
            <div class="sep"></div>
            <div class="center">
                <span>⏳ Aguardando pagamento</span><br>
                <strong>Apresente ao balcão</strong>
            </div>
        </div>
        <button class="btn-print" onclick="window.print()">🖨️  Imprimir Canhoto</button>
        </body>
        </html>
        """

        st.success(f"✅ Canhoto **#{canhoto['number']}** gerado com sucesso!")
        components.html(canhoto_html, height=480, scrolling=False)

        st.markdown("---")

        if st.button("➕  Novo Atendimento", type="primary", use_container_width=True):
            st.session_state.operator_stage = "collecting"
            st.session_state.current_canhoto_id = None
            st.rerun()
