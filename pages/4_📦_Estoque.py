"""
Página de Estoque
Visualização do estoque atual de todos os materiais
"""

import streamlit as st
import pandas as pd
from services import get_all_stock, get_current_stock

st.set_page_config(page_title="Estoque", page_icon="📦", layout="centered")

# Verifica autenticação
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("⚠️ Acesso negado. Faça login na página principal.")
    st.stop()

st.title("📦 Estoque")
st.markdown("Visualização do estoque atual")
st.markdown("---")

# ============================================
# BUSCA DADOS DE ESTOQUE
# ============================================

stock_data = get_all_stock()

if not stock_data:
    st.warning("⚠️ Nenhum material cadastrado no sistema")
    st.info("👉 Cadastre materiais na página de Cadastros para começar")
    st.stop()

df = pd.DataFrame(stock_data)

# ============================================
# RESUMO GERAL
# ============================================

# Calcula valores estimados
df['estimated_value'] = df['current_stock'] * df['avg_buy_price']
df['potential_revenue'] = df['current_stock'] * df['avg_sell_price']
df['potential_profit'] = df['potential_revenue'] - df['estimated_value']

# Totais
total_stock_value = df['estimated_value'].sum()
total_potential_revenue = df['potential_revenue'].sum()
total_potential_profit = df['potential_profit'].sum()
total_materials = len(df)
materials_in_stock = len(df[df['current_stock'] > 0])

st.markdown("### 📊 Resumo Geral")

col1, col2 = st.columns(2)
with col1:
    st.metric(
        "Total de Materiais",
        total_materials,
        delta=f"{materials_in_stock} em estoque"
    )
with col2:
    st.metric(
        "Valor em Estoque",
        f"R$ {total_stock_value:,.2f}",
        help="Valor estimado baseado no preço médio de compra"
    )

col3, col4 = st.columns(2)
with col3:
    st.metric(
        "Receita Potencial",
        f"R$ {total_potential_revenue:,.2f}",
        help="Receita potencial se vender todo o estoque ao preço médio"
    )
with col4:
    st.metric(
        "Lucro Potencial",
        f"R$ {total_potential_profit:,.2f}",
        delta=f"{total_potential_profit:,.2f}",
        delta_color="normal" if total_potential_profit >= 0 else "inverse",
        help="Lucro potencial da venda de todo o estoque"
    )

st.markdown("---")

# ============================================
# FILTROS
# ============================================

col_filter1, col_filter2 = st.columns(2)

with col_filter1:
    show_filter = st.selectbox(
        "Exibir",
        ["Todos", "Somente com estoque", "Somente sem estoque"],
        index=1
    )

with col_filter2:
    search_text = st.text_input(
        "🔍 Buscar material",
        placeholder="Digite o nome do material..."
    )

# Aplica filtros
df_filtered = df.copy()

if show_filter == "Somente com estoque":
    df_filtered = df_filtered[df_filtered['current_stock'] > 0]
elif show_filter == "Somente sem estoque":
    df_filtered = df_filtered[df_filtered['current_stock'] == 0]

if search_text:
    df_filtered = df_filtered[
        df_filtered['name'].str.contains(search_text, case=False, na=False)
    ]

# ============================================
# TABELA DE ESTOQUE
# ============================================

st.markdown("### 📋 Estoque Detalhado")

if df_filtered.empty:
    st.info("📭 Nenhum material encontrado com os filtros selecionados")
else:
    # Prepara dados para exibição
    df_display = df_filtered[[
        'name', 'unit', 'current_stock', 'total_in', 'total_out',
        'avg_buy_price', 'avg_sell_price', 'estimated_value', 'potential_profit'
    ]].copy()

    # Formata valores
    df_display['current_stock'] = df_display['current_stock'].apply(lambda x: f"{x:.2f}")
    df_display['total_in'] = df_display['total_in'].apply(lambda x: f"{x:.2f}")
    df_display['total_out'] = df_display['total_out'].apply(lambda x: f"{x:.2f}")
    df_display['avg_buy_price'] = df_display['avg_buy_price'].apply(lambda x: f"R$ {x:.2f}")
    df_display['avg_sell_price'] = df_display['avg_sell_price'].apply(lambda x: f"R$ {x:.2f}")
    df_display['estimated_value'] = df_display['estimated_value'].apply(lambda x: f"R$ {x:,.2f}")
    df_display['potential_profit'] = df_display['potential_profit'].apply(lambda x: f"R$ {x:,.2f}")

    # Renomeia colunas
    df_display.columns = [
        'Material',
        'Unidade',
        'Estoque Atual',
        'Total Entrado',
        'Total Saído',
        'Preço Médio Compra',
        'Preço Médio Venda',
        'Valor Estimado',
        'Lucro Potencial'
    ]

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True
    )

    # Estatísticas adicionais
    st.markdown("---")
    st.markdown("### 📈 Análise")

    col_analysis1, col_analysis2 = st.columns(2)

    with col_analysis1:
        st.markdown("#### 🔝 Maiores Estoques (por quantidade)")
        top_stock = df_filtered.nlargest(5, 'current_stock')[['name', 'current_stock', 'unit']].copy()
        if not top_stock.empty:
            top_stock['current_stock'] = top_stock.apply(
                lambda row: f"{row['current_stock']:.2f} {row['unit']}", axis=1
            )
            top_stock_display = top_stock[['name', 'current_stock']].copy()
            top_stock_display.columns = ['Material', 'Estoque']
            st.dataframe(top_stock_display, use_container_width=True, hide_index=True)
        else:
            st.info("Sem dados")

    with col_analysis2:
        st.markdown("#### 💰 Maiores Valores em Estoque")
        top_value = df_filtered.nlargest(5, 'estimated_value')[['name', 'estimated_value']].copy()
        if not top_value.empty:
            top_value['estimated_value'] = top_value['estimated_value'].apply(
                lambda x: f"R$ {x:,.2f}"
            )
            top_value.columns = ['Material', 'Valor Estimado']
            st.dataframe(top_value, use_container_width=True, hide_index=True)
        else:
            st.info("Sem dados")

st.markdown("---")
st.caption("💡 Dica: Os valores são estimativas baseadas nos preços médios históricos")
