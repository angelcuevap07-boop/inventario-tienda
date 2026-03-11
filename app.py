import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Tiendas - Guizado & Moda", layout="wide")

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso al Sistema</h2>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
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

# --- 2. CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def cargar_datos():
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        data = conn.read(spreadsheet=url, ttl=0)
        data.columns = data.columns.str.strip().str.lower()
        
        # Asegurar columnas numéricas
        for col in ['stock', 'precio_unidad', 'precio_mayor']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data

    df = cargar_datos()
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.title("🛍️ Panel Control")
    local_sel = st.selectbox("📍 Selecciona Local:", sorted(df['local'].unique()))
    df_local = df[df['local'] == local_sel]
    
    tela_sel = st.selectbox("🧶 Tipo de Tela:", sorted(df_local['tela'].unique()))
    st.divider()
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. GESTIÓN Y RESUMEN ---
st.header(f"📍 {local_sel} | {tela_sel}")

df_prenda_list = df_local[df_local['tela'] == tela_sel]
prendas = sorted(df_prenda_list['prenda'].unique())

if prendas:
    prenda_sel = st.selectbox("👕 Selecciona Modelo:", prendas)
    df_modelo = df_prenda_list[df_prenda_list['prenda'] == prenda_sel]
    
    # --- BLOQUE DE RESUMEN TOTAL (Lo que pediste) ---
    st.subheader("📊 Resumen del Modelo")
    total_stock_modelo = int(df_modelo['stock'].sum())
    # Calculamos el valor total basado en precio_unidad
    valor_total_stock = (df_modelo['stock'] * df_modelo['precio_unidad']).sum()
    
    res1, res2, res3 = st.columns(3)
    res1.metric("Stock Total (Todas las tallas)", total_stock_modelo)
    res2.metric("Valor del Inventario", f"S/ {valor_total_stock:,.2f}")
    res3.write("**Tallas disponibles:** " + ", ".join(df_modelo['talla'].unique()))
    
    st.divider()

    # --- EDICIÓN POR TALLA ---
    talla_sel = st.radio("📏 Selecciona Talla para modificar:", sorted(df_modelo['talla'].unique()), horizontal=True)
    df_final = df_modelo[df_modelo['talla'] == talla_sel]

    for idx, row in df_final.iterrows():
        c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
        
        with c1:
            st.markdown(f"### Color: {row['color'].upper()}")
            st.caption(f"Precio: S/ {row['precio_unidad']}")
        
        c2.metric("Stock Actual", int(row['stock']))
        
        ajuste = c3.number_input(f"Venta/Ingreso ({row['color']})", value=0, step=1, key=f"in_{idx}")
        
        if c4.button("Actualizar", key=f"btn_{idx}"):
            nuevo_valor = int(row['stock']) + ajuste
            if nuevo_valor < 0:
                st.error("El stock no puede ser menor a 0")
            else:
                df.at[idx, 'stock'] = nuevo_valor
                try:
                    conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                    st.success("¡Datos guardados!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as err:
                    st.error(f"Error: {err}")
else:
    st.warning("No hay productos registrados en este local/tela.")
