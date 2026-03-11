import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. CONFIGURACIÓN E INICIO
st.set_page_config(page_title="Inventario Inteligente - Guizado & Moda", layout="wide")

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
        for col in ['stock', 'precio_unidad', 'precio_mayor']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    df = cargar_datos()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 3. MENÚ ---
with st.sidebar:
    st.title("🛍️ Control de Stock")
    modo = st.radio("Acción:", ["📦 Ver/Editar Stock", "🚚 Traslado Inteligente"])
    if st.button("🚪 Salir"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. MODO: EDICIÓN MANUAL ---
if modo == "📦 Ver/Editar Stock":
    local_sel = st.selectbox("📍 Local:", sorted(df['local'].unique()))
    df_local = df[df['local'] == local_sel]
    prenda_sel = st.selectbox("👕 Prenda:", sorted(df_local['prenda'].unique()))
    
    df_p = df_local[df_local['prenda'] == prenda_sel]
    talla_sel = st.radio("📏 Talla:", sorted(df_p['talla'].unique()), horizontal=True)
    
    for idx, row in df_p[df_p['talla'] == talla_sel].iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{row['color'].upper()}** (S/ {row['precio_unidad']})")
        c2.metric("Stock", int(row['stock']))
        nuevo = c3.number_input("Ajuste", value=0, key=f"ed_{idx}")
        if st.button("Guardar", key=f"b_{idx}"):
            df.at[idx, 'stock'] += nuevo
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
            st.success("Ok")
            st.rerun()

# --- 5. MODO: TRASLADO INTELIGENTE (VOZ + AUTO-REGISTRO) ---
else:
    st.header("🚚 Traslado con Asistente de Voz")
    
    # Instrucción de voz
    st.info("💡 Haz clic en el cuadro de abajo y usa el MICRÓFONO de tu teclado. Di algo como: 'De taller a moda palazo talla ST guinda 4'")
    voz = st.text_input("🎙️ Dicta tu instrucción aquí:", placeholder="Ej: De taller a guizado pantalon fresh S azul 5")
    
    # Lógica de procesamiento simple (IA de texto)
    # Buscamos patrones: "de [origen] a [destino] [prenda] talla [talla] [color] [cantidad]"
    
    st.divider()
    st.subheader("Configuración Manual del Traslado")
    
    col_a, col_b = st.columns(2)
    origen = col_a.selectbox("Origen:", sorted(df['local'].unique()))
    destino = col_b.selectbox("Destino:", [l for l in sorted(df['local'].unique()) if l != origen])
    
    prenda_t = st.selectbox("Producto:", sorted(df[df['local'] == origen]['prenda'].unique()))
    talla_t = st.selectbox("Talla:", sorted(df[(df['local'] == origen) & (df['prenda'] == prenda_t)]['talla'].unique()))
    
    df_filt = df[(df['local'] == origen) & (df['prenda'] == prenda_t) & (df['talla'] == talla_t)]
    color_t = st.selectbox("Color:", sorted(df_filt['color'].unique()))
    
    fila_origen = df_filt[df_filt['color'] == color_t].iloc[0]
    st.warning(f"Disponible en {origen}: {int(fila_origen['stock'])}")
    
    cant = st.number_input("Cantidad:", min_value=1, max_value=int(fila_origen['stock']), step=1)

    if st.button("🚀 Confirmar Traslado"):
        idx_origen = df_filt[df_filt['color'] == color_t].index[0]
        
        # BUSCAR O CREAR EN DESTINO
        idx_dest_list = df[(df['local'] == destino) & 
                           (df['prenda'] == prenda_t) & 
                           (df['talla'] == talla_t) & 
                           (df['color'] == color_t)].index
        
        if not idx_dest_list.empty:
            # Si existe, sumamos
            idx_destino = idx_dest_list[0]
            df.at[idx_origen, 'stock'] -= cant
            df.at[idx_destino, 'stock'] += cant
        else:
            # SI NO EXISTE, LO CREAMOS AUTOMÁTICAMENTE
            nueva_fila = {
                'local': destino,
                'tela': fila_origen['tela'],
                'prenda': prenda_t,
                'talla': talla_t,
                'color': color_t,
                'stock': cant,
                'precio_unidad': fila_origen['precio_unidad'],
                'precio_mayor': fila_origen['precio_mayor']
            }
            df.at[idx_origen, 'stock'] -= cant
            df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
            st.info(f"✨ Se creó el producto '{prenda_t}' automáticamente en {destino}")

        try:
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
            st.success(f"✅ Movido: {cant} unidades de {prenda_t} a {destino}")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")
