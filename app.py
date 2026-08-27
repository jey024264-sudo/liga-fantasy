import streamlit as st
import random
import json
import os
import datetime

st.set_page_config(page_title="Liga Manager Fantasy", page_icon="⚽", layout="wide")

PRESUPUESTO_INICIAL = 200_000_000
CLAVE_ADMIN = "1234"
ARCHIVO_GUARDADO = "liga_estado.json"

class Jugador:
    def __init__(self, nombre, posicion, grl, valor_base):
        self.nombre = nombre
        self.posicion = posicion
        self.grl = grl
        self.valor_base = valor_base

    def to_dict(self):
        return {"nombre": self.nombre, "posicion": self.posicion, "grl": self.grl, "valor_base": self.valor_base}

    @classmethod
    def from_dict(cls, d):
        return cls(d["nombre"], d["posicion"], d["grl"], d["valor_base"])

class Equipo:
    def __init__(self, id_club, nombre, emoji, pin_predeterminado):
        self.id_club = id_club
        self.nombre = nombre
        self.emoji = emoji
        self.presidente = f"Presidente Club {id_club}"
        self.password = str(pin_predeterminado)
        self.es_humano = True
        self.presupuesto = PRESUPUESTO_INICIAL
        self.plantilla = []
        self.puntos = 0
        self.pj = 0
        self.pg = 0
        self.pe = 0
        self.pp = 0
        self.gf = 0
        self.gc = 0

    @property
    def dg(self):
        return self.gf - self.gc

    def obtener_titulares_validos(self):
        key_titulares = f"titulares_{self.id_club}"
        if key_titulares in st.session_state and st.session_state[key_titulares]:
            nombres_titulares = st.session_state[key_titulares]
            titulares = [j for j in self.plantilla if j.nombre in nombres_titulares]
            if len(titulares) == 11:
                return titulares
        mejores = []
        for pos in ["POR", "DEF", "DEF", "DEF", "DEF", "MED", "MED", "MED", "DEL", "DEL", "DEL"]:
            candidatos = [j for j in self.plantilla if j.posicion == pos and j not in mejores]
            if candidatos:
                candidatos.sort(key=lambda x: x.grl, reverse=True)
                mejores.append(candidatos[0])
            else:
                restantes = [j for j in self.plantilla if j not in mejores]
                if restantes:
                    restantes.sort(key=lambda x: x.grl, reverse=True)
                    mejores.append(restantes[0])
        return mejores

    def calcular_media_equipo(self):
        titulares = self.obtener_titulares_validos()
        if not titulares:
            return 60
        media_base = sum(j.grl for j in titulares) // len(titulares)
        if len(titulares) < 11:
            media_base -= (11 - len(titulares)) * 5
        return max(40, media_base)

    def to_dict(self):
        return {
            "id_club": self.id_club,
            "nombre": self.nombre, "emoji": self.emoji, "presidente": self.presidente,
            "password": self.password, "es_humano": self.es_humano, "presupuesto": self.presupuesto,
            "plantilla": [j.to_dict() for j in self.plantilla],
            "puntos": self.puntos, "pj": self.pj, "pg": self.pg, "pe": self.pe,
            "pp": self.pp, "gf": self.gf, "gc": self.gc
        }

    @classmethod
    def from_dict(cls, d):
        eq = cls(d.get("id_club", 1), d["nombre"], d["emoji"], d.get("password", "1"))
        eq.presidente = d["presidente"]
        eq.password = d.get("password", str(d.get("id_club", 1)))
        eq.es_humano = d.get("es_humano", True)
        eq.presupuesto = d["presupuesto"]
        eq.plantilla = [Jugador.from_dict(j) for j in d["plantilla"]]
        eq.puntos = d["puntos"]
        eq.pj = d["pj"]
        eq.pg = d["pg"]
        eq.pe = d["pe"]
        eq.pp = d["pp"]
        eq.gf = d["gf"]
        eq.gc = d["gc"]
        return eq

