import datetime
import json
import os
import random
import streamlit as st

# ============================================================
# LIGA MANAGER FANTASY — BETA 3.1
# ============================================================
# 12 clubes | 11 jornadas | Copa de España | Mundial de Clubes
# IA autónoma | Mercado | Subastas | Finanzas | Historial
# ============================================================

st.set_page_config(
    page_title="Liga Manager Fantasy Beta 3.1",
    page_icon="⚽",
    layout="wide",
)

PRESUPUESTO_INICIAL = 200_000_000
CLAVE_ADMIN = "1234"
ARCHIVO_GUARDADO = "liga_estado_beta31.json"
TOTAL_JORNADAS = 11

# Premios oficiales
PREMIOS_LIGA = {
    1: 30_000_000,
    2: 10_000_000,
    3: 7_000_000,
    4: 5_000_000,
}
PREMIO_LIGA_RESTO = 1_000_000
PREMIO_COPA = 40_000_000
PREMIO_MUNDIAL = 70_000_000


# ============================================================
# MODELOS
# ============================================================

def calcular_salario(valor_base, grl):
    """Salario anual: aumenta con el valor y el GRL del jugador."""
    return max(250_000, int(valor_base * 0.015 + grl * 100_000))

class Jugador:
    def __init__(self, nombre, posicion, grl, valor_base):
        self.nombre = nombre
        self.posicion = posicion
        self.grl = int(grl)
        self.valor_base = int(valor_base)
        self.clausula = int(valor_base * 2)
        self.salario = calcular_salario(valor_base, self.grl)

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
        j = cls(
            d.get("nombre", "Jugador"),
            d.get("posicion", "MED"),
            d.get("grl", 60),
            d.get("valor_base", 60_000_000),
        )
        j.clausula = int(d.get("clausula", j.valor_base * 2))
        j.salario = int(d.get("salario", calcular_salario(j.valor_base, j.grl)))
        return j


class Equipo:
    def __init__(self, id_club, nombre, emoji, pin_predeterminado,
                 es_humano=True, pais="España"):
        self.id_club = id_club
        self.nombre = nombre
        self.emoji = emoji
        self.pais = pais
        self.presidente = (
            f"Presidente Club {id_club}"
            if es_humano
            else f"🤖 Bot {nombre}"
        )
        self.password = str(pin_predeterminado)
        self.es_humano = es_humano
        self.presupuesto = PRESUPUESTO_INICIAL
        self.plantilla = []

        # Liga
        self.puntos = 0
        self.pj = 0
        self.pg = 0
        self.pe = 0
        self.pp = 0
        self.gf = 0
        self.gc = 0

        # Estadísticas de temporada
        self.premios = 0
        self.ingresos = 0
        self.gastos = 0
        self.titulos = 0
        self.historial_temporadas = []

        # IA
        self.estilo_ia = "Equilibrado"

    @property
    def dg(self):
        return self.gf - self.gc

    def calcular_salarios_totales(self):
        return sum(j.salario for j in self.plantilla)

    def obtener_titulares_validos(self):
        key_titulares = f"titulares_{self.id_club}"
        if key_titulares in st.session_state and st.session_state[key_titulares]:
            nombres = st.session_state[key_titulares]
            titulares = [j for j in self.plantilla if j.nombre in nombres]
            if len(titulares) == 11:
                return titulares

        requeridas = [
            "POR", "DEF", "DEF", "DEF",
            "MED", "MED", "MED",
            "DEL", "DEL", "DEL",
            "DEF",
        ]
        mejores = []

        for pos in requeridas:
            candidatos = [
                j for j in self.plantilla
                if j.posicion == pos and j not in mejores
            ]
            if not candidatos:
                candidatos = [
                    j for j in self.plantilla
                    if j not in mejores
                ]
            if candidatos:
                candidatos.sort(key=lambda x: x.grl, reverse=True)
                mejores.append(candidatos[0])

        return mejores

    def calcular_media_equipo(self):
        titulares = self.obtener_titulares_validos()
        if not titulares:
            return 40
        media = sum(j.grl for j in titulares) // len(titulares)
        if len(titulares) < 11:
            media -= (11 - len(titulares)) * 5
        return max(40, media)

    def registrar_ingreso(self, cantidad, motivo):
        self.presupuesto += cantidad
        self.ingresos += cantidad
        self.premios += cantidad
        registrar_finanza(self, "Ingreso", cantidad, motivo)

    def registrar_gasto(self, cantidad, motivo):
        self.presupuesto -= cantidad
        self.gastos += cantidad
        registrar_finanza(self, "Gasto", cantidad, motivo)

    def to_dict(self):
        return {
            "id_club": self.id_club,
            "nombre": self.nombre,
            "emoji": self.emoji,
            "pais": self.pais,
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
            "premios": self.premios,
            "ingresos": self.ingresos,
            "gastos": self.gastos,
            "titulos": self.titulos,
            "historial_temporadas": self.historial_temporadas,
            "estilo_ia": self.estilo_ia,
        }

    @classmethod
    def from_dict(cls, d):
        eq = cls(
            d.get("id_club", 1),
            d.get("nombre", "Club"),
            d.get("emoji", "⚽"),
            d.get("password", str(d.get("id_club", 1))),
            d.get("es_humano", True),
            d.get("pais", "España"),
        )
        eq.presidente = d.get("presidente", f"Presidente Club {eq.id_club}")
        eq.presupuesto = int(d.get("presupuesto", PRESUPUESTO_INICIAL))
        eq.plantilla = [Jugador.from_dict(j) for j in d.get("plantilla", [])]
        eq.puntos = int(d.get("puntos", 0))
        eq.pj = int(d.get("pj", 0))
        eq.pg = int(d.get("pg", 0))
        eq.pe = int(d.get("pe", 0))
        eq.pp = int(d.get("pp", 0))
        eq.gf = int(d.get("gf", 0))
        eq.gc = int(d.get("gc", 0))
        eq.premios = int(d.get("premios", 0))
        eq.ingresos = int(d.get("ingresos", 0))
        eq.gastos = int(d.get("gastos", 0))
        eq.titulos = int(d.get("titulos", 0))
        eq.historial_temporadas = d.get("historial_temporadas", [])
        eq.estilo_ia = d.get("estilo_ia", random.choice(ESTILOS_IA))
        return eq


ESTILOS_IA = [
    "Galáctico",
    "Agresivo",
    "Ahorrador",
    "Estratega",
    "Jóvenes",
    "Equilibrado",
]

NOMBRES = [
    "Aarón", "Beto", "Carlos", "Damián", "Enzo", "Franco", "Gael",
    "Hugo", "Iker", "Javier", "Leo", "Marco", "Nico", "Óscar",
    "Pablo", "Rayan", "Sergio", "Thiago", "Álex", "Adrián",
]
APELLIDOS = [
    "Roca", "Soto", "Vidal", "Blanco", "Cruz", "Navarro", "Peña",
    "Mora", "Ríos", "Vega", "Torres", "Molina", "Santos", "Ruiz",
]
POSICIONES = [
    "POR", "DEF", "DEF", "DEF", "DEF",
    "MED", "MED", "MED", "MED",
    "DEL", "DEL", "DEL",
]

# ============================================================
# UTILIDADES
# ============================================================

def dinero(n):
    return f"{int(n):,} €"


def registrar_finanza(eq, tipo, cantidad, motivo):
    if "historial_finanzas" not in st.session_state:
        st.session_state.historial_finanzas = []
    st.session_state.historial_finanzas.append({
        "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "club": eq.nombre,
        "tipo": tipo,
        "cantidad": int(cantidad),
        "motivo": motivo,
    })


def generar_jugador_aleatorio(min_grl=60, max_grl=75):
    pos = random.choice(POSICIONES)
    grl = random.randint(min_grl, max_grl)
    valor = random.randint(max(40, grl - 10), grl + 10) * 1_000_000
    return Jugador(
        f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}",
        pos,
        grl,
        valor,
    )


def generar_plantilla_base(min_grl=60, max_grl=75):
    return [generar_jugador_aleatorio(min_grl, max_grl) for _ in POSICIONES]


def buscar_equipo(nombre):
    return next(
        (e for e in st.session_state.equipos if e.nombre == nombre),
        None,
    )


def clasificacion():
    return sorted(
        st.session_state.equipos,
        key=lambda x: (x.puntos, x.dg, x.gf),
        reverse=True,
    )


def limpiar_resultados_temporada():
    for eq in st.session_state.equipos:
        eq.puntos = eq.pj = eq.pg = eq.pe = eq.pp = 0
        eq.gf = eq.gc = 0
        eq.premios = eq.ingresos = eq.gastos = 0


def registrar_evento(texto):
    if "noticias" not in st.session_state:
        st.session_state.noticias = []
    st.session_state.noticias.insert(0, {
        "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "texto": texto,
    })
    st.session_state.noticias = st.session_state.noticias[:100]


# ============================================================
# CALENDARIO REAL DE 11 JORNADAS
# ============================================================

def generar_calendario_11():
    equipos = [e.id_club for e in st.session_state.equipos]
    arr = equipos[:]
    calendario = []

    # Método círculo para 12 equipos = 11 jornadas.
    for jornada in range(11):
        partidos = []
        for i in range(6):
            a = arr[i]
            b = arr[-1 - i]
            # Alternar localía
            if (jornada + i) % 2 == 0:
                partidos.append((a, b))
            else:
                partidos.append((b, a))
        calendario.append(partidos)

        fijo = arr[0]
        resto = arr[1:]
        resto = [resto[-1]] + resto[:-1]
        arr = [fijo] + resto

    return calendario


# ============================================================
# SIMULACIÓN
# ============================================================

def simular_partido(eq1, eq2, eliminatoria=False):
    media1 = eq1.calcular_media_equipo()
    media2 = eq2.calcular_media_equipo()

    ventaja_local = 3 if not eliminatoria else 0
    dif = (media1 + ventaja_local) - media2

    esp1 = max(0.3, 1.45 + dif / 11)
    esp2 = max(0.3, 1.20 - dif / 11)

    g1 = max(0, int(random.gauss(esp1, 0.95)))
    g2 = max(0, int(random.gauss(esp2, 0.95)))

    return g1, g2


