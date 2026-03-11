import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Inventario - Guizado & Moda", layout="wide")

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
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.title("🛍️ Gestión de Tienda")
    modo = st.radio("Acción:", ["📦 Ver/Editar Stock", "🚚 Realizar Traslado"])
    st.divider()
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. MODO: EDITAR STOCK ---
if modo == "📦 Ver/Editar Stock":
    local_sel = st.selectbox("📍 Selecciona Local:", sorted(df['local'].unique()))
    df_local = df[df['local'] == local_sel]
    tela_sel = st.selectbox("🧶 Tipo de Tela:", sorted(df_local['tela'].unique()))
    
    st.header(f"📍 {local_sel} | {tela_sel}")
    prendas = sorted(df_local[df_local['tela'] == tela_sel]['prenda'].unique())

    if prendas:
        prenda_sel = st.selectbox("👕 Modelo:", prendas)
        df_modelo = df_local[(df_local['tela'] == tela_sel) & (df_local['prenda'] == prenda_sel)]
        
        # Resumen
        st.subheader("📊 Resumen del Modelo")
        c_res1, c_res2 = st.columns(2)
        c_res1.metric("Stock Total", int(df_modelo['stock'].sum()))
        c_res2.write("**Tallas:** " + ", ".join(df_modelo['talla'].unique()))
        
        st.divider()
        talla_sel = st.radio("📏 Talla:", sorted(df_modelo['talla'].unique()), horizontal=True)
        df_final = df_modelo[df_modelo['talla'] == talla_sel]

        for idx, row in df_final.iterrows():
            col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
            col1.write(f"**Color: {row['color'].upper()}**")
            col2.metric("Stock", int(row['stock']))
            ajuste = col3.number_input("Ajuste (+/-)", value=0, step=1, key=f"adj_{idx}")
            if col4.button("OK", key=f"btn_{idx}"):
                df.at[idx, 'stock'] = int(row['stock']) + ajuste
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Actualizado")
                st.cache_data.clear()
                st.rerun()

# --- 5. MODO: TRASLADO (Lo nuevo) ---
else:
    st.header("🚚 Traslado de Mercadería")
    col_a, col_b = st.columns(2)
    
    origen = col_a.selectbox("Desde:", sorted(df['local'].unique()), key="origen")
    destino = col_b.selectbox("Hacia:", [l for l in sorted(df['local'].unique()) if l != origen], key="destino")
    
    # Seleccionar qué mover
    df_origen = df[df['local'] == origen]
    prenda_t = st.selectbox("Producto a trasladar:", sorted(df_origen['prenda'].unique()))
    
    df_prenda_t = df_origen[df_origen['prenda'] == prenda_t]
    talla_t = st.selectbox("Talla:", sorted(df_prenda_t['talla'].unique()))
    color_t = st.selectbox("Color:", sorted(df_prenda_t[df_prenda_t['talla'] == talla_t]['color'].unique()))
    
    # Obtener stock actual en origen
    fila_origen = df[(df['local'] == origen) & (df['prenda'] == prenda_t) & (df['talla'] == talla_t) & (df['color'] == color_t)]
    stock_disp = int(fila_origen['stock'].values[0])
    
    st.warning(f"Stock disponible en {origen}: {stock_disp}")
    cantidad = st.number_input("Cantidad a mover:", min_value=1, max_value=stock_disp, step=1)
    
    if st.button("Confirmar Traslado"):
        # 1. Restar de origen
        idx_origen = fila_origen.index[0]
        
        # 2. Sumar en destino (buscamos si existe la fila en destino)
        fila_destino = df[(df['local'] == destino) & (df['prenda'] == prenda_t) & (df['talla'] == talla_t) & (df['color'] == color_t)]
        
        if not fila_destino.empty:
            idx_destino = fila_destino.index[0]
            df.at[idx_origen, 'stock'] -= cantidad
            df.at[idx_destino, 'stock'] += cantidad
            
            try:
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success(f"✅ ¡Traslado exitoso! Se movieron {cantidad} {prenda_t} de {origen} a {destino}.")
                st.cache_data.clear()
                # st.rerun() # Opcional para refrescar
            except Exception as e:
                st.error(f"Error al procesar: {e}")
        else:
            st.error(f"El producto no existe en el local de destino ({destino}). Primero créalo en el Excel.")
