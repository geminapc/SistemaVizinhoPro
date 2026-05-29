import streamlit as st
import pandas as pd
from datetime import datetime
import json
import requests
import base64

st.set_page_config(page_title="Gestão Comercial Pro", page_icon="🏪", layout="centered")

# --- CONFIGURAÇÃO AUTOMÁTICA DO GITHUB ---
# O sistema vai usar o próprio GitHub para salvar os dados com segurança
TOKEN = "ghp_sistemavizinhopro_definitivo_token_placeholder" # Não precisa mexer aqui se usar os Secrets
REPO = "SistemaVizinhoPro"

# Tentativa de carregar credenciais seguras do Streamlit, se houver
try:
    GITHUB_TOKEN = st.secrets["github"]["token"]
    GITHUB_USER = st.secrets["github"]["username"]
except:
    # Fallback para o modo local de demonstração caso os secrets não estejam prontos
    GITHUB_TOKEN = ""
    GITHUB_USER = ""

URL_ESTOQUE = f"https://api.github.com/repos/{GITHUB_USER}/{REPO}/contents/estoque.json" if GITHUB_USER else ""
URL_VENDAS = f"https://api.github.com/repos/{GITHUB_USER}/{REPO}/contents/vendas.json" if GITHUB_USER else ""

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

def carregar_dados_github(url_alvo):
    if not url_alvo or not GITHUB_TOKEN:
        return []
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url_alvo, headers=headers)
    if r.status_code == 200:
        conteudo = json.loads(base64.b64decode(r.json()["content"]).decode())
        return conteudo
    return []

def salvar_dados_github(url_alvo, dados):
    if not url_alvo or not GITHUB_TOKEN:
        return
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url_alvo, headers=headers)
    sha = r.json()["sha"] if r.status_code == 200 else None
    
    conteudo_bytes = json.dumps(dados, indent=4).encode()
    conteudo_b64 = base64.b64encode(conteudo_bytes).decode()
    
    payload = {"message": "Atualizando dados do sistema", "content": conteudo_b64}
    if sha:
        payload["sha"] = sha
        
    requests.put(url_alvo, headers=headers, json=payload)

# Inicializando estados
if "db_estoque" not in st.session_state:
    st.session_state.db_estoque = carregar_dados_github(URL_ESTOQUE) if GITHUB_TOKEN else []
if "db_vendas" not in st.session_state:
    st.session_state.db_vendas = carregar_dados_github(URL_VENDAS) if GITHUB_TOKEN else []

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
                
                if GITHUB_TOKEN:
                    salvar_dados_github(URL_ESTOQUE, st.session_state.db_estoque)
                    salvar_dados_github(URL_VENDAS, st.session_state.db_vendas)
                
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
            if GITHUB_TOKEN:
                salvar_dados_github(URL_ESTOQUE, st.session_state.db_estoque)
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
