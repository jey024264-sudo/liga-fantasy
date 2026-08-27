import datetime
import json
import os
import random
import streamlit as st

st.set_page_config(
    page_title="Liga Manager Fantasy Beta 2.0 - IA Bots", page_icon="⚽", layout="wide"
)

PRESUPUESTO_INICIAL = 200_000_000
CLAVE_ADMIN = "1234"
ARCHIVO_GUARDADO = "liga_estado_beta2_bots.json"


class Jugador:

  def __init__(self, nombre, posicion, grl, valor_base):
    self.nombre = nombre
    self.posicion = posicion
    self.grl = grl
    self.valor_base = valor_base
    self.clausula = valor_base * 2
    self.salario = int(valor_base * 0.05)

  def to_dict(self):
    return {
        "nombre": self.nombre,
        "posicion": self.posicion,
        "grl": self.grl,
        "valor_base": self.valor_base,
        "clausula": self.clausula,
        "salario": self.salario,
    }

  @classmethod
  def from_dict(cls, d):
    j = cls(d["nombre"], d["posicion"], d["grl"], d["valor_base"])
    j.clausula = d.get("clausula", d["valor_base"] * 2)
    j.salario = d.get("salario", int(d["valor_base"] * 0.05))
    return j


class Equipo:

  def __init__(self, id_club, nombre, emoji, pin_predeterminado, es_humano=True):
    self.id_club = id_club
    self.nombre = nombre
    self.emoji = emoji
    self.presidente = f"Presidente Club {id_club}" if es_humano else f"🤖 Bot {nombre}"
    self.password = str(pin_predeterminado)
    self.es_humano = es_humano
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

  def calcular_salarios_totales(self):
    return sum(j.salario for j in self.plantilla)

  def obtener_titulares_validos(self):
    key_titulares = f"titulares_{self.id_club}"
    if key_titulares in st.session_state and st.session_state[key_titulares]:
      nombres_titulares = st.session_state[key_titulares]
      titulares = [j for j in self.plantilla if j.nombre in nombres_titulares]
      if len(titulares) == 11:
        return titulares
    mejores = []
    for pos in [
        "POR",
        "DEF",
        "DEF",
        "DEF",
        "DEF",
        "MED",
        "MED",
        "MED",
        "DEL",
        "DEL",
        "DEL",
    ]:
      candidatos = [
          j for j in self.plantilla if j.posicion == pos and j not in mejores
      ]
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
        "nombre": self.nombre,
        "emoji": self.emoji,
        "presidente": self.presidente,
        "password": self.password,
        "es_humano": self.es_humano,
        "presupuesto": self.presupuesto,
        "plantilla": [j.to_dict() for j in self.plantilla],
        "puntos": self.puntos,
        "pj": self.pj,
        "pg": self.pg,
        "pe": self.pe,
        "pp": self.pp,
        "gf": self.gf,
        "gc": self.gc,
    }

  @classmethod
  def from_dict(cls, d):
    eq = cls(
        d.get("id_club", 1),
        d["nombre"],
        d["emoji"],
        d.get("password", "1"),
        d.get("es_humano", True),
    )
    eq.presidente = d["presidente"]
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


