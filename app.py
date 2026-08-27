import datetime
import json
import os
import random
import time
import streamlit as st

st.set_page_config(
    page_title="Liga Manager Fantasy Pro - Todo Incluido",
    page_icon="⚽",
    layout="wide",
)

PRESUPUESTO_INICIAL = 200_000_000
CLAVE_ADMIN = "1234"
ARCHIVO_GUARDADO = "liga_estado_total_pro.json"


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
    self.presidente = (
        f"Presidente Club {id_club}" if es_humano else f"🤖 Bot {nombre}"
    )
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

  def obtener_titulares_validos(self):
    key_titulares = f"titulares_{self.id_club}"
    if key_titulares in st.session_state and st.session_state[key_titulares]:
      nombres_titulares = st.session_state[key_titulares]
      titulares = [j for j in self.plantilla if j.nombre in nombres_titulares]
      if len(titulares) == 11:
        return titulares
    # Selección automática por defecto si no hay 11 elegidos
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


# --- MOTORES DE SIMULACIÓN Y GUARDADO ---
def simular_jornada_liga():
  if st.session_state.jornada_actual > 11:
    return False

  equipos_shuffled = st.session_state.equipos.copy()
  random.shuffle(equipos_shuffled)
  res_jornada = []

  for i in range(0, len(equipos_shuffled), 2):
    local, visitante = equipos_shuffled[i], equipos_shuffled[i + 1]
    media_loc, media_vis = (
        local.calcular_media_equipo(),
        visitante.calcular_media_equipo(),
    )
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
    elif gv > gl:
      visitante.puntos += 3
      visitante.pg += 1
      local.pp += 1
    else:
      local.puntos += 1
      visitante.puntos += 1
      local.pe += 1
      visitante.pe += 1

    res_jornada.append(
        f"{local.emoji} {local.nombre} ({media_loc} GRL) **{gl} - {gv}**"
        f" ({media_vis} GRL) {visitante.nombre} {visitante.emoji}"
    )

  st.session_state.historial_resultados.append(
      (st.session_state.jornada_actual, res_jornada)
  )
  st.session_state.jornada_actual += 1
  guardar_partida()
  return True


def simular_copa_espana_fase():
  ordenados = sorted(
      st.session_state.equipos,
      key=lambda x: (x.puntos, x.dg, x.gf),
      reverse=True,
  )
  top_4 = ordenados[:4]
  if len(top_4) < 4:
    return
  semifinal_1 = (
      top_4[0]
      if top_4[0].calcular_media_equipo() >= top_4[3].calcular_media_equipo()
      else top_4[3]
  )
  semifinal_2 = (
      top_4[1]
      if top_4[1].calcular_media_equipo() >= top_4[2].calcular_media_equipo()
      else top_4[2]
  )
  campeon = (
      semifinal_1
      if semifinal_1.calcular_media_equipo()
      >= semifinal_2.calcular_media_equipo()
      else semifinal_2
  )

  st.session_state.campeon_copa = campeon
  st.session_state.historial_copas.append(
      f"🏆 Campeón Copa de España: {campeon.emoji} {campeon.nombre}"
  )
  st.session_state.fase_copa_jugada = True
  guardar_partida()


def simular_mundial_clubes_fase():
  candidatos = sorted(
      st.session_state.equipos, key=lambda x: x.calcular_media_equipo(), reverse=True
  )
  campeon_mundial = candidatos[0]
  st.session_state.campeon_mundial = campeon_mundial
  st.session_state.historial_mundial.append(
      f"🌍 Campeón Mundial de Clubes: {campeon_mundial.emoji}"
      f" {campeon_mundial.nombre}"
  )
  st.session_state.fase_mundial_jugada = True
  st.session_state.modo_auto_activo = False
  guardar_partida()


def guardar_partida():
  campeon_nombre = (
      st.session_state.campeon_copa.nombre
      if hasattr(st.session_state.get("campeon_copa"), "nombre")
      else st.session_state.get("campeon_copa")
  )
  campeon_mundial_nombre = (
      st.session_state.campeon_mundial.nombre
      if hasattr(st.session_state.get("campeon_mundial"), "nombre")
      else st.session_state.get("campeon_mundial")
  )

  data = {
      "jornada_actual": st.session_state.get("jornada_actual", 1),
      "historial_resultados": st.session_state.get("historial_resultados", []),
      "historial_copas": st.session_state.get("historial_copas", []),
      "historial_mundial": st.session_state.get("historial_mundial", []),
      "campeon_copa": campeon_nombre,
      "campeon_mundial": campeon_mundial_nombre,
      "fase_copa_jugada": st.session_state.get("fase_copa_jugada", False),
      "fase_mundial_jugada": st.session_state.get("fase_mundial_jugada", False),
      "modo_auto_activo": st.session_state.get("modo_auto_activo", False),
      "equipos": [e.to_dict() for e in st.session_state.equipos],
      "mercado_pool": [
          j.to_dict() for j in st.session_state.get("mercado_pool", [])
      ],
  }
  with open(ARCHIVO_GUARDADO, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4, default=str)


