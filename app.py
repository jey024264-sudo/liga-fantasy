import streamlit as st
import datetime

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Liga Fantasy", layout="wide")

# Base de datos ampliada de jugadores
JUGADORES_DISPONIBLES = [
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
    {"id": 11, "nombre": "Federico Valverde", "pos": "MED", "grl": 88, "precio": 100000000},
    {"id": 12, "nombre": "Cole Palmer", "pos": "MED", "grl": 85, "precio": 80000000},
]

# Inicialización de variables de estado global
if "subasta_activa" not in st.session_state:
    st.session_state.subasta_activa = False
if "hora_fin_subasta" not in st.session_state:
    st.session_state.hora_fin_subasta = None
if "jugador_actual_idx" not in st.session_state:
    st.session_state.jugador_actual_idx = 0
if "puja_actual" not in st.session_state:
    st.session_state.puja_actual = JUGADORES_DISPONIBLES[0]["precio"]
if "postor_actual" not in st.session_state:
    st.session_state.postor_actual = "Nadie"

# --- PANEL DE ADMINISTRACIÓN ---
st.sidebar.title("⚙️ Panel de Control (Admin)")
es_admin = st.sidebar.checkbox("Modo Administrador")

if es_admin:
    st.sidebar.subheader("Temporizador y Mercado")
    
    # Iniciar temporizador de 1 hora
    if st.sidebar.button("⏱️ Iniciar subasta (1 Hora)"):
        st.session_state.hora_fin_subasta = datetime.datetime.now() + datetime.timedelta(hours=1)
        st.session_state.subasta_activa = True
        st.sidebar.success("Subasta de 1 hora iniciada.")

    # Detener o reiniciar temporizador
    if st.sidebar.button("🛑 Detener Subasta"):
        st.session_state.subasta_activa = False
        st.session_state.hora_fin_subasta = None
        st.sidebar.warning("Subasta pausada.")

    # Pasar al siguiente jugador de la lista
    if st.sidebar.button("➡️ Siguiente Jugador"):
        if st.session_state.jugador_actual_idx + 1 < len(JUGADORES_DISPONIBLES):
            st.session_state.jugador_actual_idx += 1
            jugador = JUGADORES_DISPONIBLES[st.session_state.jugador_actual_idx]
            st.session_state.puja_actual = jugador["precio"]
            st.session_state.postor_actual = "Nadie"
            st.sidebar.info(f"Cambiado a: {jugador['nombre']}")
        else:
            st.sidebar.error("No hay más jugadores en la lista.")

# --- VISTA PRINCIPAL DE LA SUBASTA ---
st.title("🔥 Subasta Abierta")

jugador_actual = JUGADORES_DISPONIBLES[st.session_state.jugador_actual_idx]

st.markdown(f"### Jugador: **{jugador_actual['nombre']}** ({jugador_actual['pos']} - GRL {jugador_actual['grl']})")

# Visualización del Reloj / Temporizador de 1 hora
if st.session_state.subasta_activa and st.session_state.hora_fin_subasta:
    tiempo_restante = st.session_state.hora_fin_subasta - datetime.datetime.now()
    
    if tiempo_restante.total_seconds() > 0:
        m, s = divmod(int(tiempo_restante.total_seconds()), 60)
        h, m = divmod(m, 60)
        st.metric("⏳ Tiempo restante de subasta:", f"{h:02d}:{m:02d}:{s:02d}")
    else:
        st.session_state.subasta_activa = False
        st.error("🚨 ¡Tiempo agotado! La subasta ha finalizado.")
else:
    st.warning("La subasta se encuentra pausada por el administrador.")

st.write(f"**Puja Actual:** {st.session_state.puja_actual:,} € por **{st.session_state.postor_actual}**")

st.divider()

# --- MÓDULO PARA PUJAR ---
st.subheader("Hacer una Puja")
col1, col2 = st.columns([2, 1])

with col1:
    nombre_equipo = st.text_input("Nombre de tu Equipo:")
    monto_puja = st.number_input(
        "Monto a pujar (€):", 
        min_value=st.session_state.puja_actual + 1000000, 
        step=1000000,
        value=st.session_state.puja_actual + 1000000
    )

with col2:
    st.write(" ")
    st.write(" ")
    if st.button("Enviar Puja"):
        if not st.session_state.subasta_activa:
            st.error("No puedes pujar mientras la subasta esté pausada.")
        elif not nombre_equipo:
            st.error("Escribe el nombre de tu equipo para pujar.")
        elif monto_puja > st.session_state.puja_actual:
            st.session_state.puja_actual = monto_puja
            st.session_state.postor_actual = nombre_equipo
            st.success(f"¡Puja registrada exitosamente por {nombre_equipo}!")
            st.rerun()