# --- CEREBRO DE LAS IAs (BOTS AUTÓNOMOS) ---
def ejecutar_logica_bots():
  """Simula el comportamiento estratégico de los equipos controlados por IA."""
  bots = [e for e in st.session_state.equipos if not e.es_humano]
  if not bots:
    return

  mensajes_ia = []

  for bot in bots:
    if st.session_state.get("subasta_activa") and st.session_state.get("subasta_actual"):
      j_sub = st.session_state.subasta_actual
      if bot.presupuesto > st.session_state.puja_max + 2_000_000:
        if st.session_state.lider_puja_eq != bot and random.random() < 0.6:
          nueva_puja = st.session_state.puja_max + random.randint(1_000_000, 5_000_000)
          if nueva_puja <= bot.presupuesto:
            st.session_state.puja_max = nueva_puja
            st.session_state.lider_puja_eq = bot
            mensajes_ia.append(f"🤖 {bot.emoji} **{bot.nombre}** pujó {nueva_puja:,} € por {j_sub.nombre}.")

    if random.random() < 0.4:
      otros = [e for e in st.session_state.equipos if e.id_club != bot.id_club]
      if otros:
        objetivo_eq = random.choice(otros)
        if objetivo_eq.plantilla:
          candidato_j = max(objetivo_eq.plantilla, key=lambda x: x.grl)
          media_actual_bot = bot.calcular_media_equipo()
          if bot.presupuesto >= candidato_j.clausula and candidato_j.grl >= media_actual_bot:
            bot.presupuesto -= candidato_j.clausula
            objetivo_eq.presupuesto += candidato_j.clausula
            objetivo_eq.plantilla.remove(candidato_j)
            bot.plantilla.append(candidato_j)
            mensajes_ia.append(
                f"🚨 ¡Cláusula pagada! 🤖 **{bot.nombre}** pagó la cláusula de"
                f" **{candidato_j.nombre}** ({candidato_j.grl} GRL) a"
                f" {objetivo_eq.nombre} por {candidato_j.clausula:,} €."
            )


# --- FUNCIONES DE SIMULACIÓN Y PERSISTENCIA ---
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


def guardar_partida():
  campeon_nombre = (
      st.session_state.campeon_copa.nombre
      if hasattr(st.session_state.get("campeon_copa"), "nombre")
      else st.session_state.get("campeon_copa")
  )
  lider_nombre = (
      st.session_state.lider_puja_eq.nombre
      if hasattr(st.session_state.get("lider_puja_eq"), "nombre")
      else st.session_state.get("lider_puja_eq")
  )

  data = {
      "jornada_actual": st.session_state.jornada_actual,
      "historial_resultados": st.session_state.get("historial_resultados", []),
      "historial_copas": st.session_state.get("historial_copas", []),
      "historial_mundial": st.session_state.get("historial_mundial", []),
      "campeon_copa": campeon_nombre,
      "equipos": [e.to_dict() for e in st.session_state.equipos],
      "mercado_pool": [j.to_dict() for j in st.session_state.mercado_pool],
      "ofertas_fichaje": st.session_state.get("ofertas_fichaje", []),
      "subasta_idx": st.session_state.get("subasta_idx", 0),
      "puja_max": st.session_state.get("puja_max", 0),
      "lider_puja_nombre": lider_nombre,
      "subasta_activa": st.session_state.get("subasta_activa", False),
      "hora_fin_subasta": (
          st.session_state.hora_fin_subasta.isoformat()
          if st.session_state.get("hora_fin_subasta")
          else None
      ),
  }
  with open(ARCHIVO_GUARDADO, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4, default=str)


def cargar_partida():
  if os.path.exists(ARCHIVO_GUARDADO):
    try:
      with open(ARCHIVO_GUARDADO, "r", encoding="utf-8") as f:
        data = json.load(f)
      st.session_state.jornada_actual = data["jornada_actual"]
      st.session_state.historial_resultados = data["historial_resultados"]
      st.session_state.historial_copas = data.get("historial_copas", [])
      st.session_state.historial_mundial = data.get("historial_mundial", [])
      st.session_state.equipos = [Equipo.from_dict(e) for e in data["equipos"]]

      camp_nom = data.get("campeon_copa")
      st.session_state.campeon_copa = (
          next(
              (e for e in st.session_state.equipos if e.nombre == str(camp_nom)),
              None,
          )
          if camp_nom
          else None
      )

      st.session_state.mercado_pool = [
          Jugador.from_dict(j) for j in data["mercado_pool"]
      ]
      st.session_state.ofertas_fichaje = data.get("ofertas_fichaje", [])
      st.session_state.subasta_idx = data["subasta_idx"]
      st.session_state.puja_max = data["puja_max"]
      st.session_state.subasta_activa = data.get("subasta_activa", False)

      st.session_state.hora_fin_subasta = (
          datetime.datetime.fromisoformat(data["hora_fin_subasta"])
          if data.get("hora_fin_subasta")
          else None
      )
      lider_nom = data.get("lider_puja_nombre")
      st.session_state.lider_puja_eq = (
          next((e for e in st.session_state.equipos if e.nombre == lider_nom), None)
          if lider_nom
          else None
      )

      st.session_state.subasta_actual = st.session_state.mercado_pool[
          st.session_state.subasta_idx
      ]
      st.session_state.liga_inicializada = True
      return True
    except Exception:
      if os.path.exists(ARCHIVO_GUARDADO):
        os.remove(ARCHIVO_GUARDADO)
      return False
  return False


