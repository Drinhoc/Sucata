"""
Página do Operador — Atendimento ao Cliente
Interface otimizada para mobile: letras grandes, botões grandes, fácil de usar na balança
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from auth import require_auth
from services import get_current_prices, create_canhoto, get_canhoto_with_items, log_action

st.set_page_config(page_title="Atendimento", page_icon="🧾", layout="centered")

require_auth()

# ============================================================
# CSS — mobile first, tudo grande e fácil de tocar
# ============================================================
st.markdown("""
<style>
/* ---- Inputs numéricos: bem grandes, centralizados ---- */
div[data-testid="stNumberInput"] input {
    font-size: 2.4rem !important;
    height: 4.2rem !important;
    text-align: center !important;
    font-weight: 700 !important;
    letter-spacing: 0.05rem;
}
div[data-testid="stNumberInput"] button {
    height: 4.2rem !important;
    width: 3.2rem !important;
    font-size: 1.4rem !important;
}

/* ---- Selectbox: label e campo maiores ---- */
div[data-testid="stSelectbox"] label p {
    font-size: 1.15rem !important;
    font-weight: 600 !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] {
    min-height: 3.2rem !important;
    font-size: 1.15rem !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] span {
    font-size: 1.15rem !important;
}

/* ---- Text input (nome do cliente) ---- */
div[data-testid="stTextInput"] input {
    font-size: 1.2rem !important;
    height: 3.2rem !important;
}
div[data-testid="stTextInput"] label p {
    font-size: 1.1rem !important;
    font-weight: 600 !important;
}

/* ---- Todos os botões: mais altos e com fonte maior ---- */
.stButton > button {
    min-height: 3.2rem !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
}

/* ---- Botão primário: destaque máximo ---- */
.stButton > button[kind="primary"] {
    min-height: 4.2rem !important;
    font-size: 1.35rem !important;
    letter-spacing: 0.03rem;
}

/* ---- Métricas ---- */
div[data-testid="stMetricValue"] {
    font-size: 2.8rem !important;
    font-weight: 700 !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 1.05rem !important;
}

