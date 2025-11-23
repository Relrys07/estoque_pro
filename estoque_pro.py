import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import time
import altair as alt

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Gestão de Estoque Pro",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILIZAÇÃO CSS PROFISSIONAL ---
st.markdown("""
<style>
    /* Variáveis Globais */
    :root {
        --primary-color: #2563eb;
        --background-light: #f8fafc;
        --card-bg: #ffffff;
        --text-dark: #1e293b;
    }
    
    /* Card Style para Métricas */
    div[data-testid="metric-container"] {
        background-color: var(--card-bg);
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border-color: var(--primary-color);
    }

    /* Tabelas */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }

    /* Cabeçalhos */
    h1, h2, h3 {
        font-family: 'Segoe UI', sans-serif;
        color: var(--text-dark);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1e293b;
        color: white;
    }
    
    /* Botões */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- GERENCIAMENTO DE BANCO DE DADOS ---

class DatabaseManager:
    def __init__(self, db_name="estoque_pro.db"):
        self.db_name = db_name

    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def init_db(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            # Tabela de Usuários
            c.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    role TEXT DEFAULT 'user'
                )
            ''')
            # Tabela de Estoque (Adicionado: categoria, preço, estoque minimo)
            c.execute('''
                CREATE TABLE IF NOT EXISTS estoque (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE,
                    categoria TEXT,
                    quantidade INTEGER DEFAULT 0,
                    preco_unitario REAL DEFAULT 0.0,
                    estoque_minimo INTEGER DEFAULT 5,
                    responsavel TEXT,
                    data_entrada TEXT
                )
            ''')
            # Histórico
            c.execute('''
                CREATE TABLE IF NOT EXISTS historico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT,
                    quantidade INTEGER,
                    tipo TEXT,
                    valor_total_movimento REAL,
                    responsavel TEXT,
                    data_hora TEXT
                )
            ''')
            
            # Criar admin padrão se não existir
            try:
                admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
                c.execute("INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)", 
                          ('admin', admin_pass, 'admin'))
            except sqlite3.IntegrityError:
                pass # Admin já existe

# Instância Global do DB
db = DatabaseManager()
db.init_db()

# --- FUNÇÕES AUXILIARES ---

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def format_currency(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- LÓGICA DE NEGÓCIO ---

def autenticar(username, password):
    with db.get_connection() as conn:
        c = conn.cursor()
        pwd_hash = hash_password(password)
        c.execute("SELECT role FROM usuarios WHERE username = ? AND password_hash = ?", (username, pwd_hash))
        result = c.fetchone()
        return result[0] if result else None

def registrar_movimentacao(nome, qtd, tipo, responsavel, preco_unit=0):
    with db.get_connection() as conn:
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        valor_total = qtd * preco_unit
        
        # Atualizar ou Inserir Estoque
        if tipo == 'entrada':
            c.execute("SELECT quantidade, preco_unitario FROM estoque WHERE nome = ?", (nome,))
            row = c.fetchone()
            if row:
                nova_qtd = row[0] + qtd
                # Atualiza preço médio ou mantém o último (regra simples: atualiza para o novo)
                c.execute("""
                    UPDATE estoque SET quantidade = ?, responsavel = ?, data_entrada = ?, preco_unitario = ? 
                    WHERE nome = ?
                """, (nova_qtd, responsavel, now, preco_unit, nome))
            else:
                c.execute("""
                    INSERT INTO estoque (nome, quantidade, responsavel, data_entrada, preco_unitario, categoria) 
                    VALUES (?, ?, ?, ?, ?, 'Geral')
                """, (nome, qtd, responsavel, now, preco_unit))
        
        elif tipo == 'saida':
            c.execute("SELECT quantidade FROM estoque WHERE nome = ?", (nome,))
            row = c.fetchone()
            if not row or row[0] < qtd:
                return False, "Estoque insuficiente ou item inexistente."
            nova_qtd = row[0] - qtd
            c.execute("UPDATE estoque SET quantidade = ?, responsavel = ?, data_entrada = ? WHERE nome = ?", 
                      (nova_qtd, responsavel, now, nome))
        
        # Log Histórico
        c.execute("""
            INSERT INTO historico (nome, quantidade, tipo, valor_total_movimento, responsavel, data_hora) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nome, qtd, tipo, valor_total, responsavel, now))
        
        return True, "Sucesso"

