"""
Página de Relatórios
Análises completas em 5 abas: Visão Geral, Evolução Temporal,
Por Material, Por Parceiro e Transações detalhadas.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from services import (
    get_transactions,
    get_all_materials,
    get_all_partners,
    get_period_comparison,
    get_temporal_evolution,
    get_material_analysis,
    get_partner_analysis,
)

st.set_page_config(page_title="Relatórios", page_icon="📈", layout="centered")

# Verifica autenticação
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("⚠️ Acesso negado. Faça login na página principal.")
    st.stop()

st.title("📈 Relatórios")
st.markdown("Análises completas do período selecionado")
st.markdown("---")

# ============================================
# FILTROS GLOBAIS
# ============================================

period_option = st.selectbox(
    "Período",
    ["Últimos 7 dias", "Últimos 15 dias", "Últimos 30 dias",
     "Últimos 90 dias", "Último ano", "Personalizado"],
    index=2
)
if period_option == "Personalizado":
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("De", value=date.today() - timedelta(days=30))
    with col_d2:
        end_date = st.date_input("Até", value=date.today())
else:
    days_map = {
        "Últimos 7 dias": 7, "Últimos 15 dias": 15,
        "Últimos 30 dias": 30, "Últimos 90 dias": 90, "Último ano": 365
    }
    start_date = date.today() - timedelta(days=days_map[period_option])
    end_date = date.today()

col_f2, col_f3 = st.columns(2)

with col_f2:
    materials = get_all_materials(active_only=False)
    mat_opts = {0: "Todos os materiais"} | {m['id']: m['name'] for m in materials}
    selected_material = st.selectbox(
        "Material",
        options=list(mat_opts.keys()),
        format_func=lambda x: mat_opts[x]
    )

with col_f3:
    partners = get_all_partners(active_only=False)
    par_opts = {0: "Todos os parceiros"} | {p['id']: p['name'] for p in partners}
    selected_partner = st.selectbox(
        "Parceiro",
        options=list(par_opts.keys()),
        format_func=lambda x: par_opts[x]
    )

mat_id = selected_material if selected_material > 0 else None
par_id = selected_partner if selected_partner > 0 else None
delta_days = (end_date - start_date).days

# Granularidade temporal automática
if delta_days <= 31:
    granularity = 'day'
    gran_label = 'dia'
elif delta_days <= 120:
    granularity = 'week'
    gran_label = 'semana'
else:
    granularity = 'month'
    gran_label = 'mês'

st.markdown("---")

# ============================================
# ABAS
# ============================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Visão Geral",
    "📅 Evolução Temporal",
    "📦 Por Material",
    "🤝 Por Parceiro",
    "📋 Transações",
])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1 — VISÃO GERAL
# ──────────────────────────────────────────────────────────────────────────────

with tab1:
    comparison = get_period_comparison(start_date, end_date)
    prev = comparison['anterior']

    def _delta_pct(curr, prev_val):
        if prev_val == 0:
            return None
        return f"{((curr - prev_val) / prev_val * 100):+.1f}%"

    # --- FINANCEIRO ---
    st.markdown("### 💰 Financeiro")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Compras (Entradas)",
            f"R$ {comparison['compras']:,.2f}",
            delta=_delta_pct(comparison['compras'], prev['compras']),
            help="Total pago por material no período."
        )

    with col2:
        st.metric(
            "Vendas (Saídas)",
            f"R$ {comparison['vendas']:,.2f}",
            delta=_delta_pct(comparison['vendas'], prev['vendas']),
            help="Total recebido nas vendas do período."
        )

    with col3:
        lucro = comparison['lucro']
        st.metric(
            "Lucro Bruto",
            f"R$ {lucro:,.2f}",
            delta=_delta_pct(lucro, prev['lucro']),
            delta_color="normal" if lucro >= 0 else "inverse",
            help="Vendas menos Compras. Não considera custos operacionais."
        )

    st.markdown("---")

    # --- EFICIÊNCIA ---
    st.markdown("### 📊 Eficiência")
    col4, col5, col6 = st.columns(3)

    with col4:
        margem = comparison['margem_pct']
        prev_margem = prev['margem_pct']
        diff_margem = f"{margem - prev_margem:+.1f}%" if prev['vendas'] > 0 else None
        st.metric(
            "Margem Bruta",
            f"{margem:.1f}%",
            delta=diff_margem,
            help="Lucro Bruto ÷ Vendas × 100. Quanto da receita vira resultado."
        )

    with col5:
        st.metric(
            "Ticket Médio por Compra",
            f"R$ {comparison['ticket_medio']:,.2f}",
            delta=_delta_pct(comparison['ticket_medio'], prev['ticket_medio']),
            help="Valor médio por transação de entrada."
        )

    with col6:
        ratio = comparison['vendas'] / comparison['compras'] if comparison['compras'] > 0 else 0
        prev_ratio = prev['vendas'] / prev['compras'] if prev['compras'] > 0 else 0
        diff_ratio = f"{ratio - prev_ratio:+.2f}x" if prev['compras'] > 0 else None
        st.metric(
            "Relação Venda / Compra",
            f"{ratio:.2f}x",
            delta=diff_ratio,
            help="Quanto você recupera por R$1 investido em compras. Acima de 1.0 é positivo."
        )

    st.markdown("---")

    # --- VOLUME ---
    st.markdown("### ⚖️ Volume")
    col7, col8, col9 = st.columns(3)

    with col7:
        st.metric(
            "Peso Comprado",
            f"{comparison['peso_in']:,.1f} kg",
            delta=_delta_pct(comparison['peso_in'], prev['peso_in'])
        )

    with col8:
        st.metric(
            "Peso Vendido",
            f"{comparison['peso_out']:,.1f} kg",
            delta=_delta_pct(comparison['peso_out'], prev['peso_out'])
        )

    with col9:
        st.metric(
            "Transações no Período",
            comparison['transacoes'],
            delta=comparison['transacoes'] - prev['transacoes'] if prev['transacoes'] > 0 else None
        )

    # Nota de comparação
    if prev['compras'] > 0 or prev['vendas'] > 0:
        prev_start = comparison['prev_start']
        prev_end = comparison['prev_end']
        st.caption(
            f"ℹ️ Deltas comparados ao período anterior "
            f"({prev_start.strftime('%d/%m/%Y')} → {prev_end.strftime('%d/%m/%Y')})"
        )
    else:
        st.caption("ℹ️ Sem dados no período anterior para comparação de deltas.")


# ──────────────────────────────────────────────────────────────────────────────
# TAB 2 — EVOLUÇÃO TEMPORAL
# ──────────────────────────────────────────────────────────────────────────────

with tab2:
    evol_data = get_temporal_evolution(start_date, end_date, granularity)

    if not evol_data:
        st.info("📭 Sem dados para o período selecionado.")
    else:
        df_evol = pd.DataFrame(evol_data).set_index('periodo')
        st.caption(
            f"Agrupamento automático por **{gran_label}** "
            f"({delta_days} dias no período selecionado)"
        )

        # Compras vs Vendas
        st.markdown("#### 💰 Compras × Vendas por período")
        st.bar_chart(
            df_evol[['compras', 'vendas']],
            color=["#FF6B6B", "#4ECDC4"]
        )

        st.markdown("---")

        # Lucro bruto
        st.markdown("#### 📈 Lucro Bruto por período")
        st.bar_chart(df_evol[['lucro']], color="#45B7D1")

        st.markdown("---")

        # Volume em kg
        st.markdown("#### ⚖️ Volume (kg) por período")
        st.bar_chart(
            df_evol[['peso_comprado', 'peso_vendido']],
            color=["#FF6B6B", "#4ECDC4"]
        )

        # Tabela de dados brutos
        with st.expander("🔍 Ver tabela de dados"):
            df_tbl = df_evol.copy()
            df_tbl['compras'] = df_tbl['compras'].apply(lambda x: f"R$ {x:,.2f}")
            df_tbl['vendas'] = df_tbl['vendas'].apply(lambda x: f"R$ {x:,.2f}")
            df_tbl['lucro'] = df_tbl['lucro'].apply(lambda x: f"R$ {x:,.2f}")
            df_tbl['peso_comprado'] = df_tbl['peso_comprado'].apply(lambda x: f"{x:,.1f} kg")
            df_tbl['peso_vendido'] = df_tbl['peso_vendido'].apply(lambda x: f"{x:,.1f} kg")
            df_tbl.columns = ['Compras', 'Vendas', 'Peso Comprado', 'Peso Vendido', 'Transações', 'Lucro']
            st.dataframe(df_tbl, use_container_width=True)


# ──────────────────────────────────────────────────────────────────────────────
# TAB 3 — POR MATERIAL
# ──────────────────────────────────────────────────────────────────────────────

with tab3:
    mat_data = get_material_analysis(start_date, end_date)

    if not mat_data:
        st.info("📭 Sem movimentação de materiais no período.")
    else:
        df_mat = pd.DataFrame(mat_data)

        # Tabela principal
        st.markdown("#### 📋 Resumo por Material")
        df_mat_disp = df_mat[[
            'material', 'peso_comprado', 'peso_vendido',
            'valor_compras', 'valor_vendas', 'lucro',
            'margem_pct', 'preco_medio_compra', 'preco_medio_venda', 'spread_kg'
        ]].copy()

        df_mat_disp['peso_comprado'] = df_mat_disp['peso_comprado'].apply(lambda x: f"{x:,.1f} kg")
        df_mat_disp['peso_vendido'] = df_mat_disp['peso_vendido'].apply(lambda x: f"{x:,.1f} kg")
        df_mat_disp['valor_compras'] = df_mat_disp['valor_compras'].apply(lambda x: f"R$ {x:,.2f}")
        df_mat_disp['valor_vendas'] = df_mat_disp['valor_vendas'].apply(lambda x: f"R$ {x:,.2f}")
        df_mat_disp['lucro'] = df_mat_disp['lucro'].apply(lambda x: f"R$ {x:,.2f}")
        df_mat_disp['margem_pct'] = df_mat_disp['margem_pct'].apply(lambda x: f"{x:.1f}%")
        df_mat_disp['preco_medio_compra'] = df_mat_disp['preco_medio_compra'].apply(
            lambda x: f"R$ {x:.2f}/kg" if x > 0 else "—"
        )
        df_mat_disp['preco_medio_venda'] = df_mat_disp['preco_medio_venda'].apply(
            lambda x: f"R$ {x:.2f}/kg" if x > 0 else "—"
        )
        df_mat_disp['spread_kg'] = df_mat_disp['spread_kg'].apply(
            lambda x: f"R$ {x:.2f}/kg" if x > 0 else "—"
        )
        df_mat_disp.columns = [
            'Material', 'Peso Comprado', 'Peso Vendido',
            'Valor Compras', 'Valor Vendas', 'Lucro',
            'Margem %', 'Preço Médio Compra', 'Preço Médio Venda', 'Spread/kg'
        ]
        st.dataframe(df_mat_disp, use_container_width=True, hide_index=True)

        st.markdown("---")

        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.markdown("#### 💰 Lucro por Material")
            df_lucro_mat = df_mat[['material', 'lucro']].set_index('material')
            st.bar_chart(df_lucro_mat, color="#45B7D1")

        with col_c2:
            st.markdown("#### 📊 Preço Médio: Compra × Venda (R$/kg)")
            df_precos = df_mat[['material', 'preco_medio_compra', 'preco_medio_venda']].copy()
            df_precos = df_precos[
                (df_precos['preco_medio_compra'] > 0) | (df_precos['preco_medio_venda'] > 0)
            ]
            if not df_precos.empty:
                df_precos = df_precos.set_index('material')
                st.bar_chart(df_precos, color=["#FF6B6B", "#4ECDC4"])
            else:
                st.info("Sem dados de preço para exibir.")

        st.markdown("---")
        st.markdown("#### ⚖️ Volume Comprado × Vendido (kg)")
        df_vol = df_mat[['material', 'peso_comprado', 'peso_vendido']].set_index('material')
        st.bar_chart(df_vol, color=["#FF6B6B", "#4ECDC4"])


# ──────────────────────────────────────────────────────────────────────────────
# TAB 4 — POR PARCEIRO
# ──────────────────────────────────────────────────────────────────────────────

with tab4:
    partner_data = get_partner_analysis(start_date, end_date)

    if not partner_data:
        st.info("📭 Sem movimentação de parceiros no período.")
    else:
        df_par = pd.DataFrame(partner_data)

        df_forn = df_par[df_par['peso_fornecido'] > 0].sort_values('valor_pago', ascending=False)
        df_cli = df_par[df_par['peso_vendido'] > 0].sort_values('valor_recebido', ascending=False)

        col_forn, col_cli = st.columns(2)

        # ---- FORNECEDORES ----
        with col_forn:
            st.markdown("#### 📥 Top Fornecedores")
            st.caption("Quem mais entregou material no período")

            if df_forn.empty:
                st.info("Sem fornecedores com movimentação no período.")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Fornecedores ativos", len(df_forn))
                with c2:
                    st.metric("Total pago", f"R$ {df_forn['valor_pago'].sum():,.2f}")

                df_forn_disp = df_forn[[
                    'parceiro', 'qtd_entradas', 'peso_fornecido',
                    'valor_pago', 'ultima_transacao'
                ]].copy()
                df_forn_disp['peso_fornecido'] = df_forn_disp['peso_fornecido'].apply(
                    lambda x: f"{x:,.1f} kg"
                )
                df_forn_disp['valor_pago'] = df_forn_disp['valor_pago'].apply(
                    lambda x: f"R$ {x:,.2f}"
                )
                df_forn_disp.columns = [
                    'Fornecedor', 'Entradas', 'Peso Fornecido', 'Valor Pago', 'Última Visita'
                ]
                st.dataframe(df_forn_disp, use_container_width=True, hide_index=True)

                if len(df_forn) > 1:
                    st.markdown("**Ranking por valor pago (top 10)**")
                    df_top_forn = (
                        df_forn.nlargest(10, 'valor_pago')[['parceiro', 'valor_pago']]
                        .set_index('parceiro')
                    )
                    st.bar_chart(df_top_forn, color="#FF6B6B")

        # ---- CLIENTES ----
        with col_cli:
            st.markdown("#### 📤 Top Clientes")
            st.caption("Quem mais comprou material no período")

            if df_cli.empty:
                st.info("Sem clientes com movimentação no período.")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Clientes ativos", len(df_cli))
                with c2:
                    st.metric("Total recebido", f"R$ {df_cli['valor_recebido'].sum():,.2f}")

                df_cli_disp = df_cli[[
                    'parceiro', 'qtd_saidas', 'peso_vendido',
                    'valor_recebido', 'ultima_transacao'
                ]].copy()
                df_cli_disp['peso_vendido'] = df_cli_disp['peso_vendido'].apply(
                    lambda x: f"{x:,.1f} kg"
                )
                df_cli_disp['valor_recebido'] = df_cli_disp['valor_recebido'].apply(
                    lambda x: f"R$ {x:,.2f}"
                )
                df_cli_disp.columns = [
                    'Cliente', 'Vendas', 'Peso Vendido', 'Valor Recebido', 'Última Compra'
                ]
                st.dataframe(df_cli_disp, use_container_width=True, hide_index=True)

                if len(df_cli) > 1:
                    st.markdown("**Ranking por valor recebido (top 10)**")
                    df_top_cli = (
                        df_cli.nlargest(10, 'valor_recebido')[['parceiro', 'valor_recebido']]
                        .set_index('parceiro')
                    )
                    st.bar_chart(df_top_cli, color="#4ECDC4")


# ──────────────────────────────────────────────────────────────────────────────
# TAB 5 — TRANSAÇÕES
# ──────────────────────────────────────────────────────────────────────────────

with tab5:
    transactions = get_transactions(
        start_date=start_date,
        end_date=end_date,
        material_id=mat_id,
        partner_id=par_id
    )

    if not transactions:
        st.info("📭 Nenhuma transação encontrada com os filtros selecionados.")
    else:
        df_all = pd.DataFrame(transactions)

        # Stats rápidos
        col_s1, col_s2 = st.columns(2)
        col_s3, col_s4 = st.columns(2)
        with col_s1:
            st.metric("Total de transações", len(df_all))
        with col_s2:
            n_entradas = len(df_all[df_all['type'] == 'entrada'])
            st.metric("Entradas", n_entradas)
        with col_s3:
            n_saidas = len(df_all[df_all['type'] == 'saida'])
            st.metric("Saídas", n_saidas)
        with col_s4:
            st.metric("Valor total movimentado", f"R$ {df_all['total_value'].sum():,.2f}")

        st.markdown("---")

        # Filtro rápido por tipo
        tipo_filtro = st.radio(
            "Filtrar por tipo", ["Todas", "Entradas", "Saídas"], horizontal=True
        )
        df_view = df_all.copy()
        if tipo_filtro == "Entradas":
            df_view = df_view[df_view['type'] == 'entrada']
        elif tipo_filtro == "Saídas":
            df_view = df_view[df_view['type'] == 'saida']

        df_display = df_view[[
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
            'Data', 'Tipo', 'Material', 'Parceiro',
            'Peso', 'Preço/kg', 'Valor Total', 'Observações'
        ]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Exportação
        st.markdown("---")
        st.markdown("#### 📥 Exportar")
        col_e1, col_e2 = st.columns(2)

        with col_e1:
            csv_data = df_all.to_csv(index=False, encoding='utf-8-sig', sep=';', decimal=',')
            st.download_button(
                label="⬇️ Exportar Transações (CSV)",
                data=csv_data,
                file_name=f"transacoes_{start_date}_{end_date}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col_e2:
            st.info(
                f"💡 {len(df_all)} transações no período. "
                f"Compatível com Excel e Google Sheets."
            )