/* ---- Info/Warning boxes ---- */
div[data-testid="stAlert"] p {
    font-size: 1.05rem !important;
}
</style>
""", unsafe_allow_html=True)


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

    st.title("🧾 Atendimento")

    # Indicador de passo
    n_itens = len(st.session_state.cart_items)
    if n_itens == 0:
        st.caption("Passo 1 de 3 — Adicione os materiais")
    else:
        st.caption(f"Passo 1 de 3 — {n_itens} item(ns) no canhoto")

    st.markdown("---")

    prices_data = get_current_prices()

    if not prices_data:
        st.warning("⚠️ Nenhum material cadastrado. Vá em **Cadastros** para adicionar materiais.")
        st.stop()

    material_options = {p['name']: p for p in prices_data}

    selected_name = st.selectbox(
        "📦 Material",
        list(material_options.keys()),
        key="sel_material"
    )
    selected_material = material_options[selected_name]
    price = float(selected_material['price_per_kg'])

    # Preço do material em destaque
    if price > 0:
        st.markdown(
            f"<div style='background:#e8f5e9;border-radius:10px;padding:12px 18px;"
            f"margin:4px 0 16px 0;font-size:1.2rem;font-weight:600;color:#1b5e20;'>"
            f"💲 Preço: R$ {price:.2f} / kg</div>",
            unsafe_allow_html=True
        )
    else:
        st.warning("⚠️ Material sem preço. Configure em **Cadastros → Preços Vigentes**.")

    st.markdown("**⚖️ Peso (kg)**")
    weight = st.number_input(
        "Peso (kg)",
        label_visibility="collapsed",
        min_value=0.01,
        step=0.5,
        format="%.2f",
        key="input_weight"
    )

    # Valor calculado em destaque
    if price > 0 and weight > 0:
        valor = price * weight
        st.markdown(
            f"<div style='background:#fff3e0;border-radius:12px;padding:16px 18px;"
            f"margin:12px 0;text-align:center;'>"
            f"<span style='font-size:1rem;color:#6d4c41;font-weight:600;'>VALOR CALCULADO</span><br>"
            f"<span style='font-size:3rem;font-weight:800;color:#e65100;'>R$ {valor:.2f}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("")
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

    # ---- Carrinho ----
    if not st.session_state.cart_items:
        st.markdown(
            "<div style='text-align:center;padding:24px;color:#999;font-size:1.1rem;'>"
            "🛒 Nenhum item ainda.<br>Selecione o material, pese e clique em <b>Adicionar</b>."
            "</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown("### 🛒 Itens do Canhoto")

        total = 0.0
        for i, item in enumerate(st.session_state.cart_items):
            col_info, col_rm = st.columns([6, 1])
            with col_info:
                st.markdown(f"**{item['material_name']}**")
                st.markdown(
                    f"<span style='font-size:1.05rem;color:#555;'>"
                    f"{item['weight_kg']:.2f} kg &nbsp;×&nbsp; R$ {item['price_per_kg']:.2f}/kg"
                    f"&nbsp;&nbsp;=&nbsp;&nbsp;"
                    f"<b style='color:#1a237e;'>R$ {item['total_value']:.2f}</b></span>",
                    unsafe_allow_html=True
                )
            with col_rm:
                if st.button("✕", key=f"rm_{i}", help="Remover"):
                    st.session_state.cart_items.pop(i)
                    st.rerun()
            total += item['total_value']
            st.divider()

        # Total grande
        st.markdown(
            f"<div style='background:#1a237e;border-radius:14px;padding:20px;"
            f"text-align:center;margin:8px 0 20px 0;'>"
            f"<span style='color:#b3c5ff;font-size:1rem;font-weight:600;'>TOTAL DO CANHOTO</span><br>"
            f"<span style='color:white;font-size:3.2rem;font-weight:800;'>R$ {total:.2f}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

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

    st.title("✅ Revisar e Confirmar")
    st.caption("Passo 2 de 3 — Confira os itens antes de imprimir")
    st.markdown("---")

    total = 0.0
    for item in st.session_state.cart_items:
        st.markdown(f"### {item['material_name']}")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Peso", f"{item['weight_kg']:.2f} kg")
        with col_b:
            st.metric("Preço/kg", f"R$ {item['price_per_kg']:.2f}")
        with col_c:
            st.metric("Valor", f"R$ {item['total_value']:.2f}")
        total += item['total_value']
        st.divider()

    # Total
    st.markdown(
        f"<div style='background:#1a237e;border-radius:14px;padding:20px;"
        f"text-align:center;margin:12px 0 24px 0;'>"
        f"<span style='color:#b3c5ff;font-size:1rem;font-weight:600;'>TOTAL A PAGAR</span><br>"
        f"<span style='color:white;font-size:3.2rem;font-weight:800;'>R$ {total:.2f}</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    st.markdown("**👤 Nome do cliente** *(opcional)*")
    client_name = st.text_input(
        "Nome do cliente",
        label_visibility="collapsed",
        placeholder="Ex: João Silva",
        key="client_name_input"
    )

    st.markdown("")
    col_back, col_confirm = st.columns(2)

    with col_back:
        if st.button("⬅️ Voltar e corrigir", use_container_width=True):
            st.session_state.operator_stage = "collecting"
            st.rerun()

    with col_confirm:
        if st.button("✅ CONFIRMAR E IMPRIMIR", type="primary", use_container_width=True):
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
        st.title("🖨️ Canhoto Gerado!")
        st.caption("Passo 3 de 3 — Imprima e entregue ao cliente")
        st.markdown("---")

        st.success(f"✅ Canhoto **#{canhoto['number']}** gerado! Aguarda confirmação de pagamento.")

        now_str = datetime.now().strftime("%d/%m/%Y  %H:%M")
        client_display = canhoto['client_name'] if canhoto['client_name'] else "Cliente"

        rows_html = ""
        for item in canhoto['items']:
            rows_html += f"""
            <tr>
                <td style="padding:8px 4px;font-size:15px;">{item['material_name']}</td>
                <td style="padding:8px 4px;font-size:15px;text-align:right;">{item['weight_kg']:.2f} kg</td>
                <td style="padding:8px 4px;font-size:15px;text-align:right;">R$ {item['price_per_kg']:.2f}</td>
                <td style="padding:8px 4px;font-size:16px;text-align:right;font-weight:bold;">R$ {item['total_value']:.2f}</td>
            </tr>"""

        canhoto_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ background: #f0f2f6; font-family: 'Courier New', monospace; padding: 12px; }}
            .canhoto-box {{
                max-width: 420px;
                margin: 0 auto;
                border: 2.5px solid #333;
                padding: 22px 18px;
                background: white;
                color: black;
                border-radius: 6px;
            }}
            .center {{ text-align: center; }}
            .sep {{ border-top: 1.5px dashed #666; margin: 12px 0; }}
            table {{ width: 100%; border-collapse: collapse; }}
            thead th {{
                border-bottom: 1.5px solid #333;
                padding: 6px 4px;
                text-align: left;
                font-size: 13px;
                text-transform: uppercase;
            }}
            thead th:not(:first-child) {{ text-align: right; }}
            .total-row {{
                background: #f5f5f5;
                font-size: 18px;
                font-weight: bold;
            }}
            .btn-print {{
                display: block;
                width: 100%;
                margin-top: 16px;
                padding: 16px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                background: #1565C0;
                color: white;
                border: none;
                border-radius: 10px;
                letter-spacing: 0.05rem;
            }}
            .btn-print:active {{ background: #0d47a1; }}
            @media print {{
                body {{ background: white; padding: 0; }}
                .btn-print {{ display: none; }}
                .canhoto-box {{ border: 1.5px solid #000; }}
            }}
        </style>
        </head>
        <body>
        <div class="canhoto-box">
            <div class="center">
                <strong style="font-size:18px;letter-spacing:0.05rem;">DEPÓSITO DE SUCATA</strong><br><br>
                <span style="font-size:15px;">Canhoto Nº <strong style="font-size:18px;">{canhoto['number']}</strong></span><br>
                <span style="font-size:14px;color:#555;">{now_str}</span><br><br>
                <span style="font-size:15px;">Cliente: <strong>{client_display}</strong></span>
            </div>
            <div class="sep"></div>
            <table>
                <thead>
                    <tr>
                        <th>Material</th>
                        <th style="text-align:right;">Peso</th>
                        <th style="text-align:right;">R$/kg</th>
                        <th style="text-align:right;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <div class="sep"></div>
            <table>
                <tr class="total-row">
                    <td style="padding:10px 4px;" colspan="3">TOTAL A PAGAR</td>
                    <td style="padding:10px 4px;text-align:right;font-size:20px;">R$ {canhoto['total_value']:.2f}</td>
                </tr>
            </table>
            <div class="sep"></div>
            <div class="center" style="font-size:14px;color:#444;line-height:1.6;">
                ⏳ <strong>Aguardando confirmação de pagamento</strong><br>
                Apresente este canhoto ao caixa
            </div>
        </div>
        <button class="btn-print" onclick="window.print()">🖨️&nbsp; Imprimir Canhoto</button>
        </body>
        </html>
        """

        components.html(canhoto_html, height=520, scrolling=False)

        st.markdown("---")

        if st.button("➕  NOVO ATENDIMENTO", type="primary", use_container_width=True):
            st.session_state.operator_stage = "collecting"
            st.session_state.current_canhoto_id = None
            st.rerun()