# --- INICIALIZACIÓN ---
if "liga_inicializada" not in st.session_state:
  if not cargar_partida():
    NOMBRES = ["Aarón", "Beto", "Carlos", "Damián", "Enzo", "Franco", "Gael", "Hugo", "Iker", "Javier"]
    APELLIDOS = ["Roca", "Soto", "Vidal", "Blanco", "Cruz", "Navarro", "Peña", "Mora", "Rios", "Vega"]
    POSICIONES = ["POR", "DEF", "DEF", "DEF", "MED", "MED", "MED", "DEL", "DEL", "DEL"]

    def generar_plantilla_base():
      return [
          Jugador(
              f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}",
              pos,
              random.randint(60, 75),
              random.randint(60, 75) * 100_000,
          )
          for pos in POSICIONES
      ]

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
        (12, "AirBending FC", "💨"),
    ]

    clubes = []
    for id_c, nom, emoji in clubes_info:
      es_humano = (id_c == 1)
      eq = Equipo(id_c, nom, emoji, pin_predeterminado=id_c, es_humano=es_humano)
      eq.plantilla = generar_plantilla_base()
      clubes.append(eq)

    st.session_state.equipos = clubes
    st.session_state.jornada_actual = 1
    st.session_state.historial_resultados = []
    st.session_state.historial_copas = []
    st.session_state.historial_mundial = []
    st.session_state.campeon_copa = None
    st.session_state.ofertas_fichaje = []
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
        Jugador("William Saliba", "DEF", 87, 80_000_000),
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

# --- PORTAL DE ACCESO ---
if "mi_equipo" not in st.session_state and not st.session_state.es_solo_admin:
  st.title("🎮 Portal de Acceso a la Liga - Beta 2.0 (Con Bots IA)")
  col_jugador, col_admin = st.columns(2)

  with col_jugador:
    st.subheader("Acceso a Clubes (PIN 1 - 12)")
    eq_login_nombre = st.selectbox(
        "Selecciona tu Club:",
        [f"Nº {e.id_club} | {e.emoji} {e.nombre} ({'Humano' if e.es_humano else '🤖 Bot'})" for e in st.session_state.equipos],
    )
    nombre_presi_input = st.text_input("Tu Nombre de Presidente (Opcional):")
    pwd_login = st.text_input("PIN de Acceso del Club:", type="password", key="pwd_club_login")

    if st.button("Ingresar al Club"):
      idx_SEL = [f"Nº {e.id_club} | {e.emoji} {e.nombre} ({'Humano' if e.es_humano else '🤖 Bot'})" for e in st.session_state.equipos].index(eq_login_nombre)
      eq_obj = st.session_state.equipos[idx_SEL]
      
      if pwd_login.strip() == str(eq_obj.password):
        eq_obj.es_humano = True
        if nombre_presi_input.strip():
          eq_obj.presidente = nombre_presi_input.strip()
        guardar_partida()
        st.session_state.mi_equipo = eq_obj
        st.success(f"¡Acceso concedido a {eq_obj.nombre}!")
        st.rerun()
      else:
        st.error("PIN incorrecto.")

  with col_admin:
    st.subheader("Acceso Administrador Supremo")
    pwd = st.text_input("Clave de Administrador:", type="password", key="pwd_admin_main")
    if st.button("Entrar como Administrador"):
      if pwd == CLAVE_ADMIN:
        st.session_state.es_solo_admin = True
        st.session_state.es_admin_autenticado = True
        st.success("¡Bienvenido, Comisionado!")
        st.rerun()
      else:
        st.error("Clave incorrecta.")
  st.stop()

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
  st.sidebar.write(f"Salarios Totales: **{mi_eq.calcular_salarios_totales():,} €**")

