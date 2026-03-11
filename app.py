import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_mic_recorder import mic_recorder
import pandas as pd
import re

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Inventario Guizado & Moda", layout="wide", page_icon="🛍️")

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

# --- 2. CONEXIÓN A DATOS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    def cargar_datos():
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        data = conn.read(spreadsheet=url, ttl=0)
        data.columns = data.columns.str.strip().str.lower()
        # Asegurar que las columnas numéricas sean tratadas como tales
        for col in ['stock', 'precio_unitario', 'precio_mayorista']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    df = cargar_datos()
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.title("🛍️ Control Maestro")
    modo = st.radio("Selecciona una opción:", 
                    ["📦 Ver/Editar Stock", "🚚 Traslado Inteligente (Voz)", "🏭 Gestión Taller"])
    st.divider()
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# --- 4. MODO: VER/EDITAR STOCK (FILTRO STOCK > 0) ---
if modo == "📦 Ver/Editar Stock":
    local_sel = st.selectbox("📍 Selecciona Local:", sorted(df['local'].unique()))
    
    # Filtramos para no mostrar lo que está en 0
    df_local = df[(df['local'] == local_sel) & (df['stock'] > 0)]
    prendas = sorted(df_local['prenda'].unique())
    
    if prendas:
        prenda_sel = st.selectbox("👕 Modelo:", prendas)
        df_p = df_local[df_local['prenda'] == prenda_sel]
        talla_sel = st.radio("📏 Talla:", sorted(df_p['talla'].unique()), horizontal=True)
        
        st.subheader(f"Inventario en {local_sel}")
        for idx, row in df_p[df_p['talla'] == talla_sel].iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['color'].upper()}** (P. Unidad: S/{row['precio_unitario']})")
            c2.metric("Stock", int(row['stock']))
            ajuste = c3.number_input("Venta/Ajuste", value=0, key=f"v_{idx}")
            if st.button("Guardar", key=f"b_{idx}"):
                df.at[idx, 'stock'] += ajuste
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("¡Sincronizado!")
                st.cache_data.clear()
                st.rerun()
    else:
        st.warning("No hay productos con stock en este local.")

# --- 5. MODO: TRASLADO INTELIGENTE (VOZ + AUTO-REGISTRO) ---
elif modo == "🚚 Traslado Inteligente (Voz)":
    st.header("🚚 Traslado con Micrófono")
    st.write("Presiona el botón y di: 'De Taller a Moda Palazo talla ST color Negro 5'")
    
    audio_info = mic_recorder(start_prompt="🎤 Toca para hablar", stop_prompt="🛑 Detener", key='recorder')
    
    voz = audio_info['text'].lower() if audio_info else ""
    if voz: st.info(f"Escuché: {voz}")

    # Lógica de detección (IA básica)
    sel_orig, sel_dest, sel_prenda, sel_talla, sel_color, sel_cant = None, None, None, None, None, 1
    
    if voz:
        locales = [l.lower() for l in df['local'].unique()]
        for l in locales:
            if f"de {l}" in voz: sel_orig = l.capitalize()
            if f"a {l}" in voz: sel_dest = l.capitalize()
        for p in [p.lower() for p in df['prenda'].unique()]:
            if p in voz: sel_prenda = p.upper()
        for t in [t.lower() for t in df['talla'].unique()]:
            if f"talla {t}" in voz or f" {t} " in voz: sel_talla = t.upper()
        for c in [c.lower() for c in df['color'].unique()]:
            if c in voz: sel_color = c.upper()
        nums = re.findall(r'\d+', voz)
        if nums: sel_cant = int(nums[-1])

    st.divider()
    col1, col2 = st.columns(2)
    origen = col1.selectbox("Origen:", sorted(df['local'].unique()), 
                            index=sorted(df['local'].unique()).index(sel_orig) if sel_orig in df['local'].unique() else 0)
    destino = col2.selectbox("Destino:", [l for l in sorted(df['local'].unique()) if l != origen],
                             index=0 if not sel_dest else ([l for l in sorted(df['local'].unique()) if l != origen].index(sel_dest) if sel_dest in df['local'].unique() else 0))
    
    df_orig = df[(df['local'] == origen) & (df['stock'] > 0)]
    if not df_orig.empty:
        prenda_t = st.selectbox("Prenda:", sorted(df_orig['prenda'].unique()),
                                index=sorted(df_orig['prenda'].unique()).index(sel_prenda) if sel_prenda in df_orig['prenda'].unique() else 0)
        df_p = df_orig[df_orig['prenda'] == prenda_t]
        talla_t = st.selectbox("Talla:", sorted(df_p['talla'].unique()),
                               index=sorted(df_p['talla'].unique()).index(sel_talla) if sel_talla in df_p['talla'].unique() else 0)
        df_c = df_p[df_p['talla'] == talla_t]
        color_t = st.selectbox("Color:", sorted(df_c['color'].unique()),
                               index=sorted(df_c['color'].unique()).index(sel_color) if sel_color in df_c['color'].unique() else 0)
        
        fila_orig = df_c[df_c['color'] == color_t].iloc[0]
        st.warning(f"Stock disponible: {int(fila_orig['stock'])}")
        cant = st.number_input("Cantidad:", min_value=1, max_value=int(fila_orig['stock']), value=min(sel_cant, int(fila_orig['stock'])))
        
        if st.button("🚀 Confirmar Traslado"):
            idx_orig = fila_orig.name
            df.at[idx_orig, 'stock'] -= cant
            # Buscar en destino o CREAR automáticamente
            idx_dest = df[(df['local'] == destino) & (df['prenda'] == prenda_t) & (df['talla'] == talla_t) & (df['color'] == color_t)].index
            if not idx_dest.empty:
                df.at[idx_dest[0], 'stock'] += cant
            else:
                nueva = {'local': destino, 'tela': fila_orig['tela'], 'prenda': prenda_t, 'talla': talla_t, 'color': color_t, 'stock': cant, 'precio_unitario': fila_orig['precio_unitario'], 'precio_mayorista': fila_orig['precio_mayorista']}
                df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
            st.success("Traslado completado con éxito")
            st.cache_data.clear()
            st.rerun()
    else:
        st.error("El origen no tiene mercadería disponible.")

