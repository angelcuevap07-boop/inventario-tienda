import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Inventario Tiendas UCSUR", layout="wide")

# --- SISTEMA DE LOGIN ---
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

# --- CONEXIÓN DIRECTA CON SERVICE ACCOUNT ---
# Forzamos a que use los secretos detallados para evitar el error de 'Public Spreadsheet'
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def cargar_datos():
        # Cargamos los datos sin usar caché para que los cambios se vean al instante
        data = conn.read(ttl=0)
        data.columns = data.columns.str.strip().str.lower()
        # Convertir columnas clave a texto para evitar errores de búsqueda
        for col in ['local', 'tela', 'prenda', 'talla', 'color']:
            if col in data.columns:
                data[col] = data[col].astype(str).str.strip()
        return data

    df = cargar_datos()
except Exception as e:
    st.error(f"Error crítico de conexión: {e}")
    st.stop()

# --- INTERFAZ DE NAVEGACIÓN (BARRA LATERAL) ---
with st.sidebar:
    st.title("🛍️ Panel de Control")
    st.write(f"Conectado como: **Admin**")
    
    st.divider()
    
    # Filtro de Local
    locales_disponibles = sorted(df['local'].unique())
    local_sel = st.selectbox("📍 SELECCIONA LOCAL:", locales_disponibles)
    
    # Filtro de Tela
    df_local = df[df['local'] == local_sel]
    telas_disponibles = sorted(df_local['tela'].unique())
    tela_sel = st.selectbox("🧶 TIPO DE TELA:", telas_disponibles)
    
    st.divider()
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# --- PANEL CENTRAL (GESTIÓN DE STOCK) ---
st.header(f"📍 Local: {local_sel} | Tela: {tela_sel}")

# Filtrar por prenda
df_prenda_list = df_local[df_local['tela'] == tela_sel]
prendas_disponibles = sorted(df_prenda_list['prenda'].unique())

if len(prendas_disponibles) > 0:
    prenda_sel = st.selectbox("👕 Selecciona la Prenda:", prendas_disponibles)
    
    # Filtrar por talla
    df_talla_list = df_prenda_list[df_prenda_list['prenda'] == prenda_sel]
    talla_sel = st.radio("📏 Talla:", sorted(df_talla_list['talla'].unique()), horizontal=True)

    st.divider()

    # MOSTRAR COLORES Y PERMITIR EDICIÓN
    df_final = df_talla_list[df_talla_list['talla'] == talla_sel]
    
    for idx, row in df_final.iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
            
            with c1:
                st.subheader(row['color'].upper())
            
            with c2:
                st.metric("Stock actual", f"{int(float(row['stock']))}")
            
            with c3:
                # El usuario pone -2 si vendió o +5 si llegó mercadería
                ajuste = st.number_input(f"Ajuste {row['color']}", value=0, step=1, key=f"input_{idx}")
            
            with c4:
                if st.button("Guardar ✅", key=f"btn_{idx}"):
                    nuevo_total = int(float(row['stock'])) + ajuste
                    
                    # Actualizamos el DataFrame local
                    df.at[idx, 'stock'] = nuevo_total
                    
                    # ENVIAR AL EXCEL
                    try:
                        # Asegúrate que tu pestaña en Excel se llame 'Sheet1' o cámbialo aquí
                        conn.update(worksheet="Sheet1", data=df)
                        st.success(f"¡Actualizado! {row['color']} ahora tiene {nuevo_total}")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as err:
                        st.error(f"Error al escribir en Excel: {err}")
            st.divider()
else:
    st.warning("No hay productos registrados para esta selección.")

# Refresco manual
if st.sidebar.button("🔄 Sincronizar"):
    st.cache_data.clear()
    st.rerun()