st.sidebar.write(f"Jornada Actual: **{st.session_state.jornada_actual} / 11**")
st.sidebar.markdown("---")

if st.sidebar.button("🚪 Salir / Cerrar Sesión"):
  if "mi_equipo" in st.session_state:
    del st.session_state["mi_equipo"]
  st.session_state.es_solo_admin = False
  st.session_state.es_admin_autenticado = False
  st.rerun()

opciones_menu = ["📊 Clasificación", "🔥 Subastas", "🤝 Mercado & Cláusulas", "⚽ Resultados", "⚡ Pro Admin"]
if not st.session_state.es_solo_admin:
  opciones_menu.insert(1, "📋 Mi Plantilla")

menu = st.sidebar.radio("Navegación", opciones_menu)

# 1. CLASIFICACIÓN
if menu == "📊 Clasificación":
  st.header("🏆 Tabla de Posiciones")
  datos = []
  ordenados = sorted(
      st.session_state.equipos,
      key=lambda x: (x.puntos, x.dg, x.gf),
      reverse=True,
  )
  for idx, eq in enumerate(ordenados, 1):
    zona = "🏆 Copa España" if idx <= 4 else ""
    tipo_cnt = "👤 Humano" if eq.es_humano else "🤖 Bot IA"
    datos.append({
        "Pos": idx,
        "Club": f"{eq.emoji} {eq.nombre}",
        "Control": tipo_cnt,
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
        "Salarios": f"{eq.calcular_salarios_totales():,} €",
        "Media 11": eq.calcular_media_equipo(),
        "Clasificación": zona,
    })
  st.table(datos)

# 2. MI PLANTILLA Y TÁCTICA
elif menu == "📋 Mi Plantilla":
  mi_eq = st.session_state.mi_equipo
  st.header(f"🛡️ Gestión Táctica y Plantilla - {mi_eq.nombre}")

  TACTICAS = {
      "4-3-3": ["POR", "DEF", "DEF", "DEF", "DEF", "MED", "MED", "MED", "DEL", "DEL", "DEL"],
      "4-4-2": ["POR", "DEF", "DEF", "DEF", "DEF", "MED", "MED", "MED", "MED", "DEL", "DEL"],
      "3-5-2": ["POR", "DEF", "DEF", "DEF", "MED", "MED", "MED", "MED", "MED", "DEL", "DEL"],
      "5-3-2": ["POR", "DEF", "DEF", "DEF", "DEF", "DEF", "MED", "MED", "MED", "DEL", "DEL"],
  }

  if f"esquema_{mi_eq.id_club}" not in st.session_state:
    st.session_state[f"esquema_{mi_eq.id_club}"] = "4-3-3"

  esquema_sel = st.selectbox(
      "📐 Esquema Táctico:",
      list(TACTICAS.keys()),
      index=list(TACTICAS.keys()).index(st.session_state[f"esquema_{mi_eq.id_club}"]),
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
        key=f"slot_{mi_eq.id_club}_{idx}",
    )
    nuevos_titulares_nombres.append(dict_jugadores[opcion_elegida_etiqueta].nombre)

  st.session_state[key_titulares] = nuevos_titulares_nombres
  media_titulares = mi_eq.calcular_media_equipo()

  st.markdown("---")
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Media 11 Titular", f"{media_titulares} ⭐️")
  c2.metric("Plantilla", len(mi_eq.plantilla))
  c3.metric("Salarios / Temp", f"{mi_eq.calcular_salarios_totales():,} €")
  c4.metric("Presupuesto", f"{mi_eq.presupuesto:,} €")

  st.subheader("📋 Detalle de Jugadores (Valor, Cláusula y Salario)")
  datos_plantilla = [
      {
          "Rol": "🟢 Titular" if j.nombre in nuevos_titulares_nombres else "⚪️ Suplente",
          "Jugador": j.nombre,
          "Posición": j.posicion,
          "Media": j.grl,
          "Valor": f"{j.valor_base:,} €",
          "Cláusula": f"{j.clausula:,} €",
          "Salario": f"{j.salario:,} €",
      }
      for j in mi_eq.plantilla
  ]
  st.dataframe(datos_plantilla, use_container_width=True, hide_index=True)