# --- 6. MODO: GESTIÓN TALLER (REPONER O CREAR) ---
else:
    st.header("🏭 Producción y Almacén Taller")
    tab1, tab2 = st.tabs(["📥 Reponer Stock", "➕ Nueva Prenda/Color"])
    
    with tab1:
        df_taller = df[df['local'] == "Taller"]
        if not df_taller.empty:
            p_ex = st.selectbox("Modelo:", sorted(df_taller['prenda'].unique()))
            df_p_ex = df_taller[df_taller['prenda'] == p_ex]
            t_ex = st.selectbox("Talla:", sorted(df_p_ex['talla'].unique()), key="tex")
            c_ex = st.selectbox("Color:", sorted(df_p_ex[df_p_ex['talla'] == t_ex]['color'].unique()), key="cex")
            cant_ex = st.number_input("Cantidad Producida:", min_value=1, value=12)
            if st.button("Sumar al Taller"):
                idx_ex = df[(df['local'] == "Taller") & (df['prenda'] == p_ex) & (df['talla'] == t_ex) & (df['color'] == c_ex)].index[0]
                df.at[idx_ex, 'stock'] += cant_ex
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Stock actualizado")
                st.cache_data.clear()
                st.rerun()

    with tab2:
        with st.form("crear"):
            col1, col2 = st.columns(2)
            n_prenda = col1.text_input("Nombre Prenda:").upper()
            n_tela = col2.text_input("Tela:", value="General")
            n_talla = st.selectbox("Talla:", ["ST", "S", "M", "L", "S/M"])
            n_color = st.text_input("Color:").upper()
            n_stock = st.number_input("Stock Inicial:", min_value=1)
            n_uni = st.number_input("Precio Unidad:", min_value=0.0)
            n_may = st.number_input("Precio Mayor:", min_value=0.0)
            if st.form_submit_button("Registrar en Taller"):
                nueva = {'local': 'Taller', 'tela': n_tela, 'prenda': n_prenda, 'talla': n_talla, 'color': n_color, 'stock': n_stock, 'precio_unitario': n_uni, 'precio_mayorista': n_may}
                df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df)
                st.success("Producto creado en el taller")
                st.cache_data.clear()
                st.rerun()
