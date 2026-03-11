import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

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
        for col in ['stock', 'precio_unidad', 'precio_mayor']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    df = cargar_datos()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 3. MENÚ PRINCIPAL ---
with st.sidebar:
    st.title("🛍️ Control Maestro")
    modo = st.radio("Menú:", ["📦 Ver/Editar Stock", "🚚 Traslados", "🏭 Producción (Taller)"])
    st.divider()
    if st.button("🚪 Salir"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. MODO: VER/EDITAR STOCK ---
if modo == "📦 Ver/Editar Stock":
    local_sel = st.selectbox("📍 Selecciona Local:", sorted(df['local'].unique()))
    df_local = df[df['local'] == local_sel]
    prendas = sorted(df_local['prenda'].unique())
    
    if prendas:
        prenda_sel = st.selectbox("👕 Modelo:", prendas)
        df_p = df_local[df_local['prenda'] == prenda_sel]
        talla_sel = st.radio("📏 Talla:", sorted(df_p['talla'].unique()), horizontal=True)
        
        for idx, row in df_p[df_p['talla'] == talla_sel].iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['color'].upper()}** (Unidad: S/{row['precio_unidad']})")
            c2.metric("Stock", int(row['stock']))
            ajuste = c3.number_input("Ajuste", value=0, key=f"v_{idx}")
            if st.button("Actualizar", key=f"b_{idx}"):
                df.at[idx, 'stock'] += ajuste
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Guardado")
                st.rerun()

# --- 5. MODO: TRASLADOS ---
elif modo == "🚚 Traslados":
    st.header("🚚 Mover Mercadería")
    col1, col2 = st.columns(2)
    origen = col1.selectbox("Desde:", sorted(df['local'].unique()))
    destino = col2.selectbox("Hacia:", [l for l in sorted(df['local'].unique()) if l != origen])
    
    df_orig = df[df['local'] == origen]
    prenda_t = st.selectbox("Prenda:", sorted(df_orig['prenda'].unique()))
    talla_t = st.selectbox("Talla:", sorted(df_orig[df_orig['prenda'] == prenda_t]['talla'].unique()))
    color_t = st.selectbox("Color:", sorted(df_orig[(df_orig['prenda'] == prenda_t) & (df_orig['talla'] == talla_t)]['color'].unique()))
    
    fila_orig = df_orig[(df_orig['prenda'] == prenda_t) & (df_orig['talla'] == talla_t) & (df_orig['color'] == color_t)].iloc[0]
    stock_max = int(fila_orig['stock'])
    
    if stock_max > 0:
        cant = st.number_input("Cantidad:", min_value=1, max_value=stock_max, value=1)
        if st.button("Confirmar Traslado"):
            idx_orig = fila_orig.name
            df.at[idx_orig, 'stock'] -= cant
            
            # Buscar o Crear en destino
            idx_dest = df[(df['local'] == destino) & (df['prenda'] == prenda_t) & (df['talla'] == talla_t) & (df['color'] == color_t)].index
            if not idx_dest.empty:
                df.at[idx_dest[0], 'stock'] += cant
            else:
                nueva = {'local': destino, 'tela': fila_orig['tela'], 'prenda': prenda_t, 'talla': talla_t, 'color': color_t, 'stock': cant, 'precio_unidad': fila_orig['precio_unidad'], 'precio_mayor': fila_orig['precio_mayor']}
                df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
            
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
            st.success("Traslado completado")
            st.rerun()
    else:
        st.error("Sin stock disponible.")

# --- 6. MODO: PRODUCCIÓN TALLER (Lo nuevo) ---
else:
    st.header("🏭 Ingreso de Nueva Producción (Taller)")
    with st.form("nueva_produccion"):
        col_t1, col_t2 = st.columns(2)
        n_prenda = col_t1.text_input("Nombre de la Prenda:", placeholder="Ej: Palazo").upper()
        n_tela = col_t2.text_input("Tipo de Tela:", value="General")
        
        col_t3, col_t4 = st.columns(2)
        n_talla = col_t3.selectbox("Talla:", ["ST", "S", "M", "L", "XL", "S/M"])
        n_color = col_t4.text_input("Color:", placeholder="Ej: Guinda, Azul, Negro").upper()
        
        col_p1, col_p2, col_p3 = st.columns(3)
        n_stock = col_p1.number_input("Cantidad Producida:", min_value=1, value=10)
        n_unidad = col_p2.number_input("Precio Unidad:", min_value=0.0, value=0.0)
        n_mayor = col_p3.number_input("Precio Mayor:", min_value=0.0, value=0.0)
        
        if st.form_submit_button("➕ Registrar en Taller"):
            # Buscar si ya existe esa combinación exacta en el Taller
            idx_existente = df[(df['local'] == "Taller") & (df['prenda'] == n_prenda) & (df['talla'] == n_talla) & (df['color'] == n_color)].index
            
            if not idx_existente.empty:
                df.at[idx_existente[0], 'stock'] += n_stock
                # Actualizar precios si se pusieron nuevos
                if n_unidad > 0: df.at[idx_existente[0], 'precio_unidad'] = n_unidad
                if n_mayor > 0: df.at[idx_existente[0], 'precio_mayor'] = n_mayor
            else:
                nueva_f = {
                    'local': 'Taller', 'tela': n_tela, 'prenda': n_prenda, 
                    'talla': n_talla, 'color': n_color, 'stock': n_stock, 
                    'precio_unidad': n_unidad, 'precio_mayor': n_mayor
                }
                df = pd.concat([df, pd.DataFrame([nueva_f])], ignore_index=True)
            
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
            st.success(f"✅ ¡Ingresado! {n_stock} unidades de {n_prenda} ({n_color}) añadidas al Taller.")
            st.rerun()
