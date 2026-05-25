import streamlit as st
import pandas as pd
import math
import smtplib
from email.message import EmailMessage
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gestão de Estoque", layout="wide")

# --- GERENCIAMENTO DE ESTADO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'alerta_enviado' not in st.session_state:
    st.session_state.alerta_enviado = False

# --- FUNÇÕES ---
@st.cache_data
def carregar_e_treinar():
    df_vendas = pd.read_csv('vendas_historico.csv')
    df_estoque = pd.read_csv('estoque.csv')
    todos_produtos = pd.concat([df_vendas['Produto'], df_estoque['Produto']]).unique()
    le = LabelEncoder().fit(todos_produtos)
    df_vendas['Produto_ID'] = le.transform(df_vendas['Produto'])
    modelo = LinearRegression().fit(df_vendas[['Produto_ID']], df_vendas['Quantidade_Vendida'])
    return modelo, le, df_estoque

def enviar_alerta_email(lista_criticos, modelo, le):
    msg = EmailMessage()
    msg['Subject'] = '⚠️ ALERTA AUTOMÁTICO: Reposição Necessária'
    msg['From'] = 'seu_email@gmail.com'
    msg['To'] = 'seu_email@gmail.com'
    
    df_rel = lista_criticos.copy()
    df_rel['Demanda_Prevista'] = df_rel['Produto'].apply(
        lambda p: math.ceil(modelo.predict([[le.transform([p])[0]]])[0])
    )
    df_rel['Sugestao_Reposicao'] = df_rel['Demanda_Prevista'] + 2
    
    html = f"""<html><body><h2>Alerta: Estoque Crítico</h2>
    <table border="1"><tr><th>Produto</th><th>Estoque</th><th>Demanda</th><th>Sugestão</th></tr>
    {df_rel.apply(lambda row: f"<tr><td>{row['Produto']}</td><td>{row['Estoque_Atual']}</td><td>{row['Demanda_Prevista']}</td><td>{row['Sugestao_Reposicao']}</td></tr>", axis=1).sum()}
    </table></body></html>"""
    msg.add_alternative(html, subtype='html')
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login('seu_email@gmail.com', 'SUA_SENHA_DE_APP')
            smtp.send_message(msg)
        return True
    except: return False

# --- LÓGICA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo")
    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if user == "admin" and pwd == "admin123":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Credenciais inválidas")
    st.stop() # Bloqueia o carregamento do dashboard se não estiver logado

# --- DASHBOARD ---
modelo, le, df_estoque = carregar_e_treinar()

if st.sidebar.button("🚪 Sair"):
    st.session_state.logado = False
    st.session_state.alerta_enviado = False
    st.rerun()

# Monitoramento automático
criticos = df_estoque[df_estoque['Estoque_Atual'] < 5]
if not criticos.empty and not st.session_state.alerta_enviado:
    if enviar_alerta_email(criticos, modelo, le):
        st.toast("⚠️ Alerta enviado ao fornecedor!")
        st.session_state.alerta_enviado = True

st.title("📦 Gestão de Estoque")

# CRUD e Interface
with st.expander("➕ Adicionar Novo Produto"):
    col_a, col_b, col_c = st.columns(3)
    novo_prod = col_a.text_input("Nome")
    qtd_ini = col_b.number_input("Qtd", min_value=0)
    if col_c.button("Cadastrar"):
        df_estoque = pd.concat([df_estoque, pd.DataFrame({'Produto': [novo_prod], 'Estoque_Atual': [qtd_ini]})])
        df_estoque.to_csv('estoque.csv', index=False); st.cache_data.clear(); st.rerun()

st.subheader("🛠️ Ajuste")
prod_edit = st.selectbox("Produto", df_estoque['Produto'])
qtd_ajuste = st.number_input("Qtd ajuste", min_value=1)
c1, c2 = st.columns(2)
if c1.button("➕ Adicionar"):
    idx = df_estoque[df_estoque['Produto'] == prod_edit].index[0]
    df_estoque.at[idx, 'Estoque_Atual'] += qtd_ajuste
    df_estoque.to_csv('estoque.csv', index=False); st.cache_data.clear(); st.rerun()
if c2.button("➖ Remover"):
    idx = df_estoque[df_estoque['Produto'] == prod_edit].index[0]
    df_estoque.at[idx, 'Estoque_Atual'] -= qtd_ajuste
    df_estoque.to_csv('estoque.csv', index=False); st.cache_data.clear(); st.rerun()

st.dataframe(df_estoque, use_container_width=True)