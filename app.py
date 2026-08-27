import streamlit as st
import random
import json
import os

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
        self.password = str(pin_predeterminado)  # PIN por defecto (1 al 12)
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

    def calcular_media_equipo(self):
        if not self.plantilla:
            return 60
        return sum(j.grl for j in self.plantilla) // len(self.plantilla)

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

# --- FUNCIONES DE PERSISTENCIA ---
def guardar_partida():
    data = {
        "jornada_actual": st.session_state.jornada_actual,
        "historial_resultados": st.session_state.historial_resultados,
        "equipos": [e.to_dict() for e in st.session_state.equipos],
        "mercado_pool": [j.to_dict() for j in st.session_state.mercado_pool],
        "subasta_idx": st.session_state.subasta_idx,
        "puja_max": st.session_state.puja_max,
        "lider_puja_nombre": st.session_state.lider_puja_eq.nombre if st.session_state.lider_puja_eq else None
    }
    with open(ARCHIVO_GUARDADO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def cargar_partida():
    if os.path.exists(ARCHIVO_GUARDADO):
        with open(ARCHIVO_GUARDADO, "r", encoding="utf-8") as f:
            data = json.load(f)
        st.session_state.jornada_actual = data["jornada_actual"]
        st.session_state.historial_resultados = data["historial_resultados"]
        st.session_state.equipos = [Equipo.from_dict(e) for e in data["equipos"]]
        st.session_state.mercado_pool = [Jugador.from_dict(j) for j in data["mercado_pool"]]
        st.session_state.subasta_idx = data["subasta_idx"]
        st.session_state.puja_max = data["puja_max"]
        
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

        # Lista de 12 equipos asignando un PIN del 1 al 12
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
        
        # Selección de club de la lista
        eq_login_nombre = st.selectbox("Selecciona tu Club:", [f"Nº {e.id_club} | {e.emoji} {e.nombre}" for e in st.session_state.equipos])
        
        # Nombre opcional para personalizar la firma del presidente
        nombre_presi_input = st.text_input("Tu Nombre de Presidente (Opcional):")
        
        # Entrada de Clave PIN
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

# --- BARRA LATERAL Y BOTÓN DE CERRAR SESIÓN ---
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
            "Media GRL": eq.calcular_media_equipo()
        })
    st.table(datos)

# 2. MI PLANTILLA
elif menu == "📋 Mi Plantilla":
    mi_eq = st.session_state.mi_equipo
    st.header(f"Plantilla de {mi_eq.nombre}")
    p_datos = [{"Nombre": j.nombre, "Posición": j.posicion, "Media GRL": j.grl, "Valor": f"{j.valor_base:,} €"} for j in mi_eq.plantilla]
    st.table(p_datos)

# 3. SUBASTAS
elif menu == "🔥 Subastas":
    st.header("🔥 Subasta Abierta")
    j_actual = st.session_state.subasta_actual
    lider_nombre = st.session_state.lider_puja_eq.nombre if st.session_state.lider_puja_eq else "Nadie"
    
    st.write(f"Jugador: **{j_actual.nombre}** ({j_actual.posicion} - GRL {j_actual.grl})")
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

# 4. RESULTADOS
elif menu == "⚽ Resultados":
    st.header("⚽ Historial de Partidos")
    if st.session_state.historial_resultados:
        for j_num, res in reversed(st.session_state.historial_resultados):
            with st.expander(f"Jornada {j_num}"):
                for match in res:
                    st.write(match)
    else:
        st.info("Aún no hay partidos simulados.")

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
        tab1, tab2, tab3 = st.tabs(["⚽ Partidos & Mercado", "💰 Gestor Financiero", "🛠️ Modificar Stats & PINs"])

        # TAB 1: SIMULAR Y MERCADO
        with tab1:
            st.subheader(f"Simular Jornada {st.session_state.jornada_actual}")
            if st.session_state.jornada_actual <= 11:
                if st.button("🚀 Simular Todos los Partidos"):
                    equipos_shuffled = st.session_state.equipos.copy()
                    random.shuffle(equipos_shuffled)
                    
                    res_jornada = []
                    for i in range(0, len(equipos_shuffled), 2):
                        local = equipos_shuffled[i]
                        visitante = equipos_shuffled[i+1]
                        
                        diff = (local.calcular_media_equipo() - visitante.calcular_media_equipo()) / 8.0
                        gl = max(0, int(random.gauss(1.6 + diff, 1.2)))
                        gv = max(0, int(random.gauss(1.1 - diff, 1.2)))
                        
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
                            
                        res_jornada.append(f"{local.emoji} {local.nombre} **{gl} - {gv}** {visitante.nombre} {visitante.emoji}")
                    
                    st.session_state.historial_resultados.append((st.session_state.jornada_actual, res_jornada))
                    st.session_state.jornada_actual += 1
                    guardar_partida()
                    st.success("¡Jornada simulada y guardada!")
                    st.rerun()
            else:
                st.info("Temporada regular completada.")

            st.markdown("---")
            st.subheader("🔨 Control de Subastas")
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
                guardar_partida()
                st.rerun()

        # TAB 2: INYECTAR / QUITAR DINERO Y RESTABLECER
        with tab2:
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

        # TAB 3: MODIFICAR PUNTOS Y PINS
        with tab3:
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