def cargar_partida():
  if os.path.exists(ARCHIVO_GUARDADO):
    try:
      with open(ARCHIVO_GUARDADO, "r", encoding="utf-8") as f:
        data = json.load(f)
      st.session_state.jornada_actual = data.get("jornada_actual", 1)
      st.session_state.historial_resultados = data.get(
          "historial_resultados", []
      )
      st.session_state.historial_copas = data.get("historial_copas", [])
      st.session_state.historial_mundial = data.get("historial_mundial", [])
      st.session_state.campeon_copa = data.get("campeon_copa")
      st.session_state.campeon_mundial = data.get("campeon_mundial")
      st.session_state.fase_copa_jugada = data.get("fase_copa_jugada", False)
      st.session_state.fase_mundial_jugada = data.get(
          "fase_mundial_jugada", False
      )
      st.session_state.modo_auto_activo = data.get("modo_auto_activo", False)
      st.session_state.equipos = [Equipo.from_dict(e) for e in data["equipos"]]
      st.session_state.mercado_pool = [
          Jugador.from_dict(j) for j in data.get("mercado_pool", [])
      ]
      st.session_state.liga_inicializada = True
      return True
    except Exception:
      if os.path.exists(ARCHIVO_GUARDADO):
        os.remove(ARCHIVO_GUARDADO)
      return False
  return False


if "liga_inicializada" not in st.session_state:
  if not cargar_partida():
    NOMBRES = [
        "Aarón",
        "Beto",
        "Carlos",
        "Damián",
        "Enzo",
        "Franco",
        "Gael",
        "Hugo",
        "Iker",
        "Javier",
    ]
    APELLIDOS = [
        "Roca",
        "Soto",
        "Vidal",
        "Blanco",
        "Cruz",
        "Navarro",
        "Peña",
        "Mora",
        "Rios",
        "Vega",
    ]
    POSICIONES = [
        "POR",
        "DEF",
        "DEF",
        "DEF",
        "MED",
        "MED",
        "MED",
        "DEL",
        "DEL",
        "DEL",
    ]

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
      es_humano = id_c == 1
      eq = Equipo(id_c, nom, emoji, pin_predeterminado=id_c, es_humano=es_humano)
      eq.plantilla = generar_plantilla_base()
      clubes.append(eq)

    # Mercado inicial de jugadores libres
    mercado_inicial = [
        Jugador(
            f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}",
            random.choice(POSICIONES),
            random.randint(65, 80),
            random.randint(65, 80) * 120_000,
        )
        for _ in range(10)
    ]

    st.session_state.equipos = clubes
    st.session_state.jornada_actual = 1
    st.session_state.historial_resultados = []
    st.session_state.historial_copas = []
    st.session_state.historial_mundial = []
    st.session_state.campeon_copa = None
    st.session_state.campeon_mundial = None
    st.session_state.fase_copa_jugada = False
    st.session_state.fase_mundial_jugada = False
    st.session_state.modo_auto_activo = False
    st.session_state.mercado_pool = mercado_inicial
    st.session_state.liga_inicializada = True
    guardar_partida()

if "es_admin_autenticado" not in st.session_state:
  st.session_state.es_admin_autenticado = False
if "es_solo_admin" not in st.session_state:
  st.session_state.es_solo_admin = False
if "modo_auto_activo" not in st.session_state:
  st.session_state.modo_auto_activo = False

# --- PORTAL DE ACCESO ---
if "mi_equipo" not in st.session_state and not st.session_state.es_solo_admin:
  st.title("🎮 Portal de Acceso a la Liga - Pro Admin Edition")
  col_jugador, col_admin = st.columns(2)

  with col_jugador:
    st.subheader("Acceso a Clubes (PIN 1 - 12)")
    eq_login_nombre = st.selectbox(
        "Selecciona tu Club:",
        [
            f"Nº {e.id_club} | {e.emoji} {e.nombre} ({'Humano' if e.es_humano else '🤖 Bot'})"
            for e in st.session_state.equipos
        ],
    )
    nombre_presi_input = st.text_input("Tu Nombre de Presidente:")
    pwd_login = st.text_input("PIN de Acceso:", type="password")

    if st.button("Ingresar al Club"):
      idx_SEL = [
          f"Nº {e.id_club} | {e.emoji} {e.nombre} ({'Humano' if e.es_humano else '🤖 Bot'})"
          for e in st.session_state.equipos
      ].index(eq_login_nombre)
      eq_obj = st.session_state.equipos[idx_SEL]

      if pwd_login.strip() == str(eq_obj.password):
        eq_obj.es_humano = True
        if nombre_presi_input.strip():
          eq_obj.presidente = nombre_presi_input.strip()
        guardar_partida()
        st.session_state.mi_equipo = eq_obj
        st.success("¡Acceso concedido!")
        st.rerun()
      else:
        st.error("PIN incorrecto.")

  with col_admin:
    st.subheader("Acceso Administrador Supremo")
    pwd = st.text_input("Clave de Administrador:", type="password")
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
  st.session_state.mi_equipo = next(
      e for e in st.session_state.equipos if e.nombre == nombre_actual
  )