# 3. SUBASTAS
elif menu == "🔥 Subastas":
  st.header("🔥 Subasta Abierta (Con Actividad de Bots IA)")
  j_actual = st.session_state.subasta_actual
  lider_nombre = st.session_state.lider_puja_eq.nombre if st.session_state.lider_puja_eq else "Nadie"
  st.write(f"Jugador en Subasta: **{j_actual.nombre}** ({j_actual.posicion} - GRL {j_actual.grl})")

  ejecutar_logica_bots()

  if st.session_state.get("subasta_activa") and st.session_state.get("hora_fin_subasta"):
    tiempo_restante = st.session_state.hora_fin_subasta - datetime.datetime.now()
    if tiempo_restante.total_seconds() > 0:
      m, s = divmod(int(tiempo_restante.total_seconds()), 60)
      h, m = divmod(m, 60)
      st.metric("⏳ Tiempo restante:", f"{h:02d}:{m:02d}:{s:02d}")
    else:
      st.session_state.subasta_activa = False
      st.error("🚨 ¡Tiempo agotado!")
  else:
    st.info("⏸️ Subasta en pausa o sin reloj activo.")

  st.write(f"Puja Actual: **{st.session_state.puja_max:,} €** por **{lider_nombre}**")

  if not st.session_state.es_solo_admin:
    mi_eq = st.session_state.mi_equipo
    monto = st.number_input(
        "Tu Oferta (€)",
        min_value=st.session_state.puja_max + 1_000_000,
        step=1_000_000,
    )
    if st.button("Pujar en Subasta"):
      if monto <= mi_eq.presupuesto:
        st.session_state.puja_max = monto
        st.session_state.lider_puja_eq = mi_eq
        guardar_partida()
        st.success("¡Puja registrada!")
        st.rerun()
      else:
        st.error("No tienes suficiente presupuesto.")

