import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Inventario Tiendas", layout="wide")

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso")
    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            if u == "tienda" and p == "ventas2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

def cargar_datos():
    data = conn.read()
    data.columns = data.columns.str.strip().str.lower()
    return data

df = cargar_datos()

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("🛍️ Menú")
    locales = sorted(df['local'].unique())
    local_sel = st.selectbox("📍 Local:", locales)
    telas = sorted(df[df['local'] == local_sel]['tela'].unique())
    tela_sel = st.selectbox("🧶 Tela:", telas)
    if st.button("🚪 Salir"):
        st.session_state.logged_in = False
        st.rerun()

# --- CUERPO PRINCIPAL ---
st.header(f"Stock en {local_sel} - {tela_sel}")
df_f = df[(df['local'] == local_sel) & (df['tela'] == tela_sel)]
prendas = sorted(df_f['prenda'].unique())

if len(prendas) > 0:
    prenda_sel = st.selectbox("👕 Prenda:", prendas)
    df_p = df_f[df_f['prenda'] == prenda_sel]
    talla_sel = st.radio("📏 Talla:", sorted(df_p['talla'].unique()), horizontal=True)

    st.divider()

    # Filtramos la fila para editar
    df_edit = df_p[df_p['talla'] == talla_sel]

    for idx, row in df_edit.iterrows():
        c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
        c1.subheader(row['color'].upper())
        c2.metric("Stock", int(row['stock']))
        
        # Entrada de ajuste
        ajuste = c3.number_input(f"Ajuste {row['color']}", value=0, key=f"in_{idx}")
        
        if c4.button("Guardar", key=f"btn_{idx}"):
            # Calculamos nuevo stock
            nuevo_valor = int(row['stock']) + ajuste
            # Actualizamos el DataFrame original
            df.at[idx, 'stock'] = nuevo_valor
            
            # INTENTAR GUARDAR EN EXCEL
            try:
                # IMPORTANTE: Revisa si tu hoja se llama 'Sheet1' o 'Hoja 1'
                conn.update(worksheet="Sheet1", data=df)
                st.success(f"¡Actualizado! Nuevo stock: {nuevo_valor}")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
else:
    st.warning("No hay prendas en esta categoría.")

# Botón manual de refresco
if st.sidebar.button("🔄 Sincronizar"):
    st.cache_data.clear()
    st.rerun()