def resultado_eliminatoria(eq1, eq2):
    g1, g2 = simular_partido(eq1, eq2, True)

    if g1 == g2:
        p1 = random.randint(3, 5)
        p2 = random.randint(3, 5)
        while p1 == p2:
            p1 = random.randint(3, 5)
            p2 = random.randint(3, 5)
        ganador = eq1 if p1 > p2 else eq2
        texto = (
            f"{eq1.emoji} **{eq1.nombre}** {g1} - {g2} "
            f"{eq2.emoji} **{eq2.nombre}** "
            f"*(Penaltis {p1}-{p2})*"
        )
    else:
        ganador = eq1 if g1 > g2 else eq2
        texto = (
            f"{eq1.emoji} **{eq1.nombre}** {g1} - {g2} "
            f"{eq2.emoji} **{eq2.nombre}**"
        )

    return ganador, texto


def simular_jornada():
    num = st.session_state.jornada_actual
    if num > TOTAL_JORNADAS:
        return False

    calendario = st.session_state.calendario
    partidos = calendario[num - 1]
    res = []

    for id_local, id_visitante in partidos:
        local = next(e for e in st.session_state.equipos if e.id_club == id_local)
        visitante = next(e for e in st.session_state.equipos if e.id_club == id_visitante)

        gl, gv = simular_partido(local, visitante)

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
            res.append(
                f"🏠 {local.emoji} **{local.nombre}** {gl} - {gv} "
                f"{visitante.emoji} {visitante.nombre}"
            )
        elif gv > gl:
            visitante.puntos += 3
            visitante.pg += 1
            local.pp += 1
            res.append(
                f"✈️ {local.emoji} {local.nombre} {gl} - {gv} "
                f"{visitante.emoji} **{visitante.nombre}**"
            )
        else:
            local.puntos += 1
            visitante.puntos += 1
            local.pe += 1
            visitante.pe += 1
            res.append(
                f"🤝 {local.emoji} {local.nombre} {gl} - {gv} "
                f"{visitante.emoji} {visitante.nombre}"
            )

    st.session_state.historial_resultados.append((num, res))
    st.session_state.jornada_actual += 1

    registrar_evento(f"Finalizada la Jornada {num}.")
    return True


def repartir_premios_liga():
    if st.session_state.premios_liga_repartidos:
        return

    tabla = clasificacion()
    for pos, eq in enumerate(tabla, 1):
        premio = PREMIOS_LIGA.get(pos, PREMIO_LIGA_RESTO)
        eq.registrar_ingreso(premio, f"Premio Liga - posición {pos}")
        st.session_state.premios_liga.append({
            "pos": pos,
            "club": eq.nombre,
            "premio": premio,
        })

    st.session_state.premios_liga_repartidos = True
    registrar_evento("💰 Premios de Liga repartidos a los 12 clubes.")


# ============================================================
# COPA DE ESPAÑA
# ============================================================

def preparar_copa():
    if st.session_state.get('copa'):
        return

    if st.session_state.jornada_actual <= TOTAL_JORNADAS:
        return

    repartir_premios_liga()
    tabla = clasificacion()
    top4 = tabla[:4]

    st.session_state.copa = {
        "equipos": [e.nombre for e in top4],
        "semifinales": [],
        "final": None,
        "campeon": None,
        "estado": "semifinales",
    }

    st.session_state.copa_semis_jugadas = False
    st.session_state.copa_final_jugada = False
    registrar_evento(
        "🏆 Copa de España preparada con los cuatro primeros de la Liga."
    )


def jugar_semifinales_copa():
    preparar_copa()
    if not st.session_state.get('copa'):
        return
    if st.session_state.get('copa_semis_jugadas', False):
        return

    nombres = st.session_state.copa["equipos"]
    eq1, eq2, eq3, eq4 = [buscar_equipo(n) for n in nombres]

    gan1, res1 = resultado_eliminatoria(eq1, eq4)
    gan2, res2 = resultado_eliminatoria(eq2, eq3)

    st.session_state.copa["semifinales"] = [
        {
            "partido": f"{eq1.nombre} vs {eq4.nombre}",
            "resultado": res1,
            "ganador": gan1.nombre,
        },
        {
            "partido": f"{eq2.nombre} vs {eq3.nombre}",
            "resultado": res2,
            "ganador": gan2.nombre,
        },
    ]
    st.session_state.copa["estado"] = "final"
    st.session_state.copa_semis_jugadas = True
    registrar_evento("🔥 Semifinales de Copa de España jugadas.")


def jugar_final_copa():
    if not st.session_state.get('copa_semis_jugadas', False):
        return
    if st.session_state.get('copa_final_jugada', False):
        return

    ganadores = [
        buscar_equipo(x["ganador"])
        for x in st.session_state.copa["semifinales"]
    ]

    campeon, resultado = resultado_eliminatoria(ganadores[0], ganadores[1])

    st.session_state.copa["final"] = {
        "partido": f"{ganadores[0].nombre} vs {ganadores[1].nombre}",
        "resultado": resultado,
    }
    st.session_state.copa["campeon"] = campeon.nombre
    st.session_state.copa["estado"] = "terminada"
    st.session_state.copa_final_jugada = True

    campeon.registrar_ingreso(PREMIO_COPA, "Premio campeón Copa de España")
    campeon.titulos += 1
    st.session_state.campeon_copa = campeon.nombre

    registrar_evento(
        f"🏆 {campeon.nombre} es campeón de Copa y recibe {dinero(PREMIO_COPA)}."
    )


# ============================================================
# MUNDIAL DE CLUBES — 3 CLUBES EXTRANJEROS CREADOS POR IA
# ============================================================

PAISES_MUNDIAL = [
    ("Inglaterra", "🏴"),
    ("Brasil", "🇧🇷"),
    ("Japón", "🇯🇵"),
    ("Italia", "🇮🇹"),
    ("Alemania", "🇩🇪"),
    ("Francia", "🇫🇷"),
    ("Argentina", "🇦🇷"),
    ("Portugal", "🇵🇹"),
    ("México", "🇲🇽"),
    ("Corea del Sur", "🇰🇷"),
]

NOMBRES_EXTRANJEROS = {
    "Inglaterra": ["London Royals", "Manchester Titans", "Red Crown FC"],
    "Brasil": ["Rio Imperial", "Sao Paulo Kings", "Amazonia FC"],
    "Japón": ["Tokyo Phoenix", "Osaka Samurai", "Kyoto Stars"],
    "Italia": ["Milano Elite", "Roma Gladiators", "Torino Calcio"],
    "Alemania": ["Berlin Kaiser", "Munich Wolves", "Hamburg United"],
    "Francia": ["Paris Royale", "Lyon Stars", "Monaco Titans"],
    "Argentina": ["Buenos Aires FC", "Patagonia Kings", "Rosario Elite"],
    "Portugal": ["Lisbon Dragons", "Porto Legends", "Braga Royal"],
    "México": ["Mexico Azteca", "Monterrey Gold", "Tijuana Stars"],
    "Corea del Sur": ["Seoul Phoenix", "Busan Tigers", "Incheon FC"],
}


def generar_equipo_mundial(id_club, usados):
    pais, emoji_pais = random.choice(PAISES_MUNDIAL)
    candidatos = [n for n in NOMBRES_EXTRANJEROS[pais] if n not in usados]
    nombre = random.choice(candidatos or NOMBRES_EXTRANJEROS[pais])
    usados.add(nombre)

    emoji_club = random.choice(["🌟", "🐉", "🦁", "🐺", "🔥", "👑", "⚡"])
    estilo = random.choice(ESTILOS_IA)
    eq = Equipo(
        id_club,
        nombre,
        emoji_club,
        f"mundial{id_club}",
        False,
        pais,
    )
    eq.presidente = f"🤖 IA {nombre}"
    eq.estilo_ia = estilo
    eq.presupuesto = random.randint(120, 260) * 1_000_000
    eq.plantilla = generar_plantilla_base(70, 84)

    return eq


def crear_mundial():
    if st.session_state.mundial:
        return

    if not st.session_state.campeon_copa:
        return

    usados = set()
    extranjeros = [
        generar_equipo_mundial(100 + i, usados)
        for i in range(1, 4)
    ]

    st.session_state.equipos_mundial = extranjeros
    campeon = buscar_equipo(st.session_state.campeon_copa)

    st.session_state.mundial = {
        "campeon_espana": campeon.nombre,
        "extranjeros": [e.nombre for e in extranjeros],
        "semifinales": [],
        "final": None,
        "campeon": None,
        "estado": "semifinales",
    }
    st.session_state.mundial_semis_jugadas = False
    st.session_state.mundial_final_jugada = False

    registrar_evento(
        "🌍 La IA ha creado 3 clubes extranjeros para el Mundial de Clubes."
    )


def jugar_semifinales_mundial():
    crear_mundial()
    if not st.session_state.mundial:
        return
    if st.session_state.get('mundial_semis_jugadas', False):
        return

    campeon = buscar_equipo(st.session_state.mundial["campeon_espana"])
    extranjeros = st.session_state.equipos_mundial

    todos = [campeon] + extranjeros
    random.shuffle(todos)

    gan1, res1 = resultado_eliminatoria(todos[0], todos[1])
    gan2, res2 = resultado_eliminatoria(todos[2], todos[3])

    st.session_state.mundial["semifinales"] = [
        {
            "partido": f"{todos[0].nombre} vs {todos[1].nombre}",
            "resultado": res1,
            "ganador": gan1.nombre,
        },
        {
            "partido": f"{todos[2].nombre} vs {todos[3].nombre}",
            "resultado": res2,
            "ganador": gan2.nombre,
        },
    ]
    st.session_state.mundial["estado"] = "final"
    st.session_state.mundial_semis_jugadas = True

    registrar_evento("🔥 Semifinales del Mundial de Clubes jugadas.")