# --- FUNCIONES DE SIMULACIÓN DIRECTA ---
def simular_partido_eliminatorio(eq1_nom, media1, eq2_nom, media2):
    diferencia = media1 - media2
    esp1 = max(0.5, 1.4 + (diferencia / 10.0))
    esp2 = max(0.5, 1.4 - (diferencia / 10.0))
    
    g1 = max(0, int(random.gauss(esp1, 0.9)))
    g2 = max(0, int(random.gauss(esp2, 0.9)))
    
    if g1 == g2:
        pen1, pen2 = 0, 0
        while pen1 == pen2:
            pen1 = random.randint(3, 5)
            pen2 = random.randint(3, 5)
        ganador = eq1_nom if pen1 > pen2 else eq2_nom
        res_str = f"{eq1_nom} **{g1} - {g2}** {eq2_nom} *(Penaltis: {pen1}-{pen2})*"
        return ganador, res_str
    else:
        ganador = eq1_nom if g1 > g2 else eq2_nom
        res_str = f"{eq1_nom} **{g1} - {g2}** {eq2_nom}"
        return ganador, res_str

# --- FUNCIONES DE PERSISTENCIA ---
def guardar_partida():
    # Guardamos únicamente el NOMBRE del campeón de copa en lugar del objeto
    campeon_nombre = None
    if st.session_state.get("campeon_copa"):
        campeon_nombre = st.session_state.campeon_copa.nombre if isinstance(st.session_state.campeon_copa, Equipo) else st.session_state.campeon_copa

    data = {
        "jornada_actual": st.session_state.jornada_actual,
        "historial_resultados": st.session_state.historial_resultados,
        "historial_copas": st.session_state.get("historial_copas", []),
        "historial_mundial": st.session_state.get("historial_mundial", []),
        "campeon_copa": campeon_nombre,
        "equipos": [e.to_dict() for e in st.session_state.equipos],
        "mercado_pool": [j.to_dict() for j in st.session_state.mercado_pool],
        "subasta_idx": st.session_state.subasta_idx,
        "puja_max": st.session_state.puja_max,
        "lider_puja_nombre": st.session_state.lider_puja_eq.nombre if st.session_state.lider_puja_eq else None,
        "subasta_activa": st.session_state.get("subasta_activa", False),
        "hora_fin_subasta": st.session_state.hora_fin_subasta.isoformat() if st.session_state.get("hora_fin_subasta") else None
    }
    with open(ARCHIVO_GUARDADO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def cargar_partida():
    if os.path.exists(ARCHIVO_GUARDADO):
        with open(ARCHIVO_GUARDADO, "r", encoding="utf-8") as f:
            data = json.load(f)
        st.session_state.jornada_actual = data["jornada_actual"]
        st.session_state.historial_resultados = data["historial_resultados"]
        st.session_state.historial_copas = data.get("historial_copas", [])
        st.session_state.historial_mundial = data.get("historial_mundial", [])
        st.session_state.equipos = [Equipo.from_dict(e) for e in data["equipos"]]
        
        # Recuperar objeto Campeón de Copa desde su nombre
        camp_nom = data.get("campeon_copa")
        if camp_nom:
            st.session_state.campeon_copa = next((e for e in st.session_state.equipos if e.nombre == camp_nom), None)
        else:
            st.session_state.campeon_copa = None

        st.session_state.mercado_pool = [Jugador.from_dict(j) for j in data["mercado_pool"]]
        st.session_state.subasta_idx = data["subasta_idx"]
        st.session_state.puja_max = data["puja_max"]
        st.session_state.subasta_activa = data.get("subasta_activa", False)
        
        if data.get("hora_fin_subasta"):
            st.session_state.hora_fin_subasta = datetime.datetime.fromisoformat(data["hora_fin_subasta"])
        else:
            st.session_state.hora_fin_subasta = None

        lider_nom = data["lider_puja_nombre"]
        if lider_nom:
            st.session_state.lider_puja_eq = next((e for e in st.session_state.equipos if e.nombre == lider_nom), None)
        else:
            st.session_state.lider_puja_eq = None
            
        st.session_state.subasta_actual = st.session_state.mercado_pool[st.session_state.subasta_idx]
        st.session_state.liga_inicializada = True
        return True
    return False

# --- INICIALIZACIÓN ---
if "liga_inicializada" not in st.session_state:
    if not cargar_partida():
        NOMBRES = ["Aarón", "Beto", "Carlos", "Damián", "Enzo", "Franco", "Gael", "Hugo", "Iker", "Javier"]
        APELLIDOS = ["Roca", "Soto", "Vidal", "Blanco", "Cruz", "Navarro", "Peña", "Mora", "Rios", "Vega"]
        POSICIONES = ["POR", "DEF", "DEF", "DEF", "MED", "MED", "MED", "DEL", "DEL", "DEL"]

        def generar_plantilla_base():
            return [Jugador(f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}", pos, random.randint(60, 75), random.randint(60, 75) * 100_000) for pos in POSICIONES]

        clubes_info = [
            (1, "Hunter x Hunter", "⚡"),
            (2, "Garra Oscura", "🖤"),
            (3, "Zaragoza Thunder", "⚡"),
            (4, "Kaiser FC", "👑"),
            (5, "JD Spider", "🕷️"),
            (6, "Z.Z.C FC", "🟡"),
            (7, "RJ Brasilia", "🇧🇷"),
            (8, "Talento Bonda", "🔥"),
            (9, "Legends FC", "🦁"),
            (10, "Phantom FC", "👻"),
            (11, "Estrella de la Muerte", "💀"),
            (12, "AirBending FC", "💨")
        ]

        clubes = []
        for id_c, nom, emoji in clubes_info:
            eq = Equipo(id_c, nom, emoji, pin_predeterminado=id_c)
            eq.plantilla = generar_plantilla_base()
            clubes.append(eq)

        st.session_state.equipos = clubes
        st.session_state.jornada_actual = 1
        st.session_state.historial_resultados = []
        st.session_state.historial_copas = []
        st.session_state.historial_mundial = []
        st.session_state.campeon_copa = None
        st.session_state.mercado_pool = [
            Jugador("Kylian Mbappé", "DEL", 91, 180_000_000),
            Jugador("Erling Haaland", "DEL", 91, 180_000_000),
            Jugador("Jude Bellingham", "MED", 90, 150_000_000),
            Jugador("Vinícius Jr.", "DEL", 90, 150_000_000),
            Jugador("Lamine Yamal", "DEL", 88, 120_000_000),
            Jugador("Pedri", "MED", 86, 80_000_000),
            Jugador("Federico Valverde", "MED", 88, 100_000_000),
            Jugador("Thibaut Courtois", "POR", 89, 45_000_000),
            Jugador("Virgil van Dijk", "DEF", 89, 50_000_000),
            Jugador("William Saliba", "DEF", 87, 80_000_000)
        ]
        st.session_state.subasta_idx = 0
        st.session_state.subasta_actual = st.session_state.mercado_pool[0]
        st.session_state.puja_max = st.session_state.mercado_pool[0].valor_base
        st.session_state.lider_puja_eq = None
        st.session_state.subasta_activa = False
        st.session_state.hora_fin_subasta = None
        st.session_state.liga_inicializada = True
        guardar_partida()

if "es_admin_autenticado" not in st.session_state:
    st.session_state.es_admin_autenticado = False
if "es_solo_admin" not in st.session_state:
    st.session_state.es_solo_admin = False

# --- SELECCIÓN DE ROL / EQUIPO ---
if "mi_equipo" not in st.session_state and not st.session_state.es_solo_admin:
    st.title("🎮 Portal de Acceso a la Liga")
    
    col_jugador, col_admin = st.columns(2)

    with col_jugador:
        st.subheader("Acceso a Clubes (PIN 1 - 12)")
        eq_login_nombre = st.selectbox("Selecciona tu Club:", [f"Nº {e.id_club} | {e.emoji} {e.nombre}" for e in st.session_state.equipos])
        nombre_presi_input = st.text_input("Tu Nombre de Presidente (Opcional):")
        pwd_login = st.text_input("PIN de Acceso del Club (del 1 al 12 por defecto):", type="password", key="pwd_club_login")
        
        if st.button("Ingresar al Club"):
            eq_obj = next(e for e in st.session_state.equipos if f"Nº {e.id_club} | {e.emoji} {e.nombre}" == eq_login_nombre)
            if pwd_login.strip() == str(eq_obj.password):
                if nombre_presi_input.strip():
                    eq_obj.presidente = nombre_presi_input.strip()
                    guardar_partida()
                st.session_state.mi_equipo = eq_obj
                st.success(f"¡Acceso concedido a {eq_obj.nombre}!")
                st.rerun()
            else:
                st.error("PIN de acceso incorrecto.")

    with col_admin:
        st.subheader("Acceso Administrador Supremo")
        pwd = st.text_input("Clave de Administrador:", type="password", key="pwd_admin_main")
        if st.button("Entrar como Administrador"):
            if pwd == CLAVE_ADMIN:
                st.session_state.es_solo_admin = True
                st.session_state.es_admin_autenticado = True
                st.success("¡Bienvenido, Administrador Supremo!")
                st.rerun()
            else:
                st.error("Clave incorrecta.")

    st.stop()

# --- RECONECTAR MI EQUIPO SI SE RECARGA LA PÁGINA ---
if not st.session_state.es_solo_admin and "mi_equipo" in st.session_state:
    nombre_actual = st.session_state.mi_equipo.nombre
    st.session_state.mi_equipo = next(e for e in st.session_state.equipos if e.nombre == nombre_actual)

# --- BARRA LATERAL ---
if st.session_state.es_solo_admin:
    st.sidebar.title("👑 Administrador")
    st.sidebar.write("Rol: **Comisionado Supremo**")
else:
    mi_eq = st.session_state.mi_equipo
    st.sidebar.title(f"👤 {mi_eq.presidente}")
    st.sidebar.write(f"Club Nº {mi_eq.id_club}: **{mi_eq.emoji} {mi_eq.nombre}**")
    st.sidebar.write(f"Presupuesto: **{mi_eq.presupuesto:,} €**")

st.sidebar.write(f"Jornada Actual: **{st.session_state.jornada_actual} / 11**")

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Salir / Cerrar Sesión"):
    if "mi_equipo" in st.session_state:
        del st.session_state["mi_equipo"]
    st.session_state.es_solo_admin = False
    st.session_state.es_admin_autenticado = False
    st.rerun()

opciones_menu = ["📊 Clasificación", "🔥 Subastas", "⚽ Resultados", "⚡ Pro Admin"]
if not st.session_state.es_solo_admin:
    opciones_menu.insert(1, "📋 Mi Plantilla")

menu = st.sidebar.radio("Navegación", opciones_menu)

# 1. TABLA DE CLASIFICACIÓN
if menu == "📊 Clasificación":
    st.header("🏆 Tabla de Posiciones")
    datos = []
    ordenados = sorted(st.session_state.equipos, key=lambda x: (x.puntos, x.dg, x.gf), reverse=True)
    for idx, eq in enumerate(ordenados, 1):
        zona = "🏆 Copa España" if idx <= 4 else ""
        datos.append({
            "Pos": idx,
            "Nº PIN": eq.id_club,
            "Club": f"{eq.emoji} {eq.nombre}",
            "Presidente": eq.presidente,
            "Pts": eq.puntos,
            "PJ": eq.pj,
            "PG": eq.pg,
            "PE": eq.pe,
            "PP": eq.pp,
            "GF": eq.gf,
            "GC": eq.gc,
            "DG": eq.dg,
            "Presupuesto": f"{eq.presupuesto:,} €",
            "Media 11": eq.calcular_media_equipo(),
            "Clasificación": zona
        })
    st.table(datos)

# 2. MI PLANTILLA Y GESTIÓN TÁCTICA
elif menu == "📋 Mi Plantilla":
    mi_eq = st.session_state.mi_equipo
    st.header(f"🛡️ Gestión Táctica y Plantilla - {mi_eq.nombre}")

    TACTICAS = {
        "4-3-3": ["POR", "DEF", "DEF", "DEF", "DEF", "MED", "MED", "MED", "DEL", "DEL", "DEL"],
        "4-4-2": ["POR", "DEF", "DEF", "DEF", "DEF", "MED", "MED", "MED", "MED", "DEL", "DEL"],
        "3-5-2": ["POR", "DEF", "DEF", "DEF", "MED", "MED", "MED", "MED", "MED", "DEL", "DEL"],
        "5-3-2": ["POR", "DEF", "DEF", "DEF", "DEF", "DEF", "MED", "MED", "MED", "DEL", "DEL"]
    }

    if f"esquema_{mi_eq.id_club}" not in st.session_state:
        st.session_state[f"esquema_{mi_eq.id_club}"] = "4-3-3"

    col_esquema, col_vacio = st.columns([1, 2])
    with col_esquema:
        esquema_sel = st.selectbox(
            "📐 Esquema Táctico:", 
            list(TACTICAS.keys()), 
            index=list(TACTICAS.keys()).index(st.session_state[f"esquema_{mi_eq.id_club}"])
        )
        st.session_state[f"esquema_{mi_eq.id_club}"] = esquema_sel

    posiciones_requeridas = TACTICAS[esquema_sel]
    key_titulares = f"titulares_{mi_eq.id_club}"

    titulares_previos = st.session_state.get(key_titulares, [])
    
    st.subheader("⚽ Selección del 11 Titular")
    
    dict_jugadores = {f"{j.nombre} ({j.posicion} - {j.grl} GRL)": j for j in mi_eq.plantilla}
    
    nuevos_titulares_nombres = []
    cols = st.columns(3)
    
    for idx, pos_req in enumerate(posiciones_requeridas):
        col = cols[idx % 3]
        
        candidatos_pos = [j for j in mi_eq.plantilla if j.posicion == pos_req]
        disponibles_objs = [j for j in candidatos_pos if j.nombre not in nuevos_titulares_nombres]

        if not disponibles_objs:
            disponibles_objs = [j for j in mi_eq.plantilla if j.nombre not in nuevos_titulares_nombres]

        if not disponibles_objs:
            disponibles_objs = mi_eq.plantilla

        opciones_etiquetas = [f"{j.nombre} ({j.posicion} - {j.grl} GRL)" for j in disponibles_objs]

        predeterminada_etiqueta = opciones_etiquetas[0]
        if idx < len(titulares_previos):
            nombre_previo = titulares_previos[idx]
            match_etiqueta = next((etq for etq in opciones_etiquetas if dict_jugadores[etq].nombre == nombre_previo), None)
            if match_etiqueta:
                predeterminada_etiqueta = match_etiqueta

        opcion_elegida_etiqueta = col.selectbox(
            f"Puesto {idx+1} ({pos_req}):",
            options=opciones_etiquetas,
            index=opciones_etiquetas.index(predeterminada_etiqueta),
            key=f"slot_{mi_eq.id_club}_{idx}"
        )
        
        jugador_seleccionado = dict_jugadores[opcion_elegida_etiqueta]
        nuevos_titulares_nombres.append(jugador_seleccionado.nombre)

    st.session_state[key_titulares] = nuevos_titulares_nombres

    media_titulares = mi_eq.calcular_media_equipo()

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Media 11 Titular", f"{media_titulares} ⭐️")
    c2.metric("Jugadores En Plantilla", len(mi_eq.plantilla))
    c3.metric("Valor Total del Club", f"{sum(j.valor_base for j in mi_eq.plantilla):,} €")

    st.subheader("📋 Lista de Jugadores")
    datos_plantilla = [
        {
            "Rol": "🟢 Titular" if j.nombre in nuevos_titulares_nombres else "⚪️ Suplente",
            "Jugador": j.nombre,
            "Posición": j.posicion,
            "Media GRL": j.grl,
            "Valor de Mercado": j.valor_base
        }
        for j in mi_eq.plantilla
    ]

    st.dataframe(
        datos_plantilla,
        column_config={
            "Rol": st.column_config.TextColumn("Estado", width="small"),
            "Jugador": st.column_config.TextColumn("Nombre del Jugador"),
            "Posición": st.column_config.TextColumn("Posición", width="small"),
            "Media GRL": st.column_config.ProgressColumn("Media (GRL)", format="%d", min_value=50, max_value=99),
            "Valor de Mercado": st.column_config.NumberColumn("Valor (€)", format="%d €")
        },
        hide_index=True,
        use_container_width=True
    )

# 3. SUBASTAS
elif menu == "🔥 Subastas":
    st.header("🔥 Subasta Abierta")
    j_actual = st.session_state.subasta_actual
    lider_nombre = st.session_state.lider_puja_eq.nombre if st.session_state.lider_puja_eq else "Nadie"
    
    st.write(f"Jugador: **{j_actual.nombre}** ({j_actual.posicion} - GRL {j_actual.grl})")
    
    if st.session_state.get("subasta_activa") and st.session_state.get("hora_fin_subasta"):
        tiempo_restante = st.session_state.hora_fin_subasta - datetime.datetime.now()
        if tiempo_restante.total_seconds() > 0:
            m, s = divmod(int(tiempo_restante.total_seconds()), 60)
            h, m = divmod(m, 60)
            st.metric("⏳ Tiempo restante:", f"{h:02d}:{m:02d}:{s:02d}")
        else:
            st.session_state.subasta_activa = False
            st.error("🚨 ¡Tiempo agotado! Esperando cierre de subasta por el Administrador.")
    else:
        st.info("⏸️ Subasta actualmente en pausa o sin temporizador activo.")

    st.write(f"Puja Actual: **{st.session_state.puja_max:,} €** por **{lider_nombre}**")
    
    if not st.session_state.es_solo_admin:
        mi_eq = st.session_state.mi_equipo
        monto = st.number_input("Oferta (€)", min_value=st.session_state.puja_max + 1_000_000, step=1_000_000)
        if st.button("Pujar"):
            if monto <= mi_eq.presupuesto:
                st.session_state.puja_max = monto
                st.session_state.lider_puja_eq = mi_eq
                guardar_partida()
                st.success("¡Puja registrada correctamente!")
                st.rerun()
            else:
                st.error("No tienes suficiente dinero.")

# 4. RESULTADOS DE PARTIDOS Y TORNEOS
elif menu == "⚽ Resultados":
    st.header("⚽ Historial General de Competiciones")
    
    tab_liga, tab_copa, tab_mundial = st.tabs(["🏆 Liga", "🇪🇸 Copa de España", "🌍 Mundial de Clubes"])

    with tab_liga:
        if st.session_state.historial_resultados:
            for j_num, res in reversed(st.session_state.historial_resultados):
                with st.expander(f"Jornada {j_num}"):
                    for match in res:
                        st.write(match)
        else:
            st.info("Aún no hay partidos de Liga simulados.")

    with tab_copa:
        if st.session_state.get("historial_copas"):
            for res in st.session_state.historial_copas:
                st.markdown(res)
        else:
            st.info("La Copa de España aún no se ha disputado esta temporada.")

    with tab_mundial:
        if st.session_state.get("historial_mundial"):
            for res in st.session_state.historial_mundial:
                st.markdown(res)
        else:
            st.info("El Mundial de Clubes se jugará cuando haya un Campeón de Copa de España.")

# 5. PANEL PRO ADMIN
elif menu == "⚡ Pro Admin":
    st.header("⚡ Panel de Control Pro Admin")
    
    if not st.session_state.es_admin_autenticado:
        pwd = st.text_input("Clave de Administrador:", type="password", key="pwd_admin_panel")
        if st.button("Autenticar"):
            if pwd == CLAVE_ADMIN:
                st.session_state.es_admin_autenticado = True
                st.success("¡Acceso concedido!")
                st.rerun()
            else:
                st.error("Clave incorrecta.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["⚽ Partidos & Mercado", "🏆 Torneos Post-Liga", "💰 Gestor Financiero", "🛠️ Modificar Stats & PINs"])

        with tab1:
            st.subheader(f"Simular Jornada {st.session_state.jornada_actual}")
            if st.session_state.jornada_actual <= 11:
                if st.button("🚀 Simular Partidos (Basado en Plantillas)"):
                    equipos_shuffled = st.session_state.equipos.copy()
                    random.shuffle(equipos_shuffled)
                    
                    res_jornada = []
                    for i in range(0, len(equipos_shuffled), 2):
                        local = equipos_shuffled[i]
                        visitante = equipos_shuffled[i+1]
                        
                        media_loc = local.calcular_media_equipo()
                        media_vis = visitante.calcular_media_equipo()
                        
                        diferencia_grl = (media_loc + 3) - media_vis
                        esperanza_loc = max(0.5, 1.5 + (diferencia_grl / 10.0))
                        esperanza_vis = max(0.3, 1.1 - (diferencia_grl / 10.0))
                        
                        gl = max(0, int(random.gauss(esperanza_loc, 0.9)))
                        gv = max(0, int(random.gauss(esperanza_vis, 0.9)))
                        
                        local.pj += 1
                        visitante.pj += 1
                        local.gf += gl
                        local.gc += gv
                        visitante.gf += gv
                        visitante.gc += gl
                        
                        if gl > gv:
                            local.puntos += 3
                            local.pg += 1
                            visitante.pp += 1
                        elif gv > gl:
                            visitante.puntos += 3
                            visitante.pg += 1
                            local.pp += 1
                        else:
                            local.puntos += 1
                            visitante.puntos += 1
                            local.pe += 1
                            visitante.pe += 1
                            
                        res_jornada.append(f"{local.emoji} {local.nombre} ({media_loc} GRL) **{gl} - {gv}** ({media_vis} GRL) {visitante.nombre} {visitante.emoji}")
                    
                    st.session_state.historial_resultados.append((st.session_state.jornada_actual, res_jornada))
                    st.session_state.jornada_actual += 1
                    guardar_partida()
                    st.success("¡Jornada simulada comparando las alineaciones de los equipos!")
                    st.rerun()
            else:
                st.info("Temporada regular completada.")

            st.markdown("---")
            st.subheader("🔨 Control de Subastas & Temporizador")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("⏱️ Iniciar Temporizador (1 Hora)"):
                    st.session_state.hora_fin_subasta = datetime.datetime.now() + datetime.timedelta(hours=1)
                    st.session_state.subasta_activa = True
                    guardar_partida()
                    st.success("Reloj de 1 hora iniciado.")
                    st.rerun()

            with c2:
                if st.button("🛑 Pausar Temporizador"):
                    st.session_state.subasta_activa = False
                    st.session_state.hora_fin_subasta = None
                    guardar_partida()
                    st.warning("Temporizador detenido.")
                    st.rerun()

            st.write("")
            if st.button("Cerrar Subasta Actual y Adjudicar Jugador"):
                ganador = st.session_state.lider_puja_eq
                jugador = st.session_state.subasta_actual
                if ganador:
                    ganador.presupuesto -= st.session_state.puja_max
                    ganador.plantilla.append(jugador)
                    st.success(f"¡{jugador.nombre} ha sido transferido a {ganador.nombre} por {st.session_state.puja_max:,} €!")
                else:
                    st.warning("Nadie pujó por este jugador. Pasa al siguiente.")
                
                st.session_state.subasta_idx = (st.session_state.subasta_idx + 1) % len(st.session_state.mercado_pool)
                nuevo_j = st.session_state.mercado_pool[st.session_state.subasta_idx]
                st.session_state.subasta_actual = nuevo_j
                st.session_state.puja_max = nuevo_j.valor_base
                st.session_state.lider_puja_eq = None
                st.session_state.subasta_activa = False
                st.session_state.hora_fin_subasta = None
                guardar_partida()
                st.rerun()

        with tab2:
            st.subheader("🇪🇸 Copa de España (Top 4 de Liga)")
            
            if st.session_state.jornada_actual > 11:
                top4 = sorted(st.session_state.equipos, key=lambda x: (x.puntos, x.dg, x.gf), reverse=True)[:4]
                st.write("Equipos clasificados:")
                for i, eq in enumerate(top4, 1):
                    st.write(f"**{i}º** {eq.emoji} {eq.nombre} ({eq.calcular_media_equipo()} GRL)")
                
                if st.button("🏆 Simular Copa de España"):
                    st.session_state.historial_copas = []
                    
                    eq1, eq2, eq3, eq4 = top4[0], top4[1], top4[2], top4[3]
                    
                    gan_sf1, res_sf1 = simular_partido_eliminatorio(
                        f"{eq1.emoji} {eq1.nombre}", eq1.calcular_media_equipo(),
                        f"{eq4.emoji} {eq4.nombre}", eq4.calcular_media_equipo()
                    )
                    gan_sf2, res_sf2 = simular_partido_eliminatorio(
                        f"{eq2.emoji} {eq2.nombre}", eq2.calcular_media_equipo(),
                        f"{eq3.emoji} {eq3.nombre}", eq3.calcular_media_equipo()
                    )
                    
                    obj_gan1 = next(e for e in top4 if f"{e.emoji} {e.nombre}" == gan_sf1)
                    obj_gan2 = next(e for e in top4 if f"{e.emoji} {e.nombre}" == gan_sf2)
                    
                    gan_final, res_final = simular_partido_eliminatorio(
                        f"{obj_gan1.emoji} {obj_gan1.nombre}", obj_gan1.calcular_media_equipo(),
                        f"{obj_gan2.emoji} {obj_gan2.nombre}", obj_gan2.calcular_media_equipo()
                    )
                    
                    obj_campeon = next(e for e in top4 if f"{e.emoji} {e.nombre}" == gan_final)
                    st.session_state.campeon_copa = obj_campeon
                    
                    res_totales = [
                        "### 🥊 Semifinales",
                        f"- **Semifinal 1:** {res_sf1}",
                        f"- **Semifinal 2:** {res_sf2}",
                        "---",
                        "### 🏆 Gran Final",
                        f"- {res_final}",
                        f"\n🎉 **¡{obj_campeon.emoji} {obj_campeon.nombre} es el CAMPEÓN de la Copa de España!**"
                    ]
                    
                    st.session_state.historial_copas = res_totales
                    guardar_partida()
                    st.success("¡Copa de España simulada con éxito!")
                    st.rerun()
            else:
                st.warning("Aún no ha terminado la Liga regular (debes llegar a la Jornada 11).")

            st.markdown("---")
            st.subheader("🌍 Mundial de Clubes (Campeón de Copa vs Rivales Internacionales IA)")
            
            if st.session_state.get("campeon_copa"):
                champ = st.session_state.campeon_copa
                st.write(f"Representante de la Liga: **{champ.emoji} {champ.nombre}** ({champ.calcular_media_equipo()} GRL)")
                
                if st.button("👑 Simular Mundial de Clubes"):
                    PAISES_RIVALES = ["Japón 🇯🇵", "Brasil 🇧🇷", "Estados Unidos 🇺🇸", "Alemania 🇩🇪", "Inglaterra 🇬🇧", "Argentina 🇦🇷"]
                    NOMBRES_RIVALES = ["Sakura Dragons", "Samba Stars FC", "Liberty Strikers", "Bavaria United", "London Titans", "Pampa Express"]
                    
                    rivales = []
                    indices = random.sample(range(len(NOMBRES_RIVALES)), 3)
                    for idx in indices:
                        rivales.append({
                            "nombre": f"🌐 {NOMBRES_RIVALES[idx]} ({PAISES_RIVALES[idx]})",
                            "media": random.randint(75, 88)
                        })
                    
                    r1, r2, r3 = rivales[0], rivales[1], rivales[2]
                    
                    gan_sf1, res_sf1 = simular_partido_eliminatorio(
                        f"{champ.emoji} {champ.nombre}", champ.calcular_media_equipo(),
                        r1["nombre"], r1["media"]
                    )
                    gan_sf2, res_sf2 = simular_partido_eliminatorio(
                        r2["nombre"], r2["media"],
                        r3["nombre"], r3["media"]
                    )
                    
                    media_fin1 = champ.calcular_media_equipo() if gan_sf1 == f"{champ.emoji} {champ.nombre}" else next(r["media"] for r in rivales if r["nombre"] == gan_sf1)
                    media_fin2 = champ.calcular_media_equipo() if gan_sf2 == f"{champ.emoji} {champ.nombre}" else next(r["media"] for r in rivales if r["nombre"] == gan_sf2)
                    
                    gan_mundial, res_final = simular_partido_eliminatorio(gan_sf1, media_fin1, gan_sf2, media_fin2)
                    
                    res_mundial = [
                        "### 🥊 Semifinales Internacionales",
                        f"- **Semifinal 1:** {res_sf1}",
                        f"- **Semifinal 2:** {res_sf2}",
                        "---",
                        "### 👑 Gran Final del Mundial",
                        f"- {res_final}",
                        f"\n🌍 **¡{gan_mundial} se corona CAMPEÓN MUNDIAL DE CLUBES!**"
                    ]
                    
                    st.session_state.historial_mundial = res_mundial
                    guardar_partida()
                    st.success("¡Mundial de Clubes simulado con éxito!")
                    st.rerun()
            else:
                st.info("Para jugar el Mundial de Clubes primero se debe simular y obtener un Campeón en la Copa de España.")

        with tab3:
            st.subheader("💵 Inyección o Descuento de Presupuesto")
            eq_destino = st.selectbox("Selecciona el equipo:", [e.nombre for e in st.session_state.equipos])
            monto_cambio = st.number_input("Monto en € (positivo para dar, negativo para quitar):", step=5_000_000)
            
            if st.button("Aplicar Transacción"):
                for e in st.session_state.equipos:
                    if e.nombre == eq_destino:
                        e.presupuesto += monto_cambio
                        guardar_partida()
                        st.success(f"Nuevo presupuesto de {e.nombre}: {e.presupuesto:,} €")
                        st.rerun()

            st.markdown("---")
            st.subheader("🔄 Restablecer Presupuestos General")
            if st.button("Restablecer Todos los Presupuestos a 200M €"):
                for e in st.session_state.equipos:
                    e.presupuesto = PRESUPUESTO_INICIAL
                guardar_partida()
                st.success("¡Todos los presupuestos han sido restablecidos a 200.000.000 €!")
                st.rerun()

        with tab4:
            st.subheader("✏️ Edición de Puntos y Tabla")
            eq_edit = st.selectbox("Selecciona equipo a editar:", [e.nombre for e in st.session_state.equipos], key="edit_eq")
            equipo_obj = next(e for e in st.session_state.equipos if e.nombre == eq_edit)
            
            nuevos_pts = st.number_input("Puntos:", value=equipo_obj.puntos, min_value=0)
            nuevos_gf = st.number_input("Goles a Favor (GF):", value=equipo_obj.gf, min_value=0)
            nuevos_gc = st.number_input("Goles en Contra (GC):", value=equipo_obj.gc, min_value=0)
            nuevo_pin = st.text_input("PIN de Acceso:", value=str(equipo_obj.password))
            
            if st.button("Guardar Cambios del Equipo"):
                equipo_obj.puntos = nuevos_pts
                equipo_obj.gf = nuevos_gf
                equipo_obj.gc = nuevos_gc
                equipo_obj.password = nuevo_pin.strip()
                guardar_partida()
                st.success("¡Datos y PIN del equipo actualizados!")
                st.rerun()
