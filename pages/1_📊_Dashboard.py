"""
Página de Dashboard
Visão geral do negócio com métricas e resumos
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from services import (
    get_monthly_metrics,
    get_stock_value_estimate,
    get_material_summary,
    get_all_stock,
    get_transactions
)

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="centered")

# Verifica autenticação
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("⚠️ Acesso negado. Faça login na página principal.")
    st.stop()

st.title("📊 Dashboard")
st.markdown("Visão geral do seu negócio")
st.markdown("---")

# Seletor de mês/ano para análise
col_filter1, col_filter2 = st.columns(2)

with col_filter1:
    current_date = datetime.now()
    selected_month = st.selectbox(
        "Mês",
        range(1, 13),
        index=current_date.month - 1,
        format_func=lambda x: [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ][x - 1]
    )

with col_filter2:
    selected_year = st.selectbox(
        "Ano",
        range(current_date.year - 5, current_date.year + 1),
        index=5
    )

# Busca métricas do mês selecionado
metrics = get_monthly_metrics(selected_year, selected_month)
stock_value = get_stock_value_estimate()

# ============================================
# MÉTRICAS PRINCIPAIS
# ============================================

st.markdown("### 💰 Métricas do Período")

col1, col2 = st.columns(2)
with col1:
    st.metric(
        label="Compras (Entradas)",
        value=f"R$ {metrics['total_purchases']:,.2f}",
        delta=f"{metrics['weight_in']:.0f} kg"
    )
with col2:
    st.metric(
        label="Vendas (Saídas)",
        value=f"R$ {metrics['total_sales']:,.2f}",
        delta=f"{metrics['weight_out']:.0f} kg"
    )

col3, col4 = st.columns(2)
with col3:
    profit = metrics['gross_profit']
    st.metric(
        label="Lucro Bruto",
        value=f"R$ {profit:,.2f}",
        delta=f"{profit:,.2f}",
        delta_color="normal" if profit >= 0 else "inverse"
    )
with col4:
    st.metric(
        label="Estoque Total Estimado",
        value=f"R$ {stock_value:,.2f}"
    )

st.markdown("---")

# ============================================
# RESUMO POR MATERIAL
# ============================================

st.markdown("### 📦 Resumo por Material (Período Selecionado)")

# Calcula data inicial e final do mês
from datetime import date
start_date = date(selected_year, selected_month, 1)
if selected_month == 12:
    end_date = date(selected_year + 1, 1, 1)
else:
    end_date = date(selected_year, selected_month + 1, 1)

material_summary = get_material_summary(start_date, end_date)

if material_summary:
    df_summary = pd.DataFrame(material_summary)

    # Formata valores monetários
    df_summary['value_in'] = df_summary['value_in'].apply(lambda x: f"R$ {x:,.2f}")
    df_summary['value_out'] = df_summary['value_out'].apply(lambda x: f"R$ {x:,.2f}")
    df_summary['profit'] = df_summary['profit'].apply(lambda x: f"R$ {x:,.2f}")
    df_summary['weight_in'] = df_summary['weight_in'].apply(lambda x: f"{x:.2f} kg")
    df_summary['weight_out'] = df_summary['weight_out'].apply(lambda x: f"{x:.2f} kg")

    # Renomeia colunas
    df_summary.columns = [
        'Material',
        'Peso Entrada',
        'Peso Saída',
        'Valor Entrada',
        'Valor Saída',
        'Lucro'
    ]

    st.dataframe(
        df_summary,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("📭 Nenhuma transação registrada neste período")

st.markdown("---")

# ============================================
# ESTOQUE ATUAL
# ============================================

st.markdown("### 📦 Estoque Atual")

stock_data = get_all_stock()

if stock_data:
    df_stock = pd.DataFrame(stock_data)

    # Filtra apenas materiais com estoque > 0
    df_stock = df_stock[df_stock['current_stock'] > 0]

    if not df_stock.empty:
        # Calcula valor estimado em estoque
        df_stock['estimated_value'] = df_stock['current_stock'] * df_stock['avg_buy_price']

        # Formata para exibição
        df_display = df_stock[['name', 'current_stock', 'avg_buy_price', 'avg_sell_price', 'estimated_value']].copy()
        df_display['current_stock'] = df_display['current_stock'].apply(lambda x: f"{x:.2f} kg")
        df_display['avg_buy_price'] = df_display['avg_buy_price'].apply(lambda x: f"R$ {x:.2f}/kg")
        df_display['avg_sell_price'] = df_display['avg_sell_price'].apply(lambda x: f"R$ {x:.2f}/kg")
        df_display['estimated_value'] = df_display['estimated_value'].apply(lambda x: f"R$ {x:,.2f}")

        df_display.columns = [
            'Material',
            'Estoque Atual',
            'Preço Médio Compra',
            'Preço Médio Venda',
            'Valor Estimado'
        ]

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("📭 Nenhum material em estoque no momento")
else:
    st.info("📭 Nenhum material cadastrado")

st.markdown("---")

# ============================================
# ÚLTIMAS TRANSAÇÕES
# ============================================

st.markdown("### 📋 Últimas Transações")

recent_transactions = get_transactions(limit=10)

if recent_transactions:
    df_trans = pd.DataFrame(recent_transactions)

    # Seleciona e formata colunas
    df_display = df_trans[[
        'date', 'type', 'material_name', 'partner_name',
        'weight_kg', 'price_per_kg', 'total_value'
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
        'Valor Total'
    ]

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("📭 Nenhuma transação registrada ainda")

st.markdown("---")
st.caption("💡 Dica: Use a página de Relatórios para análises mais detalhadas")