def jugar_final_mundial():
    if not st.session_state.get('mundial_semis_jugadas', False):
        return
    if st.session_state.get('mundial_final_jugada', False):
        return

    ganadores = [
        buscar_equipo(x["ganador"]) or
        next(
            (e for e in st.session_state.equipos_mundial
             if e.nombre == x["ganador"]),
            None,
        )
        for x in st.session_state.mundial["semifinales"]
    ]

    campeon, resultado = resultado_eliminatoria(ganadores[0], ganadores[1])

    st.session_state.mundial["final"] = {
        "partido": f"{ganadores[0].nombre} vs {ganadores[1].nombre}",
        "resultado": resultado,
    }
    st.session_state.mundial["campeon"] = campeon.nombre
    st.session_state.mundial["estado"] = "terminado"
    st.session_state.mundial_final_jugada = True

    # Si es uno de los 12 clubes, recibe el premio en su presupuesto.
    if campeon in st.session_state.equipos:
        campeon.registrar_ingreso(PREMIO_MUNDIAL, "Premio campeón Mundial de Clubes")
        campeon.titulos += 1

    registrar_evento(
        f"🌍 {campeon.nombre} es campeón del Mundial y gana {dinero(PREMIO_MUNDIAL)}."
    )


# ============================================================
# IA DE LOS CLUBES
# ============================================================

def ejecutar_ia():
    bots = [
        e for e in st.session_state.equipos
        if not e.es_humano
    ]

    for bot in bots:
        if not bot.plantilla:
            continue

        # Mercado/cláusulas: la IA busca mejorar según su estilo.
        if random.random() < 0.35:
            otros = [
                e for e in st.session_state.equipos
                if e.id_club != bot.id_club and e.plantilla
            ]
            if otros:
                objetivo = random.choice(otros)
                candidatos = sorted(
                    objetivo.plantilla,
                    key=lambda j: j.grl,
                    reverse=True,
                )
                jugador = candidatos[0]

                limite = {
                    "Galáctico": 1.25,
                    "Agresivo": 1.10,
                    "Ahorrador": 0.80,
                    "Estratega": 1.00,
                    "Jóvenes": 0.95,
                    "Equilibrado": 1.00,
                }.get(getattr(bot, 'estilo_ia', 'Equilibrado'), 1.0)

                if (
                    jugador.grl >= bot.calcular_media_equipo()
                    and bot.presupuesto >= jugador.clausula
                    and bot.presupuesto >= jugador.clausula / limite
                ):
                    bot.registrar_gasto(
                        jugador.clausula,
                        f"IA pagó cláusula de {jugador.nombre}",
                    )
                    objetivo.presupuesto += jugador.clausula
                    objetivo.ingresos += jugador.clausula
                    objetivo.plantilla.remove(jugador)
                    bot.plantilla.append(jugador)
                    registrar_evento(
                        f"🤖 {bot.nombre} pagó la cláusula de "
                        f"{jugador.nombre} a {objetivo.nombre}."
                    )

        # La IA ajusta el estilo de forma ocasional.
        if random.random() < 0.15:
            bot.estilo_ia = random.choice(ESTILOS_IA)


# ============================================================
# SUBASTA
# ============================================================

def iniciar_siguiente_subasta():
    pool = st.session_state.get("mercado_pool", [])
    if not pool:
        st.session_state.subasta_actual = None
        st.session_state.subasta_activa = False
        st.session_state.hora_fin_subasta = None
        return

    idx = max(0, min(int(st.session_state.get("subasta_idx", 0)), len(pool) - 1))
    st.session_state.subasta_idx = idx
    st.session_state.subasta_actual = pool[idx]
    st.session_state.puja_max = int(st.session_state.subasta_actual.valor_base)
    st.session_state.lider_puja_eq = None
    st.session_state.subasta_activa = True
    st.session_state.hora_fin_subasta = datetime.datetime.now() + datetime.timedelta(hours=1)


def ejecutar_bots_subasta():
    if not st.session_state.get("subasta_activa", False):
        return

    jugador = st.session_state.get("subasta_actual")
    if jugador is None:
        return

    for bot in st.session_state.equipos:
        if bot.es_humano:
            continue

        margen = {
            "Galáctico": 1.60,
            "Agresivo": 1.35,
            "Ahorrador": 0.95,
            "Estratega": 1.15,
            "Jóvenes": 1.05,
            "Equilibrado": 1.20,
        }.get(getattr(bot, "estilo_ia", "Equilibrado"), 1.20)

        if bot.presupuesto > st.session_state.puja_max + 2_000_000 and random.random() < 0.30:
            nueva = st.session_state.puja_max + random.randint(1, 6) * 1_000_000
            maximo = int(jugador.valor_base * margen)
            if nueva <= bot.presupuesto and nueva <= maximo:
                st.session_state.puja_max = nueva
                st.session_state.lider_puja_eq = bot


def cerrar_subasta(automatico=False):
    jugador = st.session_state.get("subasta_actual")
    if jugador is None:
        return

    ganador = st.session_state.get("lider_puja_eq")

    if ganador is not None and ganador.presupuesto >= st.session_state.puja_max:
        ganador.presupuesto -= st.session_state.puja_max
        ganador.gastos += st.session_state.puja_max
        ganador.plantilla.append(jugador)
        registrar_finanza(
            ganador, "Gasto", st.session_state.puja_max,
            f"Subasta de {jugador.nombre}",
        )
        registrar_evento(
            f"🔥 {ganador.nombre} ganó la subasta de {jugador.nombre} "
            f"por {dinero(st.session_state.puja_max)}."
        )
    else:
        registrar_evento(
            f"⏱️ Terminó la subasta de {jugador.nombre} sin ganador."
        )

    st.session_state.mercado_pool.pop(st.session_state.subasta_idx)

    if st.session_state.mercado_pool:
        st.session_state.subasta_idx = min(
            st.session_state.subasta_idx,
            len(st.session_state.mercado_pool) - 1,
        )
        iniciar_siguiente_subasta()
    else:
        st.session_state.subasta_actual = None
        st.session_state.subasta_activa = False
        st.session_state.hora_fin_subasta = None

    autosave_partida()


def procesar_reloj_subasta():
    """El bot árbitro cierra la subasta al llegar a 0 y abre el siguiente jugador."""
    if not st.session_state.get("subasta_activa", False):
        return

    fin = st.session_state.get("hora_fin_subasta")
    if fin and datetime.datetime.now() >= fin:
        ejecutar_bots_subasta()
        cerrar_subasta(automatico=True)
    else:
        # Las IAs pueden reaccionar mientras la subasta está abierta.
        ejecutar_bots_subasta()


def pujar_equipo(eq, monto):
    if not st.session_state.get("subasta_activa", False):
        return False, "La subasta ya terminó."
    if monto <= st.session_state.puja_max:
        return False, "La puja debe superar la actual."
    if monto > eq.presupuesto:
        return False, "No tienes presupuesto suficiente."

    st.session_state.puja_max = int(monto)
    st.session_state.lider_puja_eq = eq
    autosave_partida()
    return True, "¡Puja registrada!"


# ============================================================
# MERCADO NEGRO
# ============================================================

def reiniciar_limite_lava_si_corresponde():
    ahora = datetime.datetime.now()
    ventana = st.session_state.get("ventana_ventas_lava")
    if ventana is None or ahora >= ventana + datetime.timedelta(hours=1):
        st.session_state.ventas_lava_hora = {}
        st.session_state.ventana_ventas_lava = ahora.replace(
            minute=0, second=0, microsecond=0
        )


def vender_al_mercado_negro(eq, jugador):
    reiniciar_limite_lava_si_corresponde()
    usados = int(st.session_state.ventas_lava_hora.get(str(eq.id_club), 0))
    if usados >= 4:
        return False, "Has alcanzado el límite de 4 ventas por hora."

    if jugador not in eq.plantilla:
        return False, "Ese jugador ya no pertenece al club."

    precio = int(jugador.valor_base * 0.90)
    eq.plantilla.remove(jugador)
    eq.presupuesto += precio
    eq.ingresos += precio

    st.session_state.ventas_lava_hora[str(eq.id_club)] = usados + 1
    st.session_state.historial_mercado_negro.insert(0, {
        "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "club": eq.nombre,
        "jugador": jugador.nombre,
        "valor": int(jugador.valor_base),
        "cobrado": precio,
    })
    st.session_state.historial_mercado_negro = st.session_state.historial_mercado_negro[:100]

    registrar_finanza(eq, "Ingreso", precio, f"Mercado negro: {jugador.nombre}")
    registrar_evento(
        f"🌋 {eq.nombre} vendió a {jugador.nombre} por "
        f"{dinero(precio)} (90% de su valor)."
    )
    autosave_partida()
    return True, f"🌋 Venta realizada por {dinero(precio)}."


def cobrar_salarios_temporada():
    total = 0
    for eq in st.session_state.equipos:
        salarios = eq.calcular_salarios_totales()
        eq.presupuesto -= salarios
        eq.gastos += salarios
        registrar_finanza(eq, "Gasto", salarios, "Salarios de la temporada")
        total += salarios
    return total


def iniciar_nueva_temporada():
    """Cierra la temporada actual, conserva plantillas/títulos y cobra salarios."""
    if st.session_state.jornada_actual <= TOTAL_JORNADAS:
        return False, "La temporada actual todavía no ha terminado."

    cobrar_salarios_temporada()

    for eq in st.session_state.equipos:
        eq.historial_temporadas.append({
            "temporada": st.session_state.get("temporada", 1),
            "posicion": next(
                (i for i, x in enumerate(clasificacion(), 1) if x.id_club == eq.id_club),
                None,
            ),
            "puntos": eq.puntos,
        })
        eq.puntos = eq.pj = eq.pg = eq.pe = eq.pp = 0
        eq.gf = eq.gc = 0
        eq.premios = eq.ingresos = eq.gastos = 0

    st.session_state.temporada = int(st.session_state.get("temporada", 1)) + 1
    st.session_state.jornada_actual = 1
    st.session_state.calendario = generar_calendario_11()
    st.session_state.historial_resultados = []
    st.session_state.historial_copas = []
    st.session_state.historial_mundial = []
    st.session_state.premios_liga = []
    st.session_state.premios_liga_repartidos = False
    st.session_state.copa = None
    st.session_state.mundial = None
    st.session_state.campeon_copa = None
    st.session_state.equipos_mundial = []
    st.session_state.copa_semis_jugadas = False
    st.session_state.copa_final_jugada = False
    st.session_state.mundial_semis_jugadas = False
    st.session_state.mundial_final_jugada = False
    st.session_state.ofertas_fichaje = []

    # Nueva tanda de subastas.
    st.session_state.mercado_pool = [
        generar_jugador_aleatorio(80, 92) for _ in range(10)
    ]
    st.session_state.subasta_idx = 0
    iniciar_siguiente_subasta()

    st.session_state.ventas_lava_hora = {}
    st.session_state.ventana_ventas_lava = datetime.datetime.now().replace(
        minute=0, second=0, microsecond=0
    )
    st.session_state.historial_mercado_negro = []

    registrar_evento(
        f"🏁 Comenzó la temporada {st.session_state.temporada}. "
        f"Salarios cobrados automáticamente."
    )
    autosave_partida()
    return True, "Nueva temporada iniciada."


