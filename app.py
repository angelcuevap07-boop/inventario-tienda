import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Inventario Tiendas UCSUR", layout="wide")

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso al Sistema</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                if u == "tienda" and p == "ventas2026":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
    st.stop()

# --- 2. CONEXIÓN BLINDADA (ESTO ES LO NUEVO) ---
try:
    # Construimos las credenciales usando los Secrets de Streamlit Cloud
    creds = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": st.secrets["connections"]["gsheets"]["private_key"],
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"],
    }
    
    # Creamos la conexión pasando el diccionario de credenciales directamente
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def cargar_datos():
        # Usamos el link del excel que está en los secrets
        data = conn.read(ttl=0)
        data.columns = data.columns.str.strip().str.lower()
        return data

    df = cargar_datos()
except Exception as e:
    st.error(f"Error de configuración: {e}")
    st.stop()

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.title("🛍️ Panel Control")
    locales = sorted(df['local'].unique())
    local_sel = st.selectbox("📍 Selecciona Local:", locales)
    
    df_local = df[df['local'] == local_sel]
    telas = sorted(df_local['tela'].unique())
    tela_sel = st.selectbox("🧶 Tipo de Tela:", telas)
    
    st.divider()
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. GESTIÓN DE PRODUCTOS ---
st.header(f"📍 {local_sel} | {tela_sel}")

df_prenda_list = df_local[df_local['tela'] == tela_sel]
prendas = sorted(df_prenda_list['prenda'].unique())

if len(prendas) > 0:
    prenda_sel = st.selectbox("👕 Prenda:", prendas)
    df_p = df_prenda_list[df_prenda_list['prenda'] == prenda_sel]
    talla_sel = st.radio("📏 Talla:", sorted(df_p['talla'].unique()), horizontal=True)

    st.divider()

    # Filtro final por talla
    df_final = df_p[df_p['talla'] == talla_sel]

    for idx, row in df_final.iterrows():
        c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
        c1.subheader(row['color'].upper())
        c2.metric("Stock", int(float(row['stock'])))
        
        ajuste = c3.number_input(f"Cambio {row['color']}", value=0, step=1, key=f"in_{idx}")
        
        if c4.button("Guardar", key=f"btn_{idx}"):
            nuevo_valor = int(float(row['stock'])) + ajuste
            df.at[idx, 'stock'] = nuevo_valor
            
            try:
                # REVISA SI TU PESTAÑA SE LLAMA Sheet1 o Hoja 1
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("¡Sincronizado!")
                st.cache_data.clear()
                st.rerun()
            except Exception as err:
                st.error(f"Error al guardar: {err}")
else:
    st.warning("Sin datos.")

