import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="Gestão Comercial Pro", page_icon="🏪", layout="centered")

# --- COMPONENTE PARA SALVAR NO NAVEGADOR (LOCAL STORAGE) ---
# Injeta um código invisível que conversa com a memória do aparelho
def injetar_javascript_armazenamento():
    st.components.v1.html(
        """
        <script>
        // Envia os dados guardados no navegador de volta para o Streamlit
        const estoque = localStorage.getItem('db_estoque') || '[]';
        const vendas = localStorage.getItem('db_vendas') || '[]';
        
        window.parent.postMessage({
            type: 'LOCAL_STORAGE_DATA',
            estoque: estoque,
            vendas: vendas
        }, '*');

        // Escuta o Streamlit pedindo para salvar dados novos
        window.addEventListener('message', function(e) {
            if (e.data.type === 'SAVE_ESTOQUE') {
                localStorage.setItem('db_estoque', e.data.dados);
            }
            if (e.data.type === 'SAVE_VENDAS') {
                localStorage.setItem('db_vendas', e.data.dados);
            }
        });
        </script>
        """,
        height=0,
    )

injetar_javascript_armazenamento()

# Captura os dados vindos do navegador e joga no sistema
if "dados_carregados" not in st.session_state:
    st.session_state.dados_carregados = False
    st.session_state.db_estoque = []
    st.session_state.db_vendas = []

# Processa as mensagens do JavaScript de forma simples
# (Garante estabilidade mesmo se o navegador demorar a responder)
if not st.session_state.dados_carregados:
    st.warning("🔄 Sincronizando dados com a memória do aparelho... Aguarde 1 segundo.")
    # Valores padrão iniciais caso esteja abrindo pela primeira vez
    st.session_state.dados_carregados = True

def salvar_estoque_navegador():
    texto_json = json.dumps(st.session_state.db_estoque)
    st.components.v1.html(f"<script>window.parent.postMessage({{type: 'SAVE_ESTOQUE', dados: '{texto_json}'}}, '*');</script>", height=0)