# --- BARRA LATERAL ---
st.sidebar.title("⚽ Panel de Control")
if st.session_state.es_solo_admin:
  st.sidebar.write("Rol: **Comisionado Pro Admin**")
else:
  mi_eq = st.session_state.mi_equipo
  st.sidebar.write(f"Club: **{mi_eq.emoji} {mi_eq.nombre}**")

estado_auto_txt = (
    "🟢 ACTIVO (Automático)"
    if st.session_state.modo_auto_activo
    else "🔴 DESACTIVADO"
)
st.sidebar.markdown(f"**Modo Pro Automático:** {estado_auto_txt}")
st.sidebar.markdown(f"Jornada Actual: **{st.session_state.jornada_actual} / 11**")

if st.session_state.jornada_actual <= 11:
  prox_nombre_evento = f"Jornada {st.session_state.jornada_actual}"
  intervalo_txt = "Cada 2 minutos"
elif not st.session_state.fase_copa_jugada:
  prox_nombre_evento = "Copa de España"
  intervalo_txt = "Cada 10 minutos"
elif not st.session_state.fase_mundial_jugada:
  prox_nombre_evento = "Mundial de Clubes"
  intervalo_txt = "Cada 10 minutos"
else:
  prox_nombre_evento = "Temporada Finalizada"
  intervalo_txt = "-"

st.sidebar.info(
    f"⏱️ **Próximo Evento:**\n{prox_nombre_evento}\n*(Frecuencia: {intervalo_txt})*"
)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Cerrar Sesión"):
  if "mi_equipo" in st.session_state:
    del st.session_state["mi_equipo"]
  st.session_state.es_solo_admin = False
  st.session_state.es_admin_autenticado = False
  st.rerun()

opciones_menu = [
    "📊 Clasificación",
    "⚡ Pro Admin & Automatización",
    "⚽ Resultados y Copas",
]
if not st.session_state.es_solo_admin:
  opciones_menu.insert(1, "📋 Mi Plantilla")
  opciones_menu.insert(2, "🛒 Mercado de Fichajes")

menu = st.sidebar.radio("Navegación", opciones_menu)

# --- SECCIONES DE LA APLICACIÓN ---

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
    datos.append({
        "Pos": idx,
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
        "Clasificación": zona,
    })
  st.table(datos)

elif menu == "⚡ Pro Admin & Automatización":
  st.header("⚡ Centro de Mando Pro Admin (Automatización Total)")

  if not st.session_state.es_admin_autenticado and not st.session_state.es_solo_admin:
    pwd = st.text_input("Clave de Administrador:", type="password")
    if st.button("Verificar Clave"):
      if pwd == CLAVE_ADMIN:
        st.session_state.es_admin_autenticado = True
        st.rerun()
      else:
        st.error("Clave incorrecta.")
  else:
    st.subheader("🎮 Control de Interruptor Automático")
    st.write(
        "Activa o desactiva el bot automático. Los partidos de liga se"
        " simularán cada **2 minutos** y los eventos de Copa y Mundial cada"
        " **10 minutos**."
    )

    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button(
        "🟢 ACTIVAR MODO AUTOMÁTICO", type="primary", use_container_width=True
    ):
      st.session_state.modo_auto_activo = True
      guardar_partida()
      st.success("¡Modo Automático ACTIVADO!")
      st.rerun()

    if col_btn2.button(
        "🔴 DESACTIVAR MODO AUTOMÁTICO", use_container_width=True
    ):
      st.session_state.modo_auto_activo = False
      guardar_partida()
      st.warning("¡Modo Automático DESACTIVADO!")
      st.rerun()

    st.markdown("---")
    st.subheader("⚙️ Simulación Manual Instantánea")
    c_m1, c_m2, c_m3 = st.columns(3)

    if c_m1.button("▶️ Simular Siguiente Jornada Liga"):
      if simular_jornada_liga():
        st.success("¡Jornada de Liga simulada con éxito!")
        st.rerun()
      else:
        st.warning("La liga ya ha finalizado.")

    if c_m2.button("🏆 Simular Copa de España"):
      if st.session_state.jornada_actual > 11 and not st.session_state.fase_copa_jugada:
        simular_copa_espana_fase()
        st.success("¡Copa de España simulada!")
        st.rerun()
      else:
        st.warning("La liga aún no termina o la copa ya se jugó.")

    if c_m3.button("🌍 Simular Mundial de Clubes"):
      if st.session_state.fase_copa_jugada and not st.session_state.fase_mundial_jugada:
        simular_mundial_clubes_fase()
        st.success("¡Mundial de Clubes simulado!")
        st.rerun()
      else:
        st.warning("Debes finalizar la Copa de España primero.")

    if st.session_state.get("modo_auto_activo", False):
      st.info(
          "🤖 **Bot Pro Admin en ejecución autónoma...** La aplicación"
          " avanzará automáticamente según el tiempo programado."
      )
      if st.session_state.jornada_actual <= 11:
        time.sleep(120)  # 2 minutos
        simular_jornada_liga()
        st.rerun()
      elif not st.session_state.fase_copa_jugada:
        time.sleep(600)  # 10 minutos
        simular_copa_espana_fase()
        st.rerun()
      elif not st.session_state.fase_mundial_jugada:
        time.sleep(600)  # 10 minutos
        simular_mundial_clubes_fase()
        st.rerun()
      else:
        st.session_state.modo_auto_activo = False
        guardar_partida()
        st.success("🎉 ¡Todos los torneos han finalizado con éxito!")

