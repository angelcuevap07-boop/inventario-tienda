import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario Guizado & Moda", layout="wide")

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
        # Mapeo de columnas para evitar errores
        mapeo = {'precio unidad': 'precio_unitario', 'precio_mayor': 'precio_mayorista'}
        data = data.rename(columns=mapeo)
        for col in ['stock', 'precio_unitario', 'precio_mayorista']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    df = cargar_datos()
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- 3. MENÚ ---
with st.sidebar:
    st.title("🛍️ Control Maestro")
    modo = st.radio("Menú:", ["📦 Stock Tiendas", "🚚 Traslados Inteligentes", "🏭 Gestión Taller"])
    if st.button("🚪 Salir"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. MODO: STOCK ---
if modo == "📦 Stock Tiendas":
    local_sel = st.selectbox("📍 Local:", sorted(df['local'].unique()))
    df_local = df[(df['local'] == local_sel) & (df['stock'] > 0)]
    prenda_sel = st.selectbox("👕 Prenda:", sorted(df_local['prenda'].unique()))
    df_p = df_local[df_local['prenda'] == prenda_sel]
    talla_sel = st.radio("📏 Talla:", sorted(df_p['talla'].unique()), horizontal=True)
    
    for idx, row in df_p[df_p['talla'] == talla_sel].iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{row['color'].upper()}**")
        c2.metric("Stock", int(row['stock']))
        adj = c3.number_input("Ajuste", value=0, key=f"adj_{idx}")
        if st.button("Actualizar", key=f"btn_{idx}"):
            df.at[idx, 'stock'] += adj
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
            st.success("Guardado")
            st.cache_data.clear()
            st.rerun()

# --- 5. MODO: TRASLADOS (Usa el micro de tu teclado) ---
elif modo == "🚚 Traslados Inteligentes":
    st.header("🚚 Traslado con Voz (Teclado)")
    inst = st.text_input("Dicta aquí: (Ej: De taller a moda palazo talla ST negro 5)").lower()
    
    # IA de procesamiento de texto
    s_orig, s_dest, s_prenda, s_talla, s_color, s_cant = None, None, None, None, None, 1
    if inst:
        for l in df['local'].unique():
            if f"de {l.lower()}" in inst: s_orig = l
            if f"a {l.lower()}" in inst: s_dest = l
        for p in df['prenda'].unique():
            if p.lower() in inst: s_prenda = p
        for t in df['talla'].unique():
            if f"talla {t.lower()}" in inst or f" {t.lower()} " in inst: s_talla = t
        for c in df['color'].unique():
            if c.lower() in inst: s_color = c
        n = re.findall(r'\d+', inst)
        if n: s_cant = int(n[-1])

    col1, col2 = st.columns(2)
    origen = col1.selectbox("Desde:", sorted(df['local'].unique()), index=sorted(df['local'].unique()).index(s_orig) if s_orig in df['local'].unique() else 0)
    destino = col2.selectbox("Hacia:", [l for l in sorted(df['local'].unique()) if l != origen], index=0)
    
    df_o = df[(df['local'] == origen) & (df['stock'] > 0)]
    if not df_o.empty:
        p_t = st.selectbox("Prenda:", sorted(df_o['prenda'].unique()), index=sorted(df_o['prenda'].unique()).index(s_prenda) if s_prenda in df_o['prenda'].unique() else 0)
        t_t = st.selectbox("Talla:", sorted(df_o[df_o['prenda'] == p_t]['talla'].unique()))
        c_t = st.selectbox("Color:", sorted(df_o[(df_o['prenda'] == p_t) & (df_o['talla'] == t_t)]['color'].unique()))
        
        fila_o = df_o[(df_o['prenda'] == p_t) & (df_o['talla'] == t_t) & (df_o['color'] == c_t)].iloc[0]
        cant = st.number_input("Cantidad:", min_value=1, max_value=int(fila_o['stock']), value=min(s_cant, int(fila_o['stock'])))
        
        if st.button("🚀 Confirmar Traslado"):
            df.at[fila_o.name, 'stock'] -= cant
            idx_d = df[(df['local'] == destino) & (df['prenda'] == p_t) & (df['talla'] == t_t) & (df['color'] == c_t)].index
            if not idx_d.empty:
                df.at[idx_d[0], 'stock'] += cant
            else:
                nueva = {'local': destino, 'tela': fila_o['tela'], 'prenda': p_t, 'talla': t_t, 'color': c_t, 'stock': cant, 'precio_unitario': fila_o.get('precio_unitario', 0), 'precio_mayorista': 0}
                df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
            st.success("Traslado Exitoso")
            st.cache_data.clear()
            st.rerun()

# --- 6. MODO: TALLER ---
else:
    st.header("🏭 Gestión Taller")
    tab1, tab2 = st.tabs(["📥 Agregar Stock", "➕ Nueva Prenda"])
    with tab1:
        df_t = df[df['local'] == "Taller"]
        if not df_t.empty:
            p = st.selectbox("Modelo:", sorted(df_t['prenda'].unique()))
            t = st.selectbox("Talla:", sorted(df_t[df_t['prenda'] == p]['talla'].unique()))
            c = st.selectbox("Color:", sorted(df_t[(df_t['prenda'] == p) & (df_t['talla'] == t)]['color'].unique()))
            cant_t = st.number_input("Cantidad:", min_value=1, value=12)
            if st.button("Sumar"):
                idx = df[(df['local'] == "Taller") & (df['prenda'] == p) & (df['talla'] == t) & (df['color'] == c)].index[0]
                df.at[idx, 'stock'] += cant_t
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Añadido")
                st.rerun()