# 4. MERCADO ENTRE CLUBES & CLÁUSULAS
elif menu == "🤝 Mercado & Cláusulas":
  st.header("🤝 Mercado de Fichajes y Cláusulas de Rescisión")

  tab_neg, tab_clausulas, tab_bandeja = st.tabs([
      "📩 Negociar con Clubes",
      "⚡ Pagar Cláusulas",
      "📥 Bandeja de Ofertas Recibidas",
  ])

  with tab_neg:
    st.subheader("Hacer oferta a otro club")
    if st.session_state.es_solo_admin:
      st.warning("Entra como club para negociar.")
    else:
      mi_eq = st.session_state.mi_equipo
      otros_equipos = [e for e in st.session_state.equipos if e.id_club != mi_eq.id_club]
      eq_destino_nombre = st.selectbox("Selecciona el club propietario:", [e.nombre for e in otros_equipos])
      eq_dest = next(e for e in otros_equipos if e.nombre == eq_destino_nombre)

      if eq_dest.plantilla:
        jugador_sel_nom = st.selectbox("Selecciona al jugador:", [j.nombre for j in eq_dest.plantilla])
        j_obj = next(j for j in eq_dest.plantilla if j.nombre == jugador_sel_nom)
        st.write(f"ℹ️ Valor de mercado: {j_obj.valor_base:,} € | Cláusula: {j_obj.clausula:,} €")

        monto_oferta = st.number_input(
            "Monto de tu oferta (€):",
            min_value=1_000_000,
            step=5_000_000,
            value=j_obj.valor_base,
        )

        if st.button("Enviar Oferta Formal"):
          if monto_oferta <= mi_eq.presupuesto:
            if "ofertas_fichaje" not in st.session_state:
              st.session_state.ofertas_fichaje = []
            st.session_state.ofertas_fichaje.append({
                "comprador": mi_eq.nombre,
                "vendedor": eq_dest.nombre,
                "jugador": j_obj.nombre,
                "monto": monto_oferta,
            })
            guardar_partida()
            st.success(f"¡Oferta enviada a {eq_dest.nombre} por {monto_oferta:,} €!")
          else:
            st.error("No tienes fondos suficientes para esta oferta.")
      else:
        st.info("Este club no tiene jugadores en plantilla.")

  with tab_clausulas:
    st.subheader("Pagar cláusula de rescisión (Fichaje Inmediato)")
    if st.session_state.es_solo_admin:
      st.warning("Accede como club para pagar cláusulas.")
    else:
      mi_eq = st.session_state.mi_equipo
      todos_los_jugadores = []
      for e in st.session_state.equipos:
        if e.id_club != mi_eq.id_club:
          for j in e.plantilla:
            todos_los_jugadores.append((e, j))

      if todos_los_jugadores:
        opciones_clausulas = [
            f"{j.nombre} ({e.nombre}) - Cláusula: {j.clausula:,} €"
            for e, j in todos_los_jugadores
        ]
        sel_clausula = st.selectbox("Selecciona jugador a clausular:", opciones_clausulas)
        idx_sel = opciones_clausulas.index(sel_clausula)
        eq_propietario, jugador_clausulado = todos_los_jugadores[idx_sel]

        st.write(f"Club actual: {eq_propietario.emoji} {eq_propietario.nombre} | GRL: {jugador_clausulado.grl}")

        if st.button("🚨 Pagar Cláusula al Contado"):
          if mi_eq.presupuesto >= jugador_clausulado.clausula:
            mi_eq.presupuesto -= jugador_clausulado.clausula
            eq_propietario.presupuesto += jugador_clausulado.clausula
            eq_propietario.plantilla.remove(jugador_clausulado)
            mi_eq.plantilla.append(jugador_clausulado)
            guardar_partida()
            st.success(f"🎉 ¡Has pagado la cláusula de {jugador_clausulado.nombre} y ya es tuyo!")
            st.rerun()
          else:
            st.error("No tienes suficiente presupuesto para pagar esta cláusula.")
      else:
        st.info("No hay jugadores disponibles en otros clubes.")

  with tab_bandeja:
    st.subheader("Ofertas recibidas de otros equipos")
    if st.session_state.es_solo_admin:
      st.info("Vista de administrador.")
    else:
      mi_eq = st.session_state.mi_equipo
      ofertas_mias = [
          o for o in st.session_state.get("ofertas_fichaje", []) if o["vendedor"] == mi_eq.nombre
      ]

      if ofertas_mias:
        for i, oferta in enumerate(ofertas_mias):
          st.write(f"📌 **{oferta['comprador']}** ofrece **{oferta['monto']:,} €** por tu jugador **{oferta['jugador']}**")
          col_a, col_r = st.columns(2)
          with col_a:
            if st.button("✅ Aceptar", key=f"aceptar_{i}"):
              comprador = next(e for e in st.session_state.equipos if e.nombre == oferta["comprador"])
              jugador_obj = next(j for j in mi_eq.plantilla if j.nombre == oferta["jugador"])

              if comprador.presupuesto >= oferta["monto"]:
                comprador.presupuesto -= oferta["monto"]
                mi_eq.presupuesto += oferta["monto"]
                mi_eq.plantilla.remove(jugador_obj)
                comprador.plantilla.append(jugador_obj)
                st.session_state.ofertas_fichaje.remove(oferta)
                guardar_partida()
                st.success(f"¡Transacción completada! {jugador_obj.nombre} se fue a {comprador.nombre}.")
                st.rerun()
              else:
                st.error("El comprador ya no tiene fondos suficientes.")
          with col_r:
            if st.button("❌ Rechazar", key=f"rechazar_{i}"):
              st.session_state.ofertas_fichaje.remove(oferta)
              guardar_partida()
              st.warning("Oferta rechazada.")
              st.rerun()
      else:
        st.info("No tienes ofertas pendientes en este momento.")