def get_dataframe(query):
    with db.get_connection() as conn:
        return pd.read_sql_query(query, conn)

# --- INTERFACE DO USUÁRIO ---

def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h1>🔐 Acesso Restrito</h1></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Usuário", placeholder="admin")
            pwd = st.text_input("Senha", type="password", placeholder="admin123")
            submit = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit:
                role = autenticar(user, pwd)
                if role:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user
                    st.session_state['role'] = role
                    st.success("Login realizado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")

def dashboard_screen():
    st.title("📊 Dashboard Executivo")
    st.markdown("---")
    
    # Carregar dados
    df = get_dataframe("SELECT * FROM estoque")
    
    if df.empty:
        st.info("Nenhum dado disponível no estoque. Comece adicionando itens.")
        return

    # Cálculos de KPI
    df['valor_total'] = df['quantidade'] * df['preco_unitario']
    total_itens = df['quantidade'].sum()
    valor_patrimonio = df['valor_total'].sum()
    itens_baixo_estoque = df[df['quantidade'] <= df['estoque_minimo']].shape[0]
    categorias = df['categoria'].nunique()

    # Cards KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Itens em Estoque", f"{total_itens:,.0f}")
    c2.metric("Valor Patrimonial", format_currency(valor_patrimonio))
    c3.metric("Alertas de Reposição", itens_baixo_estoque, delta=-itens_baixo_estoque if itens_baixo_estoque > 0 else "OK", delta_color="inverse")
    c4.metric("Categorias", categorias)

    st.markdown("### 📈 Análise Visual")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.caption("Valor de Estoque por Categoria")
        chart_cat = alt.Chart(df).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("valor_total", stack=True),
            color=alt.Color("categoria", legend=None),
            tooltip=["categoria", "valor_total", "quantidade"]
        ).properties(height=300)
        st.altair_chart(chart_cat, use_container_width=True)

    with col_chart2:
        st.caption("Top 5 Itens com Maior Estoque")
        top_items = df.nlargest(5, 'quantidade')
        chart_bar = alt.Chart(top_items).mark_bar().encode(
            x='quantidade',
            y=alt.Y('nome', sort='-x'),
            color='categoria',
            tooltip=['nome', 'quantidade', 'preco_unitario']
        ).properties(height=300)
        st.altair_chart(chart_bar, use_container_width=True)

    # Tabela de Alerta
    if itens_baixo_estoque > 0:
        st.warning(f"⚠️ Atenção! {itens_baixo_estoque} itens estão abaixo do estoque mínimo.")
        st.dataframe(
            df[df['quantidade'] <= df['estoque_minimo']][['nome', 'quantidade', 'estoque_minimo', 'responsavel']],
            hide_index=True,
            use_container_width=True
        )

def operacoes_screen():
    st.title("📦 Controle de Movimentações")
    
    tab1, tab2 = st.tabs(["📥 Entrada (Compra/Devolução)", "📤 Saída (Venda/Uso)"])
    
    # Lista de produtos para autocomplete
    df_prods = get_dataframe("SELECT nome FROM estoque")
    lista_prods = df_prods['nome'].tolist() if not df_prods.empty else []

    with tab1:
        st.subheader("Registrar Nova Entrada")
        col1, col2 = st.columns(2)
        with col1:
            nome_in = st.text_input("Nome do Produto", placeholder="Digite ou selecione...") # Autocomplete seria ideal com st_searchbox externo, aqui usamos text simples
            # Dica: Se quiser dropdown para existentes, use:
            # nome_in = st.selectbox("Selecione ou Digite", options=lista_prods + ["Novo Item..."])
            qtd_in = st.number_input("Quantidade", min_value=1, value=1, key="qtd_in")
        with col2:
            preco_in = st.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f", key="price_in")
            resp_in = st.text_input("Responsável", value=st.session_state.get('username', ''), key="resp_in")
        
        if st.button("Confirmar Entrada", type="primary"):
            if nome_in and qtd_in > 0:
                ok, msg = registrar_movimentacao(nome_in, qtd_in, 'entrada', resp_in, preco_in)
                if ok:
                    st.toast("Entrada registrada com sucesso!", icon="✅")
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("Preencha o nome do produto.")

    with tab2:
        st.subheader("Registrar Saída")
        if not lista_prods:
            st.warning("Não há itens para retirar.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                nome_out = st.selectbox("Selecione o Produto", lista_prods)
                qtd_out = st.number_input("Quantidade", min_value=1, value=1, key="qtd_out")
            with c2:
                resp_out = st.text_input("Responsável pela Retirada", value=st.session_state.get('username', ''), key="resp_out")
                st.write("") 
                st.write("") 
                if st.button("Confirmar Saída", type="primary"):
                    ok, msg = registrar_movimentacao(nome_out, qtd_out, 'saida', resp_out)
                    if ok:
                        st.toast("Saída registrada!", icon="🚀")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)

