import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gestão Comercial Pro", page_icon="🏪", layout="centered")

# Link definitivo da sua nova planilha
LINK_PLANILHA = "https://docs.google.com/spreadsheets/d/1UY1Z2gSViOHBYbJXNbXMH8_ZbHtR_NPMgIZxlUMoy1g/edit?v=2"

# --- DESIGN PERSONALIZADO (CSS) ---
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .stButton>button { 
        width: 100%; border-radius: 12px; height: 3em; 
        background-color: #2E7D32; color: white; font-weight: bold; border: none;
    }
    .stButton>button:hover { background-color: #1B5E20; color: white; }
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; color: #1E88E5; }
    .card-financeiro {
        background-color: white; padding: 15px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px;
    }
    .card-preco-venda {
        background-color: #E8F5E9; padding: 10px; border-radius: 8px;
        border-left: 5px solid #2E7D32; margin-top: 10px; margin-bottom: 15px;
    }
    .card-troco {
        background-color: #FFF3E0; padding: 10px; border-radius: 8px;
        border-left: 5px solid #EF6C00; margin-top: 10px; margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(aba):
    return conn.read(spreadsheet=LINK_PLANILHA, worksheet=aba, ttl="0s")

menu = st.selectbox("🎯 Escolha a Tela:", ["💰 Frente de Caixa", "📦 Estoque e Produtos", "📊 Painel do Caixa"])
st.markdown("---")

# -----------------------------------------------------------------------------------------
# TELA 1: FRENTE DE CAIXA
# -----------------------------------------------------------------------------------------
if menu == "💰 Frente de Caixa":
    st.markdown("### 🛒 Registrar Venda")
    
    try:
        df_estoque = carregar_dados("estoque")
    except:
        df_estoque = pd.DataFrame()
        
    if df_estoque.empty or 'produto' not in df_estoque.columns:
        st.warning("Cadastre seus produtos na aba de Estoque primeiro!")
    else:
        df_estoque['quantidade'] = pd.to_numeric(df_estoque['quantidade'], errors='coerce').fillna(0).astype(int)
        df_estoque['preco_venda'] = pd.to_numeric(df_estoque['preco_venda'], errors='coerce').fillna(0.0)
        df_estoque['unidades_por_pacote'] = pd.to_numeric(df_estoque['unidades_por_pacote'], errors='coerce').fillna(1).astype(int)
        
        produtos_disponiveis = df_estoque[df_estoque['quantidade'] >= df_estoque['unidades_por_pacote']]['produto'].unique()
        
        if len(produtos_disponiveis) == 0:
            st.error("🚨 Todos os produtos estão esgotados no estoque!")
        else:
            produto = st.selectbox("Selecione o Produto", produtos_disponiveis)
            pagamento = st.selectbox("Forma de Pagamento", ["⚡ PIX", "💵 Dinheiro", "💳 Cartão"])
            
            detalhes = df_estoque[df_estoque['produto'] == produto].iloc[0]
            unidades_pack = int(detalhes['unidades_por_pacote'])
            estoque_atual_unidades = int(detalhes['quantidade'])
            
            if detalhes['tipo_venda'] == "Fardo/Fechado":
                estoque_visual = estoque_atual_unidades // unidades_pack
                texto_estoque = f"{estoque_visual} fardos"
                max_venda = estoque_visual
            else:
                texto_estoque = f"{estoque_atual_unidades} unidades"
                max_venda = estoque_atual_unidades
            
            c_preco, c_est = st.columns(2)
            c_preco.metric("Preço de Venda", f"R$ {detalhes['preco_venda']:.2f}")
            c_est.metric("Disponível", texto_estoque)
            
            qtd = st.number_input("Quantidade Vendida", min_value=1, max_value=int(max_venda), step=1)
            total = qtd * detalhes['preco_venda']
            
            st.markdown(f"<h2>Total: :green[R$ {total:.2f}]</h2>", unsafe_allow_html=True)
            
            if pagamento == "💵 Dinheiro":
                valor_pago = st.number_input("Valor entregue pelo cliente (R$)", min_value=float(total), step=1.0)
                if valor_pago > total:
                    troco = valor_pago - total
                    st.markdown(f"""
                    <div class="card-troco">
                        <p style='margin:0; color:#E65100; font-size:14px;'>💵 Troco a devolver:</p>
                        <h3 style='margin:0; color:#EF6C00;'>R$ {troco:.2f}</h3>
                    </div>
                    """, unsafe_allow_html=True)
            
            if st.button("Confirmar Recebimento"):
                unidades_saidas = qtd * unidades_pack
                
                try:
                    df_vendas = carregar_dados("vendas")
                except:
                    df_vendas = pd.DataFrame()
                    
                custo_unitario_real = float(detalhes['custo']) / unidades_pack
                lucro_total = total - (unidades_saidas * custo_unitario_real)
                
                nova_venda = pd.DataFrame([{
                    "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "produto": produto,
                    "quantidade": int(qtd),
                    "valor_total": float(total),
                    "lucro": float(lucro_total),
                    "pagamento": pagamento
                }])
                
                df_vendas_atualizado = pd.concat([df_vendas, nova_venda], ignore_index=True)
                conn.update(spreadsheet=LINK_PLANILHA, worksheet="vendas", data=df_vendas_atualizado)
                
                df_estoque.loc[df_estoque['produto'] == produto, 'quantidade'] -= unidades_saidas
                conn.update(spreadsheet=LINK_PLANILHA, worksheet="estoque", data=df_estoque)
                
                st.balloons()
                st.success("Venda salva com sucesso!")
                st.rerun()

# -----------------------------------------------------------------------------------------
# TELA 2: ESTOQUE E PRODUTOS
# -----------------------------------------------------------------------------------------
elif menu == "📦 Estoque e Produtos":
    st.markdown("### 📦 Gerenciar Produtos e Preços")
    
    try:
        df_estoque = carregar_dados("estoque")
    except:
        df_estoque = pd.DataFrame(columns=['produto', 'custo', 'margem', 'preco_venda', 'quantidade', 'unidades_por_pacote', 'tipo_venda'])
        
    nome = st.text_input("Nome do Item (Ex: Cerveja Skol Lata ou Cerveja Skol Fardo)").strip()
    tipo = st.selectbox("Como esse item será vendido no balcão?", ["Unidade Avulsa", "Fardo/Fechado"])
    
    if tipo == "Fardo/Fechado":
        pack = st.number_input("Quantas unidades vêm dentro desse fardo?", min_value=2, value=10, step=1)
    else:
        pack = 1
        
    custo = st.number_input("Preço de Custo total pago pelo item/fardo (R$)", min_value=0.0, step=0.10, value=0.0)
    margem = st.number_input("Margem de Lucro Desejada (%)", min_value=0.0, value=50.0, step=5.0)
    qtd_comprada = st.number_input(f"Quantidade de {'Fardos' if tipo == 'Fardo/Fechado' else 'Unidades'} para o estoque", min_value=0, step=1, value=0)
    
    preco_venda_sugerido = custo * (1 + (margem / 100))
    st.markdown(f"""
    <div class="card-preco-venda">
        <p style='margin:0; color:#1B5E20; font-size:14px;'>💰 Preço Final de Venda Cadastrado:</p>
        <h3 style='margin:0; color:#2E7D32;'>R$ {preco_venda_sugerido:.2f} {'por Fardo' if tipo == 'Fardo/Fechado' else 'por Unidade'}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Gravar no Estoque"):
        if nome:
            total_unidades_estoque = int(qtd_comprada * pack)
            
            novo_p = pd.DataFrame([{
                "produto": nome, "custo": custo, "margem": margem, 
                "preco_venda": preco_venda_sugerido, "quantidade": total_unidades_estoque,
                "unidades_por_pacote": pack, "tipo_venda": tipo
            }])
            
            if not df_estoque.empty and nome in df_estoque['produto'].values:
                df_estoque.loc[df_estoque['produto'] == nome] = [nome, custo, margem, preco_venda_sugerido, total_unidades_estoque, pack, tipo]
            else:
                df_estoque = pd.concat([df_estoque, novo_p], ignore_index=True)
                
            conn.update(spreadsheet=LINK_PLANILHA, worksheet="estoque", data=df_estoque)
            st.success(f"'{nome}' salvo com sucesso!")
            st.rerun()
        else:
            st.error("Por favor, digite o nome do produto.")

    st.markdown("---")
    st.markdown("#### 📋 Situação Atual do Estoque")
    if not df_estoque.empty:
        st.dataframe(df_estoque[['produto', 'preco_venda', 'quantidade', 'tipo_venda']].rename(columns={'produto': 'Produto', 'preco_venda': 'Preço Balcão', 'quantidade': 'Estoque (Total Unidades)', 'tipo_venda': 'Modelo'}), use_container_width=True)

# -----------------------------------------------------------------------------------------
# TELA 3: PAINEL FINANCEIRO
# -----------------------------------------------------------------------------------------
else:
    st.markdown("### 📊 Fechamento de Caixa e Lucros")
    try:
        df_vendas = carregar_dados("vendas")
    except:
        df_vendas = pd.DataFrame()
        
    if df_vendas.empty:
        st.info("Nenhuma venda computada ainda.")
    else:
        tot_faturamento = df_vendas['valor_total'].sum()
        tot_lucro = df_vendas['lucro'].sum()
        
        st.markdown(f"""
        <div class="card-financeiro">
            <p style='margin:0; color:#666;'>💰 Faturamento Bruto</p>
            <h2 style='margin:0; color:#2E7D32;'>R$ {tot_faturamento:.2f}</h2>
        </div>
        <div class="card-financeiro">
            <p style='margin:0; color:#666;'>📈 Lucro Líquido Real (Dinheiro no Bolso)</p>
            <h2 style='margin:0; color:#1565C0;'>R$ {tot_lucro:.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### 💸 Entradas por Tipo de Pagamento")
        resumo_pagos = df_vendas.groupby("pagamento")["valor_total"].sum().reset_index()
        st.dataframe(resumo_pagos.rename(columns={'pagamento': 'Forma', 'valor_total': 'Total (R$)'}), use_container_width=True)