# 5. RESULTADOS
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
      st.info("Sin partidos de Liga simulados.")
  with tab_copa:
    if st.session_state.get("historial_copas"):
      for res in st.session_state.historial_copas:
        st.markdown(res)
    else:
      st.info("Copa de España pendiente.")
  with tab_mundial:
    if st.session_state.get("historial_mundial"):
      for res in st.session_state.historial_mundial:
        st.markdown(res)
    else:
      st.info("Mundial de Clubes pendiente.")

# 6. PANEL PRO ADMIN
elif menu == "⚡ Pro Admin":
  st.header("⚡ Panel de Control Pro Admin - Beta 2.0 (Con Bots IA)")

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
    st.info("💡 Gestiona torneos, simula jornadas, configura bots o avanza de temporada.")
    col_temp_btn1, col_temp_btn2 = st.columns([2, 1])
    with col_temp_btn1:
      st.warning("⚠️ ¿Iniciar siguiente temporada? ¡Se cobrarán los salarios de las plantillas a todos los clubes!")
    with col_temp_btn2:
      if st.button("🌟 Iniciar Siguiente Temporada", type="primary"):
        for eq in st.session_state.equipos:
          total_salarios = eq.calcular_salarios_totales()
          eq.presupuesto -= total_salarios
          eq.puntos = 0
          eq.pj = 0
          eq.pg = 0
          eq.pe = 0
          eq.pp = 0
          eq.gf = 0
          eq.gc = 0

        st.session_state.jornada_actual = 1
        st.session_state.historial_resultados = []
        st.session_state.historial_copas = []
        st.session_state.historial_mundial = []
        st.session_state.campeon_copa = None
        guardar_partida()
        st.success("¡Nueva temporada iniciada con éxito! Salarios descontados.")
        st.rerun()

    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚽ Partidos & Mercado",
        "🏆 Torneos Post-Liga",
        "🤖 Gestión de Bots",
        "💰 Gestor Financiero",
        "🛠️ Modificar Stats & PINs",
    ])

    with tab1:
      st.subheader(f"Simular Jornada {st.session_state.jornada_actual}")
      if st.session_state.jornada_actual <= 11:
        if st.button("🚀 Simular Partidos & Acciones IA"):
          ejecutar_logica_bots()

          equipos_shuffled = st.session_state.equipos.copy()
          random.shuffle(equipos_shuffled)
          res_jornada = []
          for i in range(0, len(equipos_shuffled), 2):
            local, visitante = equipos_shuffled[i], equipos_shuffled[i + 1]
            media_loc, media_vis = local.calcular_media_equipo(), visitante.calcular_media_equipo()
            dif = (media_loc + 3) - media_vis
            gl = max(0, int(random.gauss(max(0.5, 1.5 + (dif / 10.0)), 0.9)))
            gv = max(0, int(random.gauss(max(0.3, 1.1 - (dif / 10.0)), 0.9)))

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
              res_jornada.append(f"{local.emoji} **{local.nombre}** {gl} - {gv} {visitante.emoji} {visitante.nombre} (Gana local)")
            elif gv > gl:
              visitante.puntos += 3
              visitante.pg += 1
              local.pp += 1
              res_jornada.append(f"{local.emoji} {local.nombre} {gl} - {gv} {visitante.emoji} **{visitante.nombre}** (Gana visitante)")
            else:
              local.puntos += 1
              visitante.puntos += 1
              local.pe += 1
              visitante.pe += 1
              res_jornada.append(f"🤝 {local.emoji} {local.nombre} {gl} - {gv} {visitante.emoji} {visitante.nombre} (Empate)")

          st.session_state.historial_resultados.append((st.session_state.jornada_actual, res_jornada))
          st.session_state.jornada_actual += 1
          guardar_partida()
          st.success(f"¡Jornada simulada con éxito!")
          st.rerun()