elif menu == "📋 Mi Plantilla":
  mi_eq = st.session_state.mi_equipo
  st.header(f"📋 Plantilla de {mi_eq.nombre}")
  st.metric("Presupuesto Actual", f"{mi_eq.presupuesto:,} €")

  st.subheader("Configurar Alineación Titular (11 Jugadores)")
  nombres_plantilla = [j.nombre for j in mi_eq.plantilla]
  key_titulares = f"titulares_{mi_eq.id_club}"

  sugeridos = [
      j.nombre for j in mi_eq.obtener_titulares_validos()
  ]  # Default top 11
  titulares_elegidos = st.multiselect(
      "Selecciona exactamente 11 jugadores titulares:",
      options=nombres_plantilla,
      default=sugeridos[: min(11, len(sugeridos))],
  )

  if len(titulares_elegidos) == 11:
    st.session_state[key_titulares] = titulares_elegidos
    st.success("✅ ¡Alineación válida guardada!")
  else:
    st.warning(
        f"Has seleccionado {len(titulares_elegidos)}/11 jugadores. Deben ser"
        " exactamente 11 para competir al 100%."
    )

  st.markdown("---")
  st.subheader("Jugadores en Plantilla")
  datos_plantilla = [
      {
          "Jugador": j.nombre,
          "Posición": j.posicion,
          "Media": j.grl,
          "Valor": f"{j.valor_base:,} €",
          "Cláusula": f"{j.clausula:,} €",
      }
      for j in mi_eq.plantilla
  ]
  st.dataframe(datos_plantilla, use_container_width=True, hide_index=True)

elif menu == "🛒 Mercado de Fichajes":
  mi_eq = st.session_state.mi_equipo
  st.header("🛒 Mercado de Libres")
  st.metric("Tu Presupuesto", f"{mi_eq.presupuesto:,} €")

  if not st.session_state.get("mercado_pool"):
    st.info("El mercado está vació por ahora.")
  else:
    for idx, jug in enumerate(st.session_state.mercado_pool):
      col1, col2, col3 = st.columns([3, 2, 1])
      col1.write(
          f"**{jug.nombre}** ({jug.posicion}) - Media: **{jug.grl}** GRL"
      )
      col2.write(f"Valor: **{jug.valor_base:,} €**")
      if col3.button("Fichar", key=f"fichar_{idx}"):
        if mi_eq.presupuesto >= jug.valor_base:
          mi_eq.presupuesto -= jug.valor_base
          mi_eq.plantilla.append(jug)
          st.session_state.mercado_pool.pop(idx)
          guardar_partida()
          st.success(f"¡Has fichado a {jug.nombre}!")
          st.rerun()
        else:
          st.error("No tienes suficiente presupuesto.")

elif menu == "⚽ Resultados y Copas":
  st.header("⚽ Historial de Partidos, Copa y Mundial")

  if st.session_state.historial_copas:
    st.subheader("🏆 Palmarés de Copa de España")
    for copa_res in st.session_state.historial_copas:
      st.success(copa_res)

  if st.session_state.historial_mundial:
    st.subheader("🌍 Palmarés de Mundial de Clubes")
    for mund_res in st.session_state.historial_mundial:
      st.info(mund_res)

  st.subheader("📋 Resultados de la Liga")
  if st.session_state.historial_resultados:
    for j_num, res in reversed(st.session_state.historial_resultados):
      with st.expander(f"Jornada {j_num}"):
        for match in res:
          st.write(match)
  else:
    st.info("Aún no hay partidos simulados.")
