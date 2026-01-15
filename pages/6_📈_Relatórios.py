"""
Página de Relatórios
Análises detalhadas e exportação de dados
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from io import BytesIO
from services import (
    get_transactions,
    get_all_materials,
    get_all_partners,
    get_material_summary
)

st.set_page_config(page_title="Relatórios", page_icon="📈", layout="wide")

# Verifica autenticação
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("⚠️ Acesso negado. Faça login na página principal.")
    st.stop()

st.title("📈 Relatórios")
st.markdown("Análises detalhadas e exportação de dados")
st.markdown("---")

# ============================================
# FILTROS
# ============================================

st.markdown("### 🔍 Filtros")

col_filter1, col_filter2, col_filter3 = st.columns(3)

with col_filter1:
    # Período
    period_option = st.selectbox(
        "Período",
        ["Últimos 7 dias", "Últimos 15 dias", "Últimos 30 dias", "Últimos 90 dias",
         "Último ano", "Personalizado"],
        index=2
    )

    if period_option == "Personalizado":
        start_date = st.date_input(
            "Data inicial",
            value=date.today() - timedelta(days=30)
        )
        end_date = st.date_input(
            "Data final",
            value=date.today()
        )
    else:
        days_map = {
            "Últimos 7 dias": 7,
            "Últimos 15 dias": 15,
            "Últimos 30 dias": 30,
            "Últimos 90 dias": 90,
            "Último ano": 365
        }
        days = days_map[period_option]
        start_date = date.today() - timedelta(days=days)
        end_date = date.today()

with col_filter2:
    # Tipo de transação
    transaction_type = st.selectbox(
        "Tipo de Transação",
        ["Todas", "Entradas", "Saídas"],
        index=0
    )

    type_filter = None
    if transaction_type == "Entradas":
        type_filter = "entrada"
    elif transaction_type == "Saídas":
        type_filter = "saida"

    # Material
    materials = get_all_materials(active_only=False)
    material_options = {0: "Todos"} | {m['id']: m['name'] for m in materials}
    selected_material = st.selectbox(
        "Material",
        options=list(material_options.keys()),
        format_func=lambda x: material_options[x]
    )

with col_filter3:
    # Parceiro
    partners = get_all_partners(active_only=False)
    partner_options = {0: "Todos"} | {p['id']: p['name'] for p in partners}
    selected_partner = st.selectbox(
        "Parceiro",
        options=list(partner_options.keys()),
        format_func=lambda x: partner_options[x]
    )

    # Botão de aplicar filtros
    st.markdown("##")
    apply_filters = st.button("🔍 Aplicar Filtros", type="primary", use_container_width=True)

st.markdown("---")

# ============================================
# BUSCA DADOS COM FILTROS
# ============================================

transactions = get_transactions(
    start_date=start_date,
    end_date=end_date,
    transaction_type=type_filter,
    material_id=selected_material if selected_material > 0 else None,
    partner_id=selected_partner if selected_partner > 0 else None
)

# ============================================
# MÉTRICAS DO PERÍODO
# ============================================

if transactions:
    df = pd.DataFrame(transactions)

    st.markdown("### 📊 Resumo do Período")

    # Calcula métricas
    total_transactions = len(df)
    total_weight = df['weight_kg'].sum()

    entradas_df = df[df['type'] == 'entrada']
    saidas_df = df[df['type'] == 'saida']

    total_purchases = entradas_df['total_value'].sum() if not entradas_df.empty else 0
    total_sales = saidas_df['total_value'].sum() if not saidas_df.empty else 0
    gross_profit = total_sales - total_purchases

    weight_in = entradas_df['weight_kg'].sum() if not entradas_df.empty else 0
    weight_out = saidas_df['weight_kg'].sum() if not saidas_df.empty else 0

    # Exibe métricas
    col_metric1, col_metric2, col_metric3, col_metric4, col_metric5 = st.columns(5)

    with col_metric1:
        st.metric(
            "Total de Transações",
            total_transactions
        )

    with col_metric2:
        st.metric(
            "💰 Compras",
            f"R$ {total_purchases:,.2f}",
            delta=f"{weight_in:.0f} kg"
        )

    with col_metric3:
        st.metric(
            "💵 Vendas",
            f"R$ {total_sales:,.2f}",
            delta=f"{weight_out:.0f} kg"
        )

    with col_metric4:
        st.metric(
            "📈 Lucro Bruto",
            f"R$ {gross_profit:,.2f}",
            delta=f"{gross_profit:,.2f}",
            delta_color="normal" if gross_profit >= 0 else "inverse"
        )

    with col_metric5:
        st.metric(
            "⚖️ Peso Total",
            f"{total_weight:.2f} kg"
        )

    st.markdown("---")

    # ============================================
    # RESUMO POR MATERIAL
    # ============================================

    st.markdown("### 📦 Resumo por Material")

    material_summary = get_material_summary(start_date, end_date)

    if material_summary:
        df_summary = pd.DataFrame(material_summary)

        # Formata valores
        df_summary_display = df_summary.copy()
        df_summary_display['weight_in'] = df_summary_display['weight_in'].apply(lambda x: f"{x:.2f} kg")
        df_summary_display['weight_out'] = df_summary_display['weight_out'].apply(lambda x: f"{x:.2f} kg")
        df_summary_display['value_in'] = df_summary_display['value_in'].apply(lambda x: f"R$ {x:,.2f}")
        df_summary_display['value_out'] = df_summary_display['value_out'].apply(lambda x: f"R$ {x:,.2f}")
        df_summary_display['profit'] = df_summary_display['profit'].apply(lambda x: f"R$ {x:,.2f}")

        df_summary_display.columns = [
            'Material',
            'Peso Entrada',
            'Peso Saída',
            'Valor Entrada',
            'Valor Saída',
            'Lucro'
        ]

        st.dataframe(
            df_summary_display,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("📭 Nenhum resumo disponível para o período")

    st.markdown("---")

    # ============================================
    # TRANSAÇÕES DETALHADAS
    # ============================================

    st.markdown("### 📋 Transações Detalhadas")

    # Prepara dados para exibição
    df_display = df[[
        'date', 'type', 'material_name', 'partner_name',
        'weight_kg', 'price_per_kg', 'total_value', 'notes'
    ]].copy()

    df_display['type'] = df_display['type'].apply(
        lambda x: '📥 Entrada' if x == 'entrada' else '📤 Saída'
    )
    df_display['weight_kg'] = df_display['weight_kg'].apply(lambda x: f"{x:.2f} kg")
    df_display['price_per_kg'] = df_display['price_per_kg'].apply(lambda x: f"R$ {x:.2f}/kg")
    df_display['total_value'] = df_display['total_value'].apply(lambda x: f"R$ {x:,.2f}")

    df_display.columns = [
        'Data',
        'Tipo',
        'Material',
        'Parceiro',
        'Peso',
        'Preço/kg',
        'Valor Total',
        'Observações'
    ]

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=400
    )

    # ============================================
    # EXPORTAÇÃO CSV
    # ============================================

    st.markdown("---")
    st.markdown("### 📥 Exportar Dados")

    col_export1, col_export2, col_export3 = st.columns([2, 1, 1])

    with col_export1:
        st.info("💡 Exporte os dados filtrados para análise em planilhas (Excel, Google Sheets, etc.)")

    with col_export2:
        # Exporta transações detalhadas
        csv_transactions = df.to_csv(index=False, encoding='utf-8-sig', sep=';', decimal=',')
        st.download_button(
            label="📊 Exportar Transações (CSV)",
            data=csv_transactions,
            file_name=f"transacoes_{start_date}_{end_date}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_export3:
        # Exporta resumo por material
        if material_summary:
            csv_summary = pd.DataFrame(material_summary).to_csv(
                index=False, encoding='utf-8-sig', sep=';', decimal=','
            )
            st.download_button(
                label="📦 Exportar Resumo (CSV)",
                data=csv_summary,
                file_name=f"resumo_materiais_{start_date}_{end_date}.csv",
                mime="text/csv",
                use_container_width=True
            )

else:
    st.info("📭 Nenhuma transação encontrada com os filtros selecionados")
    st.markdown("---")
    st.markdown("### 💡 Dicas")
    st.markdown("""
    - Ajuste o período de busca
    - Remova filtros de material ou parceiro
    - Certifique-se de que há transações cadastradas no sistema
    """)

st.markdown("---")
st.caption("💡 Dica: Use filtros personalizados para análises específicas do seu negócio")
