import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text  # Garante que os comandos SQL funcionem perfeitamente

st.set_page_config(page_title="Gestão Comercial Pro", page_icon="🏪", layout="wide")

# --- CONEXÃO COM O POSTGRESQL (SUPABASE) ---
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error(f"Erro ao inicializar conexão com o banco: {e}")

# Inicializa o carrinho na sessão se não existir
if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

# --- DESIGN PERSONALIZADO (CSS) ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .total-card { background-color: #e8f5e9; padding: 20px; border-radius: 10px; border-left: 6px solid #2e7d32; text-align: center; }
    .card-financeiro { background-color: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- MENU LATERAL INTERATIVO ---
with st.sidebar:
    st.markdown("## 🏪 **Menu Principal**")
    tela = st.radio("Ir para:", ["💰 Frente de Caixa (Balcão)", "📦 Controle de Estoque", "📊 Painel Financeiro"])
    st.markdown("---")
    st.caption("Conectado ao Supabase PostgreSQL")

# -----------------------------------------------------------------------------------------
# TELA 1: FRENTE DE CAIXA (CARRINHO MULTI-ITENS)
# -----------------------------------------------------------------------------------------
if tela == "💰 Frente de Caixa (Balcão)":
    st.title("🛒 Frente de Caixa")
    
    # Busca estoque atualizado do banco de forma segura
    try:
        df_est = conn.query("SELECT * FROM estoque ORDER BY produto;", ttl="0s")
    except Exception as e:
        st.error(f"Não foi possível ler o banco de dados: {e}")
        df_est = pd.DataFrame()
        
    if df_est.empty:
        st.warning("Estoque zerado ou tabela não encontrada! Cadastre produtos na aba de Estoque.")
    else:
        col_venda, col_carrinho = st.columns([1.2, 1])
        
        with col_venda:
            st.markdown("### 1. Adicionar Produto")
            produtos_disponiveis = df_est[df_est['quantidade'] > 0]['produto'].tolist()
            
            if not produtos_disponiveis:
                st.error("🚨 Todos os produtos estão esgotados no estoque!")
            else:
                prod_selecionado = st.selectbox("Selecione o Produto", produtos_disponiveis)
                detalhes = df_est[df_est['produto'] == prod_selecionado].iloc[0]
                
                unidades_pack = int(detalhes['unidades_por_pacote'])
                qtd_maxima = int(detalhes['quantidade'] // unidades_pack) if detalhes['tipo_venda'] == "Fardo/Fechado" else int(detalhes['quantidade'])
                
                c1, c2 = st.columns(2)
                c1.metric("Preço Unitário", f"R$ {float(detalhes['preco_venda']):.2f}")
                c2.metric("Disponível", f"{qtd_maxima} fardos" if detalhes['tipo_venda'] == "Fardo/Fechado" else f"{qtd_maxima} un")
                
                qtd_venda = st.number_input("Quantidade desejada", min_value=1, max_value=max(1, qtd_maxima), value=1, step=1)
                
                if st.button("➕ Adicionar ao Pedido"):
                    ja_no_carrinho = False
                    for item in st.session_state.carrinho:
                        if item['produto'] == prod_selecionado:
                            if item['quantidade'] + qtd_venda <= qtd_maxima:
                                item['quantidade'] += qtd_venda
                                item['subtotal'] = item['quantidade'] * float(detalhes['preco_venda'])
                                item['unidades_totais'] = item['quantidade'] * unidades_pack
                                if detalhes['tipo_venda'] == "Fardo/Fechado":
                                    item['custo_total'] = float(detalhes['custo']) * item['quantidade']
                                else:
                                    item['custo_total'] = (float(detalhes['custo']) / unidades_pack) * item['unidades_totais']
                                ja_no_carrinho = True
                            else:
                                st.error("Quantidade total excede o estoque disponível!")
                                ja_no_carrinho = True
                    
                    if not ja_no_carrinho:
                        if detalhes['tipo_venda'] == "Fardo/Fechado":
                            custo_calculado = float(detalhes['custo']) * qtd_venda
                        else:
                            custo_calculado = (float(detalhes['custo']) / unidades_pack) * (qtd_venda * unidades_pack)

                        st.session_state.carrinho.append({
                            "produto": prod_selecionado,
                            "quantidade": qtd_venda,
                            "preco_venda": float(detalhes['preco_venda']),
                            "custo_total": custo_calculado,
                            "unidades_totais": qtd_venda * unidades_pack,
                            "subtotal": qtd_venda * float(detalhes['preco_venda'])
                        })
                    st.rerun()

        with col_carrinho:
            st.markdown("### 📋 Carrinho de Compras")
            if not st.session_state.carrinho:
                st.info("O carrinho está vazio. Adicione itens.")
            else:
                df_cart = pd.DataFrame(st.session_state.carrinho)
                st.dataframe(df_cart[['produto', 'quantidade', 'subtotal']].rename(columns={
                    'produto': 'Item', 'quantidade': 'Qtd', 'subtotal': 'Subtotal (R$)'
                }), use_container_width=True)
                
                total_geral = df_cart['subtotal'].sum()
                
                st.markdown(f"""
                    <div class="total-card">
                        <p style="margin:0; font-size: 15px; color: #1b5e20;">TOTAL DO PEDIDO</p>
                        <h2 style="margin:0; font-size: 32px; color: #2e7d32;">R$ {total_geral:.2f}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                
                forma_pagamento = st.selectbox("Forma de Pagamento", ["⚡ PIX", "💵 Dinheiro", "💳 Cartão"])
                
                if forma_pagamento == "💵 Dinheiro":
                    pago = st.number_input("Valor Entregue", min_value=float(total_geral), value=float(total_geral))
                    if pago > total_geral:
                        st.success(f"💵 Troco: **R$ {pago - total_geral:.2f}**")
                
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button("❌ Limpar Carrinho"):
                    st.session_state.carrinho = []
                    st.rerun()
                    
                if c_btn2.button("✅ Confirmar Venda"):
                    try:
                        with conn.session as session:
                            for item in st.session_state.carrinho:
                                session.execute(
                                    text("UPDATE estoque SET quantidade = quantidade - :unidades WHERE produto = :prod;"),
                                    {"unidades": item['unidades_totais'], "prod": item['produto']}
                                )
                                lucro_item = item['subtotal'] - item['custo_total']
                                session.execute(
                                    text("INSERT INTO vendas (data_hora, produto, quantidade, valor_total, lucro, pagamento) VALUES (:dt, :prod, :qtd, :val, :luc, :pag);"),
                                    {
                                        "dt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "prod": item['produto'], "qtd": item['quantidade'], 
                                        "val": item['subtotal'], "luc": lucro_item, "pag": forma_pagamento
                                    }
                                )
                            session.commit()
                        st.session_state.carrinho = []
                        st.balloons()
                        st.success("Venda registrada e integrada ao Supabase!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Falha ao salvar no banco: {err}")

# -----------------------------------------------------------------------------------------
# TELA 2: CONTROLE DE ESTOQUE (PRO)
# -----------------------------------------------------------------------------------------
elif tela == "📦 Controle de Estoque":
    st.title("📦 Controle de Estoque Profissional")

    try:
        df_estoque = conn.query(
            "SELECT * FROM estoque ORDER BY produto;",
            ttl="0s"
        )
    except Exception as e:
        st.error(f"Erro ao carregar estoque: {e}")
        df_estoque = pd.DataFrame()

    # ==========================
    # BUSCA
    # ==========================
    busca = st.text_input(
        "🔍 Buscar produto",
        placeholder="Digite o nome do produto..."
    )

    if busca and not df_estoque.empty:
        df_estoque = df_estoque[
            df_estoque["produto"].str.contains(busca, case=False, na=False)
        ]

    # ==========================
    # ALERTA DE ESTOQUE BAIXO
    # ==========================
    if not df_estoque.empty:
        produtos_baixos = df_estoque[df_estoque["quantidade"] <= 10]

        if not produtos_baixos.empty:
            st.warning(
                f"⚠️ Atenção: {len(produtos_baixos)} produto(s) com estoque baixo (10 unidades ou menos)."
            )

    # ==========================
    # LISTAGEM
    # ==========================
    st.subheader("📋 Estoque Atual")

    if not df_estoque.empty:
        df_exibicao = df_estoque[['produto', 'preco_venda', 'quantidade', 'tipo_venda']].rename(columns={
            'produto': 'Nome do Produto',
            'preco_venda': 'Preço de Venda (R$)',
            'quantidade': 'Qtd em Estoque',
            'tipo_venda': 'Modo de Venda'
        })
        st.dataframe(df_exibicao, use_container_width=True)
    else:
        st.info("Nenhum produto cadastrado.")

    st.divider()

    # ==========================
    # CADASTRO / EDIÇÃO
    # ==========================
    st.subheader("➕ Cadastrar ou Atualizar Produto")

    with st.form("cadastro_produto"):
        nome = st.text_input("Produto")
        tipo = st.selectbox("Tipo de Venda", ["Unidade Avulsa", "Fardo/Fechado"])
        pack = st.number_input("Unidades por pacote/fardo (Para avulso deixe 1)", min_value=1, value=1)
        custo = st.number_input("Preço de Custo Total (R$)", min_value=0.0, value=0.0, step=0.50)
        margem = st.number_input("Margem (%)", min_value=0.0, value=50.0, step=5.0)
        quantidade = st.number_input("Quantidade de fardos/unidades compradas", min_value=0, value=0)

        salvar = st.form_submit_button("💾 Salvar Produto")

        if salvar and nome:
            preco_venda = custo * (1 + margem / 100)
            unidades_totais = int(quantidade * pack)

            try:
                with conn.session as session:
                    session.execute(
                        text("""
                        INSERT INTO estoque (produto, custo, preco_venda, quantidade, unidades_por_pacote, tipo_venda)
                        VALUES (:produto, :custo, :preco, :qtd, :pack, :tipo)
                        ON CONFLICT (produto)
                        DO UPDATE SET
                            custo = :custo,
                            preco_venda = :preco,
                            quantidade = estoque.quantidade + :qtd,
                            unidades_por_pacote = :pack,
                            tipo_venda = :tipo
                        """),
                        {
                            "produto": nome, "custo": custo, "preco": preco_venda,
                            "qtd": unidades_totais, "pack": pack, "tipo": tipo
                        }
                    )
                    session.commit()
                st.success(f"Produto '{nome}' salvo com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

    st.divider()

    # ==========================
    # AJUSTE MANUAL DE ESTOQUE
    # ==========================
    if not df_estoque.empty:
        st.subheader("✏️ Ajustar Estoque Manualmente")

        produto_ajuste = st.selectbox(
            "Selecione o Produto para ajustar",
            df_estoque["produto"].tolist(),
            key="ajuste_produto"
        )

        qtd_atual = int(df_estoque[df_estoque["produto"] == produto_ajuste]["quantidade"].values[0])

        nova_qtd = st.number_input(
            "Nova Quantidade Exata em Estoque",
            min_value=0,
            value=qtd_atual
        )

        if st.button("Salvar Ajuste"):
            try:
                with conn.session as session:
                    session.execute(
                        text("UPDATE estoque SET quantidade = :qtd WHERE produto = :produto"),
                        {"qtd": nova_qtd, "produto": produto_ajuste}
                    )
                    session.commit()
                st.success("Estoque atualizado!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

    st.divider()

    # ==========================
    # EXCLUIR PRODUTO
    # ==========================
    if not df_estoque.empty:
        st.subheader("🗑️ Excluir Produto")

        produto_excluir = st.selectbox(
            "Produto para excluir",
            df_estoque["produto"].tolist(),
            key="excluir_produto"
        )

        if st.button("Excluir Produto Definitivamente"):
            try:
                with conn.session as session:
                    session.execute(
                        text("DELETE FROM estoque WHERE produto = :produto"),
                        {"produto": produto_excluir}
                    )
                    session.commit()
                st.success("Produto excluído!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

# -----------------------------------------------------------------------------------------
# TELA 3: PAINEL FINANCEIRO
# -----------------------------------------------------------------------------------------
else:
    st.title("📊 Painel Financeiro Realtime")
    
    try:
        df_vendas = conn.query("SELECT * FROM vendas ORDER BY id DESC;", ttl="0s")
    except:
        df_vendas = pd.DataFrame()
        
    if df_vendas.empty:
        st.info("Nenhuma venda realizada.")
    else:
        c1, c2 = st.columns(2)
        c1.metric("💰 Faturamento Bruto", f"R$ {df_vendas['valor_total'].sum():.2f}")
        c2.metric("📈 Lucro Líquido Real", f"R$ {df_vendas['lucro'].sum():.2f}")
        
        st.markdown("### 📋 Histórico Geral de Vendas")
        st.dataframe(df_vendas, use_container_width=True)