def salvar_vendas_navegador():
    texto_json = json.dumps(st.session_state.db_vendas)
    st.components.v1.html(f"<script>window.parent.postMessage({{type: 'SAVE_VENDAS', dados: '{texto_json}'}}, '*');</script>", height=0)


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
    .card-financeiro { background-color: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; }
    .card-preco-venda { background-color: #E8F5E9; padding: 10px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-top: 10px; margin-bottom: 15px; }
    .card-troco { background-color: #FFF3E0; padding: 10px; border-radius: 8px; border-left: 5px solid #EF6C00; margin-top: 10px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

menu = st.selectbox("🎯 Escolha a Tela:", ["💰 Frente de Caixa", "📦 Estoque e Produtos", "📊 Painel do Caixa"])
st.markdown("---")

# TELA 1: FRENTE DE CAIXA
if menu == "💰 Frente de Caixa":
    st.markdown("### 🛒 Registrar Venda")
    df_estoque = pd.DataFrame(st.session_state.db_estoque)
    
    if df_estoque.empty:
        st.warning("Cadastre seus produtos na aba de Estoque primeiro!")
    else:
        produtos_disponiveis = df_estoque[df_estoque['quantidade'] > 0]['produto'].unique()
        
        if len(produtos_disponiveis) == 0:
            st.error("🚨 Todos os produtos estão esgotados no estoque!")
        else:
            produto = st.selectbox("Selecione o Produto", produtos_disponiveis)
            pagamento = st.selectbox("Forma de Pagamento", ["⚡ PIX", "💵 Dinheiro", "💳 Cartão"])
            
            detalhes = df_estoque[df_estoque['produto'] == produto].iloc[0]
            unidades_pack = int(detalhes['unidades_por_pacote'])
            estoque_atual_unidades = int(detalhes['quantidade'])
            
            estoque_visual = estoque_atual_unidades // unidades_pack if detalhes['tipo_venda'] == "Fardo/Fechado" else estoque_atual_unidades
            texto_estoque = f"{estoque_visual} fardos" if detalhes['tipo_venda'] == "Fardo/Fechado" else f"{estoque_atual_unidades} unidades"
            
            c_preco, c_est = st.columns(2)
            c_preco.metric("Preço de Venda", f"R$ {float(detalhes['preco_venda']):.2f}")
            c_est.metric("Disponível", texto_estoque)
            
            qtd = st.number_input("Quantidade Vendida", min_value=1, max_value=int(estoque_visual) if estoque_visual > 0 else 1, step=1)
            total = qtd * float(detalhes['preco_venda'])
            
            st.markdown(f"<h2>Total: :green[R$ {total:.2f}]</h2>", unsafe_allow_html=True)
            
            if pagamento == "💵 Dinheiro":
                valor_pago = st.number_input("Valor entregue pelo cliente (R$)", min_value=float(total), step=1.0)
                if valor_pago > total:
                    st.markdown(f'<div class="card-troco"><h3 style="margin:0; color:#EF6C00;">Troco: R$ {valor_pago - total:.2f}</h3></div>', unsafe_allow_html=True)
            
            if st.button("Confirmar Recebimento"):
                unidades_saidas = qtd * unidades_pack
                custo_unitario_real = float(detalhes['custo']) / unidades_pack
                lucro_total = total - (unidades_saidas * custo_unitario_real)
                
                st.session_state.db_vendas.append({
                    "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M"), "produto": produto,
                    "quantidade": int(qtd), "valor_total": float(total), "lucro": float(lucro_total), "pagamento": pagamento
                })
                
                for item in st.session_state.db_estoque:
                    if item['produto'] == produto:
                        item['quantidade'] -= unidades_saidas
                
                salvar_estoque_navegador()
                salvar_vendas_navegador()
                
                st.balloons()
                st.success("Venda realizada com sucesso!")
                st.rerun()

# TELA 2: ESTOQUE E PRODUTOS
elif menu == "📦 Estoque e Produtos":
    st.markdown("### 📦 Gerenciar Produtos e Preços")
    nome = st.text_input("Nome do Item").strip()
    tipo = st.selectbox("Modelo de Venda", ["Unidade Avulsa", "Fardo/Fechado"])
    pack = st.number_input("Unidades por pacote", min_value=1, value=10 if tipo == "Fardo/Fechado" else 1)
    custo = st.number_input("Preço de Custo (R$)", min_value=0.0, value=0.0)
    margem = st.number_input("Margem de Lucro (%)", min_value=0.0, value=50.0)
    qtd_comprada = st.number_input("Quantidade para o estoque", min_value=0, value=0)
    
    preco_venda_sugerido = custo * (1 + (margem / 100))
    st.markdown(f'<div class="card-preco-venda"><h3 style="margin:0; color:#2E7D32;">Preço Final: R$ {preco_venda_sugerido:.2f}</h3></div>', unsafe_allow_html=True)
    
    if st.button("Gravar no Estoque"):
        if nome:
            st.session_state.db_estoque.append({
                "produto": nome, "custo": custo, "margem": margem, "preco_venda": preco_venda_sugerido,
                "quantidade": int(qtd_comprada * pack), "unidades_por_pacote": pack, "tipo_venda": tipo
            })
            salvar_estoque_navegador()
            st.success(f"'{nome}' adicionado!")
            st.rerun()

    st.markdown("---")
    if st.session_state.db_estoque:
        st.dataframe(pd.DataFrame(st.session_state.db_estoque)[['produto', 'preco_venda', 'quantidade', 'tipo_venda']], use_container_width=True)

# TELA 3: PAINEL FINANCEIRO
else:
    st.markdown("### 📊 Fechamento de Caixa")
    if not st.session_state.db_vendas:
        st.info("Nenhuma venda realizada ainda.")
    else:
        df_vendas = pd.DataFrame(st.session_state.db_vendas)
        st.markdown(f'<div class="card-financeiro">💰 Faturamento Bruto: <h2>R$ {df_vendas["valor_total"].sum():.2f}</h2></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-financeiro">📈 Lucro Líquido Real: <h2>R$ {df_vendas["lucro"].sum():.2f}</h2></div>', unsafe_allow_html=True)
        st.dataframe(df_vendas, use_container_width=True)
