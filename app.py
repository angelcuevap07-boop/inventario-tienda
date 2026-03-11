import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Inventario Real - Gestión", layout="wide")

# --- LOGIN ---
def login():
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso al Inventario</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login"):
            usuario = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                if usuario == "tienda" and clave == "ventas2026":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    data = conn.read()
    data.columns = data.columns.str.strip().str.lower()
    return data

df = cargar_datos()

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("🛍️ Menú Inventario")
    opcion_local = st.selectbox("📍 Selecciona Local:", sorted(df['local'].unique()))
    st.divider()
    df_local = df[df['local'] == opcion_local]
    opcion_tela = st.selectbox("🧶 Tipo de Tela:", sorted(df_local['tela'].unique()))
    st.divider()
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.header(f"📍 Local: {opcion_local}")
st.info(f"Viendo tela: {opcion_tela}")

df_prenda_list = df_local[df_local['tela'] == opcion_tela]
opcion_prenda = st.selectbox("👕 Selecciona Prenda:", sorted(df_prenda_list['prenda'].unique()))

st.write("### 📏 Selecciona la Talla:")
df_final = df_prenda_list[df_prenda_list['prenda'] == opcion_prenda]
opcion_talla = st.radio("Tallas", sorted(df_final['talla'].unique()), horizontal=True, label_visibility="collapsed")

st.divider()

# --- VISUALIZACIÓN Y EDICIÓN ---
df_colores = df_final[df_final['talla'] == opcion_talla]

if not df_colores.empty:
    for index, row in df_colores.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 3, 2])
            
            with col1:
                st.subheader(row['color'].upper())
            
            with col2:
                # Mostramos el stock actual
                st.metric("Stock Actual", f"{int(row['stock'])} und")
            
            with col3:
                # Campo para agregar o quitar
                cambio = st.number_input(f"Ajustar {row['color']}", value=0, step=1, key=f"input_{index}")
            
            with col4:
                if st.button("Confirmar ✅", key=f"btn_{index}"):
                    if cambio != 0:
                        # Calculamos el nuevo valor
                        nuevo_stock = int(row['stock']) + cambio
                        
                        # Actualizamos el DataFrame original usando el índice
                        # Nota: En gsheets_connection, para actualizar, usualmente 
                        # sobreescribimos la hoja con el nuevo DataFrame
                        df.at[index, 'stock'] = nuevo_stock
                        
                        # GUARDAR EN GOOGLE SHEETS
                        conn.update(data=df)
                        st.success(f"¡Actualizado! {row['color']} ahora tiene {nuevo_stock}")
                        st.cache_data.clear()
                        st.rerun()
            st.divider()
else:
    st.warning("No hay datos disponibles.")

# Botón para refrescar
if st.sidebar.button("🔄 Sincronizar Excel"):
    st.cache_data.clear()
    st.rerun()