# ============================================================
# GUARDADO / CARGA
# ============================================================

def autosave_partida():
    campeon_copa = st.session_state.get("campeon_copa")
    if hasattr(campeon_copa, "nombre"):
        campeon_copa = campeon_copa.nombre

    lider = st.session_state.get("lider_puja_eq")
    lider_nombre = lider.nombre if hasattr(lider, "nombre") else lider

    data = {
        "version": "3.1",
        "temporada": st.session_state.get("temporada", 1),
        "jornada_actual": st.session_state.jornada_actual,
        "calendario": st.session_state.calendario,
        "historial_resultados": st.session_state.historial_resultados,
        "historial_copas": st.session_state.historial_copas,
        "historial_mundial": st.session_state.historial_mundial,
        "historial_finanzas": st.session_state.get("historial_finanzas", []),
        "noticias": st.session_state.get("noticias", []),
        "campeon_copa": campeon_copa,
        "equipos": [e.to_dict() for e in st.session_state.equipos],
        "equipos_mundial": [e.to_dict() for e in st.session_state.get("equipos_mundial", [])],
        "copa": st.session_state.get("copa"),
        "mundial": st.session_state.get("mundial"),
        "premios_liga": st.session_state.get("premios_liga", []),
        "premios_liga_repartidos": st.session_state.get("premios_liga_repartidos", False),
        "copa_semis_jugadas": st.session_state.get("copa_semis_jugadas", False),
        "copa_final_jugada": st.session_state.get("copa_final_jugada", False),
        "mundial_semis_jugadas": st.session_state.get("mundial_semis_jugadas", False),
        "mundial_final_jugada": st.session_state.get("mundial_final_jugada", False),
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
        "mercado_pool": [
            j.to_dict() for j in st.session_state.get("mercado_pool", [])
        ],
        "ventas_lava_hora": st.session_state.get("ventas_lava_hora", {}),
        "ventana_ventas_lava": (
            st.session_state.ventana_ventas_lava.isoformat()
            if st.session_state.get("ventana_ventas_lava") else None
        ),
        "historial_mercado_negro": st.session_state.get("historial_mercado_negro", []),
    }

    with open(ARCHIVO_GUARDADO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cargar_partida():
    if not os.path.exists(ARCHIVO_GUARDADO):
        return False

    try:
        with open(ARCHIVO_GUARDADO, "r", encoding="utf-8") as f:
            data = json.load(f)

        st.session_state.temporada = int(data.get("temporada", 1))
        st.session_state.jornada_actual = int(data.get("jornada_actual", 1))
        st.session_state.calendario = data.get("calendario", [])
        st.session_state.historial_resultados = data.get("historial_resultados", [])
        st.session_state.historial_copas = data.get("historial_copas", [])
        st.session_state.historial_mundial = data.get("historial_mundial", [])
        st.session_state.historial_finanzas = data.get("historial_finanzas", [])
        st.session_state.noticias = data.get("noticias", [])
        st.session_state.equipos = [
            Equipo.from_dict(e) for e in data.get("equipos", [])
        ]

        if not st.session_state.calendario:
            st.session_state.calendario = generar_calendario_11()

        st.session_state.copa = data.get("copa")
        st.session_state.mundial = data.get("mundial")
        st.session_state.premios_liga = data.get("premios_liga", [])
        st.session_state.premios_liga_repartidos = data.get(
            "premios_liga_repartidos", False
        )

        st.session_state.copa_semis_jugadas = data.get(
            "copa_semis_jugadas", False
        )
        st.session_state.copa_final_jugada = data.get(
            "copa_final_jugada", False
        )
        st.session_state.mundial_semis_jugadas = data.get(
            "mundial_semis_jugadas", False
        )
        st.session_state.mundial_final_jugada = data.get(
            "mundial_final_jugada", False
        )

        st.session_state.equipos_mundial = [
            Equipo.from_dict(e)
            for e in data.get("equipos_mundial", [])
        ]

        st.session_state.ofertas_fichaje = data.get("ofertas_fichaje", [])

        pool = data.get("mercado_pool", [])
        st.session_state.mercado_pool = [
            Jugador.from_dict(j) for j in pool
        ]

        st.session_state.subasta_idx = int(data.get("subasta_idx", 0))

        if st.session_state.mercado_pool:
            st.session_state.subasta_idx = min(
                st.session_state.subasta_idx,
                len(st.session_state.mercado_pool) - 1,
            )
            st.session_state.subasta_actual = (
                st.session_state.mercado_pool[st.session_state.subasta_idx]
            )
        else:
            st.session_state.subasta_actual = None

        st.session_state.puja_max = int(data.get("puja_max", 0))
        lider_nombre = data.get("lider_puja_nombre")
        st.session_state.lider_puja_eq = buscar_equipo(lider_nombre) if lider_nombre else None
        st.session_state.subasta_activa = data.get("subasta_activa", False)

        hora = data.get("hora_fin_subasta")
        st.session_state.hora_fin_subasta = (
            datetime.datetime.fromisoformat(hora) if hora else None
        )
        st.session_state.ventas_lava_hora = data.get("ventas_lava_hora", {})
        ventana_lava = data.get("ventana_ventas_lava")
        st.session_state.ventana_ventas_lava = (
            datetime.datetime.fromisoformat(ventana_lava)
            if ventana_lava else datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        )
        st.session_state.historial_mercado_negro = data.get("historial_mercado_negro", [])

        camp_nom = data.get("campeon_copa")
        st.session_state.campeon_copa = camp_nom

        st.session_state.liga_inicializada = True
        return True

    except Exception:
        return False


def inicializar_nueva_partida():
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
    for id_c, nombre, emoji in clubes_info:
        es_humano = False
        eq = Equipo(
            id_c,
            nombre,
            emoji,
            id_c,
            es_humano=es_humano,
            pais="España",
        )
        eq.estilo_ia = random.choice(ESTILOS_IA)
        eq.plantilla = generar_plantilla_base()
        clubes.append(eq)

    st.session_state.equipos = clubes
    st.session_state.temporada = 1
    st.session_state.jornada_actual = 1
    st.session_state.calendario = generar_calendario_11()
    st.session_state.historial_resultados = []
    st.session_state.historial_copas = []
    st.session_state.historial_mundial = []
    st.session_state.historial_finanzas = []
    st.session_state.noticias = []

    st.session_state.copa = None
    st.session_state.mundial = None
    st.session_state.campeon_copa = None
    st.session_state.equipos_mundial = []

    st.session_state.premios_liga = []
    st.session_state.premios_liga_repartidos = False
    st.session_state.copa_semis_jugadas = False
    st.session_state.copa_final_jugada = False
    st.session_state.mundial_semis_jugadas = False
    st.session_state.mundial_final_jugada = False

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
    st.session_state.puja_max = st.session_state.subasta_actual.valor_base
    st.session_state.lider_puja_eq = None
    st.session_state.subasta_activa = False
    st.session_state.hora_fin_subasta = datetime.datetime.now() + datetime.timedelta(hours=1)
    st.session_state.subasta_activa = True
    st.session_state.ventas_lava_hora = {}
    st.session_state.ventana_ventas_lava = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
    st.session_state.historial_mercado_negro = []

    st.session_state.liga_inicializada = True


# ============================================================
# INICIALIZACIÓN
# ============================================================

# ============================================================
# AUTOCORRECCIÓN / MIGRACIÓN BETA 3.1
# ============================================================
def reparar_estado_beta31():
    """Normaliza partidas de Beta 3.1 para evitar AttributeError por estados antiguos."""
    defaults = {
        "copa": None,
        "mundial": None,
        "campeon_copa": None,
        "equipos_mundial": [],
        "historial_resultados": [],
        "historial_copas": [],
        "historial_mundial": [],
        "historial_finanzas": [],
        "noticias": [],
        "premios_liga": [],
        "premios_liga_repartidos": False,
        "copa_semis_jugadas": False,
        "copa_final_jugada": False,
        "mundial_semis_jugadas": False,
        "mundial_final_jugada": False,
        "ofertas_fichaje": [],
        "mercado_pool": [],
        "subasta_idx": 0,
        "puja_max": 0,
        "lider_puja_eq": None,
        "subasta_activa": False,
        "hora_fin_subasta": None,
        "temporada": 1,
        "ventas_lava_hora": {},
        "ventana_ventas_lava": datetime.datetime.now().replace(minute=0, second=0, microsecond=0),
        "historial_mercado_negro": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = list(value) if isinstance(value, list) else value

    equipos = st.session_state.get("equipos", [])
    if not isinstance(equipos, list):
        st.session_state.equipos = []
        equipos = []

    for eq in equipos:
        for jugador in getattr(eq, "plantilla", []):
            jugador.salario = calcular_salario(jugador.valor_base, jugador.grl)
        if not hasattr(eq, "es_humano"):
            eq.es_humano = False
        if not hasattr(eq, "estilo_ia") or eq.estilo_ia not in ESTILOS_IA:
            eq.estilo_ia = random.choice(ESTILOS_IA)
        if not hasattr(eq, "password") or not str(eq.password):
            eq.password = str(getattr(eq, "id_club", 1))
        if not hasattr(eq, "pais") or not eq.pais:
            eq.pais = "España"
        if not hasattr(eq, "presupuesto"):
            eq.presupuesto = PRESUPUESTO_INICIAL
        if not hasattr(eq, "plantilla"):
            eq.plantilla = []

    # El líder de una puja debe apuntar siempre a un objeto Equipo actual.
    lider = st.session_state.get("lider_puja_eq")
    if lider is not None and not hasattr(lider, "id_club"):
        st.session_state.lider_puja_eq = None

    # Si el pool existe pero la referencia del jugador se perdió, la reconstruimos.
    pool = st.session_state.get("mercado_pool", [])
    if pool:
        idx = max(0, min(int(st.session_state.get("subasta_idx", 0)), len(pool) - 1))
        st.session_state.subasta_idx = idx
        actual = st.session_state.get("subasta_actual")
        if actual is None or not hasattr(actual, "nombre"):
            st.session_state.subasta_actual = pool[idx]
    else:
        st.session_state.subasta_actual = None
        st.session_state.subasta_activa = False


if "liga_inicializada" not in st.session_state:
    if not cargar_partida():
        inicializar_nueva_partida()
        autosave_partida()

reparar_estado_beta31()
procesar_reloj_subasta()
reiniciar_limite_lava_si_corresponde()

if "es_admin_autenticado" not in st.session_state:
    st.session_state.es_admin_autenticado = False
if "es_solo_admin" not in st.session_state:
    st.session_state.es_solo_admin = False


# ============================================================
# PORTAL DE ACCESO
# ============================================================

if "mi_equipo" not in st.session_state and not st.session_state.es_solo_admin:
    st.title("🎮 Liga Manager Fantasy — Beta 3.1")
    st.caption("12 clubes · IA · Copa de España · Mundial de Clubes")

    col_jugador, col_admin = st.columns(2)

    with col_jugador:
        st.subheader("⚽ Acceso a Clubes")
        opciones = [
            f"Nº {e.id_club} | {e.emoji} {e.nombre} "
            f"({'Humano' if e.es_humano else '🤖 Bot IA'})"
            for e in st.session_state.equipos
        ]
        eq_login_nombre = st.selectbox("Selecciona tu Club:", opciones)
        nombre_presi_input = st.text_input(
            "Nombre de Presidente (opcional):"
        )
        pwd_login = st.text_input(
            "PIN del Club:",
            type="password",
            key="pwd_club_login",
        )

        if st.button("Ingresar al Club", type="primary"):
            idx = opciones.index(eq_login_nombre)
            eq_obj = st.session_state.equipos[idx]

            if not eq_obj.es_humano:
                st.error("🔒 Este club está controlado por la IA. El Administrador Supremo debe marcarlo como HUMANO.")
            elif pwd_login.strip() == str(eq_obj.password):
                if nombre_presi_input.strip():
                    eq_obj.presidente = nombre_presi_input.strip()
                autosave_partida()
                st.session_state.mi_equipo = eq_obj
                st.success(f"¡Bienvenido a {eq_obj.nombre}!")
                st.rerun()
            else:
                st.error("PIN incorrecto.")

    with col_admin:
        st.subheader("👑 Administrador Supremo")
        pwd = st.text_input(
            "Clave de Administrador Supremo:",
            type="password",
            key="pwd_admin_main",
        )
        if st.button("Entrar como Administrador"):
            if pwd == CLAVE_ADMIN:
                st.session_state.es_solo_admin = True
                st.session_state.es_admin_autenticado = True
                st.rerun()
            else:
                st.error("Clave incorrecta.")

    st.stop()


# Refresca referencia del club conectado
if not st.session_state.es_solo_admin and "mi_equipo" in st.session_state:
    nombre_actual = st.session_state.mi_equipo.nombre
    encontrado = next(
        (e for e in st.session_state.equipos if e.nombre == nombre_actual),
        None,
    )
    if encontrado is not None:
        st.session_state.mi_equipo = encontrado
    else:
        st.session_state.pop("mi_equipo", None)
        st.rerun()


# ============================================================
# BARRA LATERAL
# ============================================================

if st.session_state.es_solo_admin:
    st.sidebar.title("👑 Administrador")
    st.sidebar.write("Rol: **Comisionado Supremo**")
    st.sidebar.write(f"Temporada: **{st.session_state.get('temporada', 1)}**")
else:
    mi_eq = st.session_state.mi_equipo
    st.sidebar.title(f"👤 {mi_eq.presidente}")
    st.sidebar.write(
        f"Temporada {st.session_state.get('temporada', 1)} · Club Nº {mi_eq.id_club}: **{mi_eq.emoji} {mi_eq.nombre}**"
    )
    st.sidebar.write(f"Presupuesto: **{dinero(mi_eq.presupuesto)}**")
    st.sidebar.write(
        f"Salarios: **{dinero(mi_eq.calcular_salarios_totales())}**"
    )
    st.sidebar.write(f"Media: **{mi_eq.calcular_media_equipo()} ⭐**")

st.sidebar.write(
    f"Jornada Liga: **{min(st.session_state.jornada_actual, TOTAL_JORNADAS)} / {TOTAL_JORNADAS}**"
)
st.sidebar.markdown("---")

if st.sidebar.button("🚪 Salir / Cerrar Sesión"):
    st.session_state.pop("mi_equipo", None)
    st.session_state.es_solo_admin = False
    st.session_state.es_admin_autenticado = False
    st.rerun()

opciones_menu = [
    "🏠 Inicio",
    "📊 Clasificación",
    "📋 Mi Plantilla",
    "🔥 Subastas",
    "🌋 Mercado Negro",
    "🤝 Mercado & Cláusulas",
    "🏆 Competiciones",
    "⚽ Resultados",
    "📰 Noticias",
    "⚡ Pro Admin",
]

if st.session_state.es_solo_admin:
    opciones_menu.remove("📋 Mi Plantilla")

menu = st.sidebar.radio("Navegación", opciones_menu)


# ============================================================
# INICIO
# ============================================================

if menu == "🏠 Inicio":
    st.title("⚽ Liga Manager Fantasy — BETA 3.1")
    st.subheader("Tu carrera de manager empieza aquí.")

    tabla = clasificacion()
    posicion_usuario = None

    if not st.session_state.es_solo_admin:
        for i, eq in enumerate(tabla, 1):
            if eq.nombre == st.session_state.mi_equipo.nombre:
                posicion_usuario = i
                break

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Jornada",
        f"{min(st.session_state.jornada_actual, 11)}/11",
    )

    if st.session_state.es_solo_admin:
        c2.metric("Clubes", "12")
        c3.metric("Bots IA", sum(not e.es_humano for e in st.session_state.equipos))
        c4.metric("Estado", "ADMIN")
    else:
        c2.metric("Posición", f"{posicion_usuario}º")
        c3.metric("Media", f"{st.session_state.mi_equipo.calcular_media_equipo()} ⭐")
        c4.metric("Presupuesto", dinero(st.session_state.mi_equipo.presupuesto))

    st.markdown("---")
    st.subheader("🏆 Camino al Mundial de Clubes")

    pasos = [
        ("1", "Liga", "11 jornadas"),
        ("2", "Copa de España", "Top 4"),
        ("3", "Mundial de Clubes", "Campeón de Copa"),
        ("4", "🏆 Mundial", "70 M€"),
    ]
    cols = st.columns(4)
    for col, (num, titulo, sub) in zip(cols, pasos):
        with col:
            st.info(f"### {num}\n**{titulo}**\n\n{sub}")

    st.markdown("---")
    st.subheader("📰 Últimas noticias")
    for noticia in st.session_state.get("noticias", [])[:5]:
        st.write(
            f"**{noticia['fecha']}** — {noticia['texto']}"
        )


# ============================================================
# CLASIFICACIÓN
# ============================================================

elif menu == "📊 Clasificación":
    st.header("🏆 Tabla de Posiciones")

    tabla = clasificacion()
    datos = []

    for idx, eq in enumerate(tabla, 1):
        if idx <= 4:
            zona = "🏆 COPA"
        else:
            zona = "❌ FUERA"

        premio = PREMIOS_LIGA.get(idx, PREMIO_LIGA_RESTO)

        datos.append({
            "Pos": idx,
            "Club": f"{eq.emoji} {eq.nombre}",
            "Control": "👤 Humano" if eq.es_humano else "🤖 Bot IA",
            "Pts": eq.puntos,
            "PJ": eq.pj,
            "PG": eq.pg,
            "PE": eq.pe,
            "PP": eq.pp,
            "GF": eq.gf,
            "GC": eq.gc,
            "DG": eq.dg,
            "Media": eq.calcular_media_equipo(),
            "Presupuesto": dinero(eq.presupuesto),
            "Premio Liga": dinero(premio),
            "Destino": zona,
        })

    st.dataframe(datos, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("💰 Premios oficiales de Liga")

    premio_cols = st.columns(5)
    premios_mostrar = [
        ("🥇 1.º", 30_000_000),
        ("🥈 2.º", 10_000_000),
        ("🥉 3.º", 7_000_000),
        ("4️⃣ 4.º", 5_000_000),
        ("5.º–12.º", 1_000_000),
    ]
    for col, (nombre, premio) in zip(premio_cols, premios_mostrar):
        col.metric(nombre, dinero(premio))


# ============================================================
# MI PLANTILLA
# ============================================================

elif menu == "📋 Mi Plantilla":
    mi_eq = st.session_state.mi_equipo
    st.header(f"🛡️ Plantilla — {mi_eq.nombre}")

    TACTICAS = {
        "4-3-3": ["POR", "DEF", "DEF", "DEF", "MED", "MED", "MED", "DEL", "DEL", "DEL", "DEF"],
        "4-4-2": ["POR", "DEF", "DEF", "DEF", "MED", "MED", "MED", "MED", "DEL", "DEL", "DEF"],
        "3-5-2": ["POR", "DEF", "DEF", "MED", "MED", "MED", "MED", "MED", "DEL", "DEL", "DEF"],
        "5-3-2": ["POR", "DEF", "DEF", "DEF", "DEF", "MED", "MED", "MED", "DEL", "DEL", "DEF"],
    }

    key_esquema = f"esquema_{mi_eq.id_club}"
    if key_esquema not in st.session_state:
        st.session_state[key_esquema] = "4-3-3"

    esquema = st.selectbox(
        "📐 Formación:",
        list(TACTICAS.keys()),
        index=list(TACTICAS.keys()).index(st.session_state[key_esquema]),
    )
    st.session_state[key_esquema] = esquema

    st.subheader("⚽ Selección del 11 titular")

    key_titulares = f"titulares_{mi_eq.id_club}"
    previos = st.session_state.get(key_titulares, [])
    nuevos = []

    for idx, pos in enumerate(TACTICAS[esquema]):
        candidatos = [
            j for j in mi_eq.plantilla
            if j.posicion == pos and j.nombre not in nuevos
        ]
        if not candidatos:
            candidatos = [
                j for j in mi_eq.plantilla
                if j.nombre not in nuevos
            ]
        if not candidatos:
            continue

        candidatos = sorted(
            candidatos,
            key=lambda j: j.grl,
            reverse=True,
        )
        etiquetas = [
            f"{j.nombre} ({j.posicion} · {j.grl})"
            for j in candidatos
        ]

        defecto = 0
        if idx < len(previos):
            for k, j in enumerate(candidatos):
                if j.nombre == previos[idx]:
                    defecto = k
                    break

        elegido = st.selectbox(
            f"Puesto {idx + 1} · {pos}",
            etiquetas,
            index=defecto,
            key=f"slot_{mi_eq.id_club}_{idx}",
        )
        jugador_elegido = candidatos[etiquetas.index(elegido)]
        nuevos.append(jugador_elegido.nombre)

    st.session_state[key_titulares] = nuevos

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Media 11", f"{mi_eq.calcular_media_equipo()} ⭐")
    c2.metric("Jugadores", len(mi_eq.plantilla))
    c3.metric("Salarios", dinero(mi_eq.calcular_salarios_totales()))
    c4.metric("Presupuesto", dinero(mi_eq.presupuesto))

    st.markdown("---")
    datos = []
    for j in mi_eq.plantilla:
        datos.append({
            "Estado": "🟢 Titular" if j.nombre in nuevos else "⚪ Suplente",
            "Jugador": j.nombre,
            "Posición": j.posicion,
            "GRL": j.grl,
            "Valor": dinero(j.valor_base),
            "Cláusula": dinero(j.clausula),
            "Salario": dinero(j.salario),
        })

    st.dataframe(datos, use_container_width=True, hide_index=True)


# ============================================================
# SUBASTAS
# ============================================================

elif menu == "🔥 Subastas":
    st.header("🔥 Subastas — 1 jugador por hora")
    st.caption("⏱️ El árbitro IA cierra automáticamente cada subasta al terminar la hora.")

    jugador = st.session_state.get("subasta_actual")
    fin = st.session_state.get("hora_fin_subasta")

    if jugador is None:
        st.success("🎉 No quedan jugadores en el mercado de subastas.")
    else:
        if fin:
            restantes = max(0, int((fin - datetime.datetime.now()).total_seconds()))
            horas, rem = divmod(restantes, 3600)
            minutos, segundos = divmod(rem, 60)
            st.metric("⏳ Tiempo restante", f"{horas:02d}:{minutos:02d}:{segundos:02d}")

        st.subheader(f"{jugador.nombre} · {jugador.posicion} · ⭐ {jugador.grl}")
        c1,c2,c3=st.columns(3)
        c1.metric("Valor base", dinero(jugador.valor_base))
        c2.metric("Puja actual", dinero(st.session_state.puja_max))
        c3.metric("Estado", "🔥 ABIERTA" if st.session_state.subasta_activa else "⏸️ CERRADA")

        if st.session_state.get("lider_puja_eq"):
            st.info(
                f"👑 Líder: **{st.session_state.lider_puja_eq.nombre}** · "
                f"{dinero(st.session_state.puja_max)}"
            )
        else:
            st.info("Nadie lidera todavía.")

        if not st.session_state.es_solo_admin:
            mi_eq = st.session_state.mi_equipo
            monto = st.number_input(
                "Tu oferta (€)",
                min_value=int(st.session_state.puja_max + 1_000_000),
                max_value=int(max(mi_eq.presupuesto, st.session_state.puja_max + 1_000_000)),
                value=int(st.session_state.puja_max + 1_000_000),
                step=1_000_000,
                key="puja_31",
            )
            if st.button("💰 PUJAR", type="primary"):
                ok,msg=pujar_equipo(mi_eq,int(monto))
                if ok:
                    st.success(msg); st.rerun()
                else:
                    st.error(msg)

        if st.session_state.get("es_admin_autenticado", False):
            st.markdown("---")
            st.caption("🔐 Control Supremo")
            if st.button("🛑 Cerrar subasta ahora", type="secondary"):
                cerrar_subasta()
                st.success("Subasta cerrada por el Administrador Supremo.")
                st.rerun()
        else:
            st.caption("🔒 El cierre manual está reservado al Administrador Supremo; el cierre normal lo realiza automáticamente el árbitro IA.")


# ============================================================
# MERCADO & CLÁUSULAS
# ============================================================

elif menu == "🌋 Mercado Negro":
    st.header("🌋 Mercado Negro")
    st.caption("Vende jugadores al mercado negro por el 90% de su valor. Máximo: 4 jugadores por club y hora.")

    if st.session_state.es_solo_admin:
        st.info("El Mercado Negro se gestiona desde la vista de cada club.")
    else:
        mi_eq = st.session_state.mi_equipo
        reiniciar_limite_lava_si_corresponde()
        usados = int(st.session_state.ventas_lava_hora.get(str(mi_eq.id_club), 0))
        restantes = max(0, 4 - usados)

        c1,c2,c3=st.columns(3)
        c1.metric("Ventas usadas", usados)
        c2.metric("Ventas disponibles", restantes)
        c3.metric("Ventana", "1 hora")

        if mi_eq.plantilla and restantes > 0:
            etiquetas=[f"{i} · {j.nombre} · GRL {j.grl} · {dinero(j.valor_base)}" for i,j in enumerate(mi_eq.plantilla)]
            sel=st.selectbox("Jugador que irá al mercado negro", etiquetas)
            jugador=mi_eq.plantilla[etiquetas.index(sel)]
            cobro=int(jugador.valor_base*0.90)

            st.warning(
                f"🌋 Se elimina de tu plantilla y recibes **{dinero(cobro)}** "
                f"(90% de {dinero(jugador.valor_base)})."
            )
            if st.button("🌋 VENDER AL MERCADO NEGRO", type="primary"):
                ok,msg=vender_al_mercado_negro(mi_eq,jugador)
                if ok:
                    st.success(msg); st.rerun()
                else:
                    st.error(msg)
        elif not mi_eq.plantilla:
            st.info("No tienes jugadores para vender.")
        else:
            st.warning("Has alcanzado las 4 ventas de esta hora.")

        st.markdown("---")
        st.subheader("📜 Últimas operaciones")
        operaciones=[
            x for x in st.session_state.get("historial_mercado_negro",[])
            if x["club"]==mi_eq.nombre
        ][:20]
        if operaciones:
            for op in operaciones:
                st.write(f"🌋 {op['fecha']} · {op['jugador']} · +{dinero(op['cobrado'])}")
        else:
            st.info("Todavía no has realizado ventas.")
elif menu == "🤝 Mercado & Cláusulas":
    st.header("🤝 Mercado de Fichajes")

    tab_neg, tab_clausulas, tab_bandeja = st.tabs([
        "📩 Negociar",
        "⚡ Cláusulas",
        "📥 Ofertas recibidas",
    ])

    with tab_neg:
        if st.session_state.es_solo_admin:
            st.info("Entra a un club para negociar.")
        else:
            mi_eq = st.session_state.mi_equipo
            otros = [
                e for e in st.session_state.equipos
                if e.id_club != mi_eq.id_club
            ]

            destino = st.selectbox(
                "Club vendedor",
                [e.nombre for e in otros],
            )
            eq_dest = buscar_equipo(destino)

            if eq_dest and eq_dest.plantilla:
                jugador_nom = st.selectbox(
                    "Jugador",
                    [j.nombre for j in eq_dest.plantilla],
                )
                jugador = next(
                    j for j in eq_dest.plantilla
                    if j.nombre == jugador_nom
                )

                st.write(
                    f"GRL: **{jugador.grl}** · "
                    f"Valor: **{dinero(jugador.valor_base)}** · "
                    f"Cláusula: **{dinero(jugador.clausula)}**"
                )

                oferta = st.number_input(
                    "Oferta (€)",
                    min_value=1_000_000,
                    value=jugador.valor_base,
                    step=5_000_000,
                )

                if st.button("📤 Enviar oferta"):
                    if oferta <= mi_eq.presupuesto:
                        st.session_state.ofertas_fichaje.append({
                            "comprador": mi_eq.nombre,
                            "vendedor": eq_dest.nombre,
                            "jugador": jugador.nombre,
                            "monto": int(oferta),
                        })
                        autosave_partida()
                        st.success("Oferta enviada.")
                    else:
                        st.error("No tienes suficiente presupuesto.")

    with tab_clausulas:
        if st.session_state.es_solo_admin:
            st.info("Entra como club para pagar cláusulas.")
        else:
            mi_eq = st.session_state.mi_equipo
            opciones = []

            for eq in st.session_state.equipos:
                if eq.id_club == mi_eq.id_club:
                    continue
                for j in eq.plantilla:
                    opciones.append((eq, j))

            if opciones:
                etiquetas = [
                    f"{j.nombre} · {eq.nombre} · {dinero(j.clausula)}"
                    for eq, j in opciones
                ]
                sel = st.selectbox("Jugador", etiquetas)
                eq_prop, jugador = opciones[etiquetas.index(sel)]

                if st.button("🚨 Pagar cláusula"):
                    if mi_eq.presupuesto >= jugador.clausula:
                        mi_eq.registrar_gasto(
                            jugador.clausula,
                            f"Cláusula de {jugador.nombre}",
                        )
                        eq_prop.presupuesto += jugador.clausula
                        eq_prop.ingresos += jugador.clausula
                        eq_prop.plantilla.remove(jugador)
                        mi_eq.plantilla.append(jugador)
                        registrar_evento(
                            f"⚡ {mi_eq.nombre} pagó la cláusula de "
                            f"{jugador.nombre} a {eq_prop.nombre}."
                        )
                        autosave_partida()
                        st.success("¡Fichaje completado!")
                        st.rerun()
                    else:
                        st.error("No tienes dinero suficiente.")

    with tab_bandeja:
        if st.session_state.es_solo_admin:
            st.info("Vista de administrador.")
        else:
            mi_eq = st.session_state.mi_equipo
            ofertas = [
                o for o in st.session_state.ofertas_fichaje
                if o["vendedor"] == mi_eq.nombre
            ]

            if not ofertas:
                st.info("No tienes ofertas pendientes.")
            else:
                for i, oferta in enumerate(ofertas):
                    st.write(
                        f"📌 **{oferta['comprador']}** ofrece "
                        f"**{dinero(oferta['monto'])}** por "
                        f"**{oferta['jugador']}**"
                    )

                    ca, cr = st.columns(2)
                    with ca:
                        if st.button("✅ Aceptar", key=f"aceptar_{i}"):
                            comprador = buscar_equipo(oferta["comprador"])
                            jugador = next(
                                (
                                    j for j in mi_eq.plantilla
                                    if j.nombre == oferta["jugador"]
                                ),
                                None,
                            )

                            if jugador and comprador and comprador.presupuesto >= oferta["monto"]:
                                comprador.registrar_gasto(
                                    oferta["monto"],
                                    f"Fichaje de {jugador.nombre}",
                                )
                                mi_eq.presupuesto += oferta["monto"]
                                mi_eq.ingresos += oferta["monto"]
                                mi_eq.plantilla.remove(jugador)
                                comprador.plantilla.append(jugador)
                                st.session_state.ofertas_fichaje.remove(oferta)
                                registrar_evento(
                                    f"🤝 {comprador.nombre} fichó a "
                                    f"{jugador.nombre} desde {mi_eq.nombre}."
                                )
                                autosave_partida()
                                st.rerun()
                            else:
                                st.error("La operación ya no es posible.")

                    with cr:
                        if st.button("❌ Rechazar", key=f"rechazar_{i}"):
                            st.session_state.ofertas_fichaje.remove(oferta)
                            autosave_partida()
                            st.rerun()


# ============================================================
# COMPETICIONES
# ============================================================

elif menu == "🏆 Competiciones":
    st.header("🏆 Competiciones")

    tab_copa, tab_mundial = st.tabs([
        "🇪🇸 Copa de España",
        "🌍 Mundial de Clubes",
    ])

    with tab_copa:
        if st.session_state.jornada_actual <= TOTAL_JORNADAS:
            st.info(
                "La Copa se desbloquea cuando terminan las 11 jornadas de Liga."
            )
            faltan = TOTAL_JORNADAS - st.session_state.jornada_actual + 1
            st.write(f"Jornadas pendientes: **{max(0, faltan)}**")
        else:
            preparar_copa()

            tabla = clasificacion()
            st.subheader("🎟️ Clasificados")
            for i, eq in enumerate(tabla[:4], 1):
                st.write(
                    f"**{i}.** {eq.emoji} {eq.nombre}"
                )

            st.markdown("---")

            if not st.session_state.get('copa_semis_jugadas', False):
                if st.button("🔥 Jugar Semifinales de Copa", type="primary"):
                    jugar_semifinales_copa()
                    autosave_partida()
                    st.rerun()
            else:
                st.subheader("🔥 Semifinales")
                for semi in st.session_state.copa["semifinales"]:
                    st.write(semi["resultado"])
                    st.success(f"➡️ Pasa: {semi['ganador']}")

                st.markdown("---")

                if not st.session_state.get('copa_final_jugada', False):
                    if st.button("🏆 Jugar Final de Copa", type="primary"):
                        jugar_final_copa()
                        autosave_partida()
                        st.rerun()
                else:
                    st.subheader("🏆 FINAL DE COPA")
                    st.write(
                        st.session_state.copa["final"]["resultado"]
                    )
                    campeon = st.session_state.copa["campeon"]
                    st.success(
                        f"🏆 CAMPEÓN: **{campeon}** · "
                        f"Premio: **{dinero(PREMIO_COPA)}**"
                    )
                    st.info(
                        "🌍 El campeón obtiene la plaza para el Mundial de Clubes."
                    )

    with tab_mundial:
        if not st.session_state.campeon_copa:
            st.info(
                "El Mundial se desbloquea cuando termina la Copa de España."
            )
        else:
            crear_mundial()

            st.subheader("🌍 Participantes")

            campeon = buscar_equipo(st.session_state.campeon_copa)
            st.write(
                f"🇪🇸 **{campeon.nombre}** — Campeón de Copa"
            )

            for eq in st.session_state.equipos_mundial:
                st.write(
                    f"{eq.emoji} **{eq.nombre}** — {eq.pais} · "
                    f"⭐ {eq.calcular_media_equipo()} · "
                    f"IA: {getattr(eq, 'estilo_ia', 'Equilibrado')}"
                )

            st.markdown("---")

            if not st.session_state.get('mundial_semis_jugadas', False):
                if st.button("🔥 Jugar Semifinales del Mundial", type="primary"):
                    jugar_semifinales_mundial()
                    autosave_partida()
                    st.rerun()
            else:
                st.subheader("🔥 Semifinales")
                for semi in st.session_state.mundial["semifinales"]:
                    st.write(semi["resultado"])
                    st.success(f"➡️ Pasa: {semi['ganador']}")

                st.markdown("---")

                if not st.session_state.get('mundial_final_jugada', False):
                    if st.button("🏆 Jugar Final del Mundial", type="primary"):
                        jugar_final_mundial()
                        autosave_partida()
                        st.rerun()
                else:
                    st.subheader("🏆 FINAL DEL MUNDIAL")
                    st.write(
                        st.session_state.mundial["final"]["resultado"]
                    )
                    st.success(
                        f"🌍 CAMPEÓN DEL MUNDIAL: "
                        f"**{st.session_state.mundial['campeon']}**"
                    )
                    st.info(
                        f"💰 Premio campeón: **{dinero(PREMIO_MUNDIAL)}**"
                    )


# ============================================================
# RESULTADOS
# ============================================================

elif menu == "⚽ Resultados":
    st.header("⚽ Historial de Competiciones")

    tab_liga, tab_copa, tab_mundial = st.tabs([
        "🏆 Liga",
        "🇪🇸 Copa",
        "🌍 Mundial",
    ])

    with tab_liga:
        if not st.session_state.historial_resultados:
            st.info("Todavía no hay jornadas jugadas.")
        else:
            for jornada, resultados in reversed(
                st.session_state.historial_resultados
            ):
                with st.expander(f"Jornada {jornada}"):
                    for resultado in resultados:
                        st.write(resultado)

    with tab_copa:
        if not st.session_state.get('copa'):
            st.info("La Copa todavía no ha comenzado.")
        else:
            for semi in st.session_state.copa.get("semifinales", []):
                st.write(semi["resultado"])
            if st.session_state.copa.get("final"):
                st.write(st.session_state.copa["final"]["resultado"])

    with tab_mundial:
        if not st.session_state.mundial:
            st.info("El Mundial todavía no ha comenzado.")
        else:
            for semi in st.session_state.mundial.get("semifinales", []):
                st.write(semi["resultado"])
            if st.session_state.mundial.get("final"):
                st.write(st.session_state.mundial["final"]["resultado"])


# ============================================================
# NOTICIAS
# ============================================================

elif menu == "📰 Noticias":
    st.header("📰 Noticias de la Liga")

    if not st.session_state.noticias:
        st.info("Todavía no hay noticias.")
    else:
        for noticia in st.session_state.noticias:
            st.write(
                f"**{noticia['fecha']}** · {noticia['texto']}"
            )


# ============================================================
# PRO ADMIN
# ============================================================

elif menu == "⚡ Pro Admin":
    st.header("⚡ Panel Pro Admin — Beta 3.1")
    st.caption("👑 Centro de control: humanos, bots, liga, torneos, finanzas y seguridad.")

    if not st.session_state.es_admin_autenticado:
        pwd = st.text_input(
            "Clave de Administrador Supremo:",
            type="password",
            key="pwd_admin_panel",
        )
        if st.button("Autenticar"):
            if pwd == CLAVE_ADMIN:
                st.session_state.es_admin_autenticado = True
                st.rerun()
            else:
                st.error("Clave incorrecta.")
    else:
        st.success("🔓 Administrador autenticado.")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "⚽ Liga",
            "🏆 Torneos",
            "🤖 Gestión IA",
            "💰 Finanzas",
            "🛠️ Stats & PINs",
        ])

        # ----------------------------------------------------
        # TAB 1 — LIGA
        # ----------------------------------------------------
        with tab1:
            st.subheader(
                f"Simular Jornada {min(st.session_state.jornada_actual, 11)}/11"
            )

            st.markdown("### 👥 Control Supremo de clubes")
            st.caption("Tú decides desde aquí qué clubes son 👤 HUMANOS y cuáles siguen como 🤖 BOT IA.")

            cols = st.columns(3)
            for n, club in enumerate(st.session_state.equipos):
                with cols[n % 3]:
                    estado = "👤 HUMANO" if club.es_humano else "🤖 BOT IA"
                    st.markdown(f"**#{club.id_club} {club.emoji} {club.nombre}**")
                    st.caption(estado)
                    modo = st.radio(
                        "Control",
                        ["🤖 BOT IA", "👤 HUMANO"],
                        index=1 if club.es_humano else 0,
                        horizontal=True,
                        key=f"admin_modo_{club.id_club}",
                        label_visibility="collapsed",
                    )
                    if st.button("Aplicar", key=f"admin_aplicar_{club.id_club}", use_container_width=True):
                        club.es_humano = modo == "👤 HUMANO"
                        if not club.es_humano:
                            club.presidente = f"🤖 Bot {club.nombre}"
                        autosave_partida()
                        st.success(f"{club.nombre} ahora es {modo}.")
                        st.rerun()

            st.markdown("---")

            if st.session_state.jornada_actual <= TOTAL_JORNADAS:
                if st.button(
                    "🚀 Simular Jornada + Acciones IA",
                    type="primary",
                ):
                    ejecutar_ia()
                    simular_jornada()
                    autosave_partida()
                    st.success("¡Jornada simulada!")
                    st.rerun()
            else:
                st.success("🏁 Las 11 jornadas de Liga están terminadas.")
                repartir_premios_liga()

                st.subheader("💰 Premios repartidos")
                for p in st.session_state.premios_liga:
                    st.write(
                        f"{p['pos']}º · {p['club']} · "
                        f"**{dinero(p['premio'])}**"
                    )

                st.markdown("---")
                st.subheader("🔄 Nueva temporada")
                st.caption("Al iniciar la nueva temporada se cobran automáticamente los salarios de todas las plantillas.")
                if st.button("🚀 INICIAR SIGUIENTE TEMPORADA", type="primary"):
                    ok, msg = iniciar_nueva_temporada()
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.warning(msg)

        # ----------------------------------------------------
        # TAB 2 — TORNEOS
        # ----------------------------------------------------
        with tab2:
            st.subheader("🏆 Gestión de Torneos Post-Liga")

            if st.session_state.jornada_actual <= TOTAL_JORNADAS:
                st.warning(
                    "Termina primero las 11 jornadas de Liga."
                )
            else:
                preparar_copa()

                if not st.session_state.get('copa_semis_jugadas', False):
                    if st.button("🔥 Simular Semifinales Copa"):
                        jugar_semifinales_copa()
                        autosave_partida()
                        st.rerun()

                if st.session_state.get('copa_semis_jugadas', False):
                    for semi in st.session_state.copa["semifinales"]:
                        st.write(semi["resultado"])

                if (
                    st.session_state.copa_semis_jugadas
                    and not st.session_state.get('copa_final_jugada', False)
                ):
                    if st.button("🏆 Simular Final Copa"):
                        jugar_final_copa()
                        autosave_partida()
                        st.rerun()

                if st.session_state.get('copa_final_jugada', False):
                    st.success(
                        f"🏆 Campeón Copa: "
                        f"{st.session_state.copa['campeon']} · "
                        f"{dinero(PREMIO_COPA)}"
                    )

                if st.session_state.campeon_copa:
                    crear_mundial()

                    st.markdown("---")
                    st.subheader("🌍 Mundial de Clubes")

                    for eq in st.session_state.equipos_mundial:
                        st.write(
                            f"{eq.emoji} {eq.nombre} · {eq.pais} · "
                            f"⭐ {eq.calcular_media_equipo()} · "
                            f"IA {getattr(eq, 'estilo_ia', 'Equilibrado')}"
                        )

                    if not st.session_state.get('mundial_semis_jugadas', False):
                        if st.button("🔥 Simular Semifinales Mundial"):
                            jugar_semifinales_mundial()
                            autosave_partida()
                            st.rerun()

                    if st.session_state.get('mundial_semis_jugadas', False):
                        for semi in st.session_state.mundial["semifinales"]:
                            st.write(semi["resultado"])

                    if (
                        st.session_state.mundial_semis_jugadas
                        and not st.session_state.mundial_final_jugada
                    ):
                        if st.button("🏆 Simular Final Mundial"):
                            jugar_final_mundial()
                            autosave_partida()
                            st.rerun()

                    if st.session_state.get('mundial_final_jugada', False):
                        st.success(
                            f"🌍 Campeón Mundial: "
                            f"{st.session_state.mundial['campeon']} · "
                            f"{dinero(PREMIO_MUNDIAL)}"
                        )

        # ----------------------------------------------------
        # TAB 3 — IA
        # ----------------------------------------------------
        with tab3:
            st.subheader("🤖 Gestión de Bots IA")

            bots = [
                e for e in st.session_state.equipos
                if not e.es_humano
            ]

            if not bots:
                st.info("No hay clubes controlados por IA.")
            else:
                for bot in bots:
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.write(
                            f"**{bot.emoji} {bot.nombre}**"
                        )
                        st.caption(
                            f"Presupuesto: {dinero(bot.presupuesto)}"
                        )

                    with col2:
                        estilo = st.selectbox(
                            "Estilo",
                            ESTILOS_IA,
                            index=ESTILOS_IA.index(getattr(bot, 'estilo_ia', 'Equilibrado'))
                            if getattr(bot, 'estilo_ia', 'Equilibrado') in ESTILOS_IA
                            else 0,
                            key=f"ia_estilo_{bot.id_club}",
                        )
                        bot.estilo_ia = estilo

                    with col3:
                        st.metric(
                            "Media",
                            bot.calcular_media_equipo(),
                        )

                if st.button("🤖 Ejecutar decisiones IA ahora"):
                    ejecutar_ia()
                    autosave_partida()
                    st.success("Las IAs han tomado decisiones.")
                    st.rerun()

        # ----------------------------------------------------
        # TAB 4 — FINANZAS
        # ----------------------------------------------------
        with tab4:
            st.subheader("💰 Gestor Financiero")

            tabla_fin = []
            for eq in sorted(
                st.session_state.equipos,
                key=lambda x: x.presupuesto,
                reverse=True,
            ):
                tabla_fin.append({
                    "Club": f"{eq.emoji} {eq.nombre}",
                    "Presupuesto": dinero(eq.presupuesto),
                    "Ingresos": dinero(eq.ingresos),
                    "Gastos": dinero(eq.gastos),
                    "Salarios": dinero(eq.calcular_salarios_totales()),
                    "Premios": dinero(eq.premios),
                })

            st.dataframe(
                tabla_fin,
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")
            st.subheader("🧾 Últimos movimientos")

            for mov in reversed(
                st.session_state.get("historial_finanzas", [])
            )[:30]:
                icono = "🟢" if mov["tipo"] == "Ingreso" else "🔴"
                st.write(
                    f"{icono} **{mov['club']}** · "
                    f"{mov['tipo']} · "
                    f"{dinero(mov['cantidad'])} · "
                    f"{mov['motivo']}"
                )

        # ----------------------------------------------------
        # TAB 5 — STATS & PINS
        # ----------------------------------------------------
        with tab5:
            st.subheader("🛠️ Modificar Stats, Presupuesto y PINs")

            nombres = [
                f"{e.id_club} · {e.emoji} {e.nombre}"
                for e in st.session_state.equipos
            ]
            seleccion = st.selectbox(
                "Selecciona club",
                nombres,
            )
            idx = nombres.index(seleccion)
            eq = st.session_state.equipos[idx]

            st.write(
                f"### {eq.emoji} {eq.nombre}"
            )

            col1, col2 = st.columns(2)

            with col1:
                nuevo_presupuesto = st.number_input(
                    "Presupuesto (€)",
                    min_value=0,
                    value=int(eq.presupuesto),
                    step=1_000_000,
                    key=f"budget_{eq.id_club}",
                )
                nuevo_pin = st.text_input(
                    "PIN",
                    value=str(eq.password),
                    key=f"pin_{eq.id_club}",
                )

            with col2:
                nuevo_presidente = st.text_input(
                    "Presidente",
                    value=eq.presidente,
                    key=f"presi_{eq.id_club}",
                )
                nuevo_nombre = st.text_input(
                    "Nombre del club",
                    value=eq.nombre,
                    key=f"clubname_{eq.id_club}",
                )

            if st.button("💾 Guardar datos del club"):
                eq.presupuesto = int(nuevo_presupuesto)
                eq.password = nuevo_pin
                eq.presidente = nuevo_presidente

                if nuevo_nombre.strip() and nuevo_nombre != eq.nombre:
                    antiguo = eq.nombre
                    eq.nombre = nuevo_nombre.strip()
                    registrar_evento(
                        f"🛠️ Admin renombró {antiguo} como {eq.nombre}."
                    )

                autosave_partida()
                st.success("Datos del club actualizados.")
                st.rerun()

            st.markdown("---")
            st.subheader("👤 Editar jugadores")

            if eq.plantilla:
                jugador_nombres = [
                    f"{i} · {j.nombre} · {j.posicion} · GRL {j.grl}"
                    for i, j in enumerate(eq.plantilla)
                ]
                jugador_sel = st.selectbox(
                    "Jugador",
                    jugador_nombres,
                )
                ji = jugador_nombres.index(jugador_sel)
                jugador = eq.plantilla[ji]

                c1, c2, c3 = st.columns(3)
                with c1:
                    grl_nuevo = st.number_input(
                        "GRL",
                        1,
                        99,
                        int(jugador.grl),
                        key=f"grl_{eq.id_club}_{ji}",
                    )
                with c2:
                    valor_nuevo = st.number_input(
                        "Valor (€)",
                        0,
                        1_000_000_000,
                        int(jugador.valor_base),
                        step=1_000_000,
                        key=f"valor_{eq.id_club}_{ji}",
                    )
                with c3:
                    clausula_nueva = st.number_input(
                        "Cláusula (€)",
                        0,
                        2_000_000_000,
                        int(jugador.clausula),
                        step=1_000_000,
                        key=f"clausula_{eq.id_club}_{ji}",
                    )

                salario_nuevo = st.number_input(
                    "Salario (€)",
                    0,
                    200_000_000,
                    int(jugador.salario),
                    step=100_000,
                    key=f"salario_{eq.id_club}_{ji}",
                )

                if st.button("💾 Guardar jugador"):
                    jugador.grl = int(grl_nuevo)
                    jugador.valor_base = int(valor_nuevo)
                    jugador.clausula = int(clausula_nueva)
                    jugador.salario = calcular_salario(jugador.valor_base, jugador.grl)
                    autosave_partida()
                    st.success("Jugador actualizado.")
                    st.rerun()


# ============================================================
# GUARDADO AUTOMÁTICO
# ============================================================

try:
    reparar_estado_beta31()
    autosave_partida()
except Exception:
    pass