def inventario_screen():
    st.title("🗃️ Gestão de Inventário")
    st.markdown("Edite os dados diretamente na tabela abaixo.")
    
    df = get_dataframe("SELECT id, nome, categoria, quantidade, preco_unitario, estoque_minimo, responsavel FROM estoque")
    
    # Editor de Dados (Excel-like)
    edited_df = st.data_editor(
        df,
        column_config={
            "preco_unitario": st.column_config.NumberColumn("Preço (R$)", format="R$ %.2f"),
            "quantidade": st.column_config.NumberColumn("Qtd Atual", help="Estoque físico"),
            "estoque_minimo": st.column_config.NumberColumn("Min. Alerta", help="Avisa quando baixar disso"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=["Geral", "Eletrônicos", "Papelaria", "Limpeza", "Outros"], required=True)
        },
        disabled=["id", "data_entrada"],
        hide_index=True,
        use_container_width=True,
        key="data_editor"
    )
    
    # Botão para salvar alterações em massa
    if st.button("💾 Salvar Alterações"):
        try:
            with db.get_connection() as conn:
                c = conn.cursor()
                # Itera sobre o DF editado e atualiza o banco
                # Nota: Em produção, compare o diff para ser mais eficiente
                for index, row in edited_df.iterrows():
                    c.execute("""
                        UPDATE estoque 
                        SET nome=?, categoria=?, quantidade=?, preco_unitario=?, estoque_minimo=?, responsavel=?
                        WHERE id=?
                    """, (row['nome'], row['categoria'], row['quantidade'], row['preco_unitario'], row['estoque_minimo'], row['responsavel'], row['id']))
            st.success("Inventário atualizado com sucesso!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

def relatorios_screen():
    st.title("📑 Relatórios e Auditoria")
    
    tipo_rel = st.radio("Tipo de Relatório", ["Histórico Completo", "Análise de Entrada vs Saída"], horizontal=True)
    
    df_hist = get_dataframe("SELECT * FROM historico ORDER BY data_hora DESC")
    
    if tipo_rel == "Histórico Completo":
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        
        # Botão Download
        csv = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar CSV", data=csv, file_name="historico_completo.csv", mime="text/csv")
        
    else:
        df_hist['data_hora'] = pd.to_datetime(df_hist['data_hora'])
        df_hist['date'] = df_hist['data_hora'].dt.date
        
        daily = df_hist.groupby(['date', 'tipo'])['quantidade'].sum().reset_index()
        
        chart = alt.Chart(daily).mark_line(point=True).encode(
            x='date',
            y='quantidade',
            color='tipo',
            tooltip=['date', 'tipo', 'quantidade']
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)

# --- MAIN APP FLOW ---

def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_screen()
    else:
        # Sidebar Navigation
        with st.sidebar:
            st.title("StockMaster v2.0")
            st.write(f"Olá, **{st.session_state['username']}**")
            st.markdown("---")
            
            menu = st.radio(
                "Navegação", 
                ["Dashboard", "Operações", "Inventário", "Relatórios"],
                index=0,
                label_visibility="collapsed"
            )
            
            st.markdown("---")
            if st.button("Sair / Logout", type="secondary"):
                st.session_state['logged_in'] = False
                st.rerun()
            
            # Mobile QR (Mantido do original pois é útil)
            with st.expander("📱 Acesso Mobile"):
                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    ip = s.getsockname()[0]
                    s.close()
                    st.image(f"https://chart.googleapis.com/chart?cht=qr&chs=150x150&chl=http://{ip}:8501")
                    st.caption(f"http://{ip}:8501")
                except:
                    st.write("Não foi possível gerar QR Code")

        # Roteamento de Páginas
        if menu == "Dashboard":
            dashboard_screen()
        elif menu == "Operações":
            operacoes_screen()
        elif menu == "Inventário":
            inventario_screen()
        elif menu == "Relatórios":
            relatorios_screen()

if __name__ == "__main__":
    main()