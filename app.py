import streamlit as st
import datetime

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Liga Manager Fantasy", layout="wide")

# Credenciales de los equipos y datos iniciales
EQUIPOS_PIN = {
    "Real Madrid": "1234",
    "FC Barcelona": "5678",
    "Atletico de Madrid": "9012",
    "Manchester City": "3456",
    "Bayern München": "7890"
}

JUGADORES_BASE = [
    {"id": 1, "nombre": "Kylian Mbappé", "pos": "DEL", "grl": 91, "precio": 180000000},
    {"id": 2, "nombre": "Erling Haaland", "pos": "DEL", "grl": 91, "precio": 175000000},
    {"id": 3, "nombre": "Jude Bellingham", "pos": "MED", "grl": 90, "precio": 150000000},
    {"id": 4, "nombre": "Vinícius Jr.", "pos": "DEL", "grl": 90, "precio": 150000000},
    {"id": 5, "nombre": "Rodri", "pos": "MED", "grl": 91, "precio": 130000000},
    {"id": 6, "nombre": "Bukayo Saka", "pos": "DEL", "grl": 88, "precio": 120000000},
    {"id": 7, "nombre": "Pedri", "pos": "MED", "grl": 86, "precio": 90000000},
    {"id": 8, "nombre": "William Saliba", "pos": "DEF", "grl": 87, "precio": 80000000},
    {"id": 9, "nombre": "Lamine Yamal", "pos": "DEL", "grl": 82, "precio": 90000000},
    {"id": 10, "nombre": "Thibaut Courtois", "pos": "POR", "grl": 89, "precio": 60000000},
]

# Estado persistente
if "subasta_activa" not in st.session_state:
    st.session_state.subasta_activa = False
if "hora_fin_subasta" not in st.session_state:
    st.session_state.hora_fin_subasta = None
if "jugador_idx" not in st.session_state:
    st.session_state.jugador_idx = 0
if "puja_actual" not in st.session_state:
    st.session_state.puja_actual = JUGADORES_BASE[0]["precio"]
if "postor_actual" not in st.session_state:
    st.session_state.postor_actual = "Nadie"
if "plantillas" not in st.session_state:
    st.session_state.plantillas = {eq: [] for eq in EQUIPOS_PIN}
if "presupuestos" not in st.session_state:
    st.session_state.presupuestos = {eq: 300000000 for eq in EQUIPOS_PIN}

# --- BARRA LATERAL (AUTENTICACIÓN Y ADMIN) ---
st.sidebar.title("🎮 Menú de Usuario")
equipo_sel = st.sidebar.selectbox("Selecciona tu Equipo", list(EQUIPOS_PIN.keys()))
pin_ingresado = st.sidebar.text_input("Ingresa tu PIN", type="password")

login_correcto = pin_ingresado == EQUIPOS_PIN.get(equipo_sel)

if login_correcto:
    st.sidebar.success(f"Sesión: {equipo_sel}")
    st.sidebar.metric("Presupuesto", f"{st.session_state.presupuestos[equipo_sel]:,} €")
else:
    st.sidebar.warning("Introduce tu PIN para realizar acciones.")

st.sidebar.divider()
es_admin = st.sidebar.checkbox("Modo Administrador")

if es_admin:
    st.sidebar.subheader("⚙️ Control de Subastas")
    if st.sidebar.button("⏱️ Iniciar Temporizador (1h)"):
        st.session_state.hora_fin_subasta = datetime.datetime.now() + datetime.timedelta(hours=1)
        st.session_state.subasta_activa = True
        st.sidebar.success("Reloj activado.")
    
    if st.sidebar.button("🛑 Pausar Subasta"):
        st.session_state.subasta_activa = False
        st.session_state.hora_fin_subasta = None
        st.sidebar.warning("Pausado.")

    if st.sidebar.button("➡️ Siguiente Jugador"):
        if st.session_state.jugador_idx + 1 < len(JUGADORES_BASE):
            st.session_state.jugador_idx += 1
            jugador = JUGADORES_BASE[st.session_state.jugador_idx]
            st.session_state.puja_actual = jugador["precio"]
            st.session_state.postor_actual = "Nadie"
            st.rerun()

# --- NAVEGACIÓN PRINCIPAL ---
opcion_menu = st.radio(
    "Navegación", 
    ["🔥 Mercado de Subastas", "🛡️ Mi Equipo / Plantilla", "📊 Tabla General y Presupuestos"], 
    horizontal=True
)

st.divider()

if opcion_menu == "🔥 Mercado de Subastas":
    st.title("🔥 Mercado de Subastas")
    
    j_actual = JUGADORES_BASE[st.session_state.jugador_idx]
    st.subheader(f"Jugador en puja: **{j_actual['nombre']}** ({j_actual['pos']} - GRL {j_actual['grl']})")
    
    # Temporizador visible
    if st.session_state.subasta_activa and st.session_state.hora_fin_subasta:
        tiempo_restante = st.session_state.hora_fin_subasta - datetime.datetime.now()
        if tiempo_restante.total_seconds() > 0:
            m, s = divmod(int(tiempo_restante.total_seconds()), 60)
            h, m = divmod(m, 60)
            st.metric("⏳ Tiempo restante:", f"{h:02d}:{m:02d}:{s:02d}")
        else:
            st.session_state.subasta_activa = False
            st.error("🚨 La subasta ha finalizado.")
    else:
        st.info("Subasta pausada por el Administrador.")

    st.write(f"**Puja más alta:** {st.session_state.puja_actual:,} € por **{st.session_state.postor_actual}**")
    
    if login_correcto:
        monto = st.number_input(
            "Tu Oferta (€):", 
            min_value=st.session_state.puja_actual + 1000000, 
            step=1000000
        )
        if st.button("Enviar Oferta"):
            if not st.session_state.subasta_activa:
                st.error("La subasta está pausada.")
            elif monto > st.session_state.presupuestos[equipo_sel]:
                st.error("No tienes suficiente presupuesto.")
            else:
                st.session_state.puja_actual = monto
                st.session_state.postor_actual = equipo_sel
                st.success("¡Oferta enviada!")
                st.rerun()

elif opcion_menu == "🛡️ Mi Equipo / Plantilla":
    st.title(f"🛡️ Gestión de {equipo_sel if login_correcto else 'Equipos'}")
    if login_correcto:
        st.write(f"**Plantilla actual de {equipo_sel}:**")
        st.write(st.session_state.plantillas[equipo_sel] if st.session_state.plantillas[equipo_sel] else "Sin fichajes aún.")
    else:
        st.warning("Inicia sesión en la barra lateral para ver tu equipo.")

elif opcion_menu == "📊 Tabla General y Presupuestos":
    st.title("📊 Resumen de la Liga")
    st.table([{"Equipo": eq, "Presupuesto (€)": f"{st.session_state.presupuestos[eq]:,}"} for eq in EQUIPOS_PIN])
