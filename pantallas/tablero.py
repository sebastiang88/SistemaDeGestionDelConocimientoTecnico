# -- Tablero: los indicadores de la documentación, calculados en vivo desde la base.

from contextlib import closing
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

import config
import ui
from core import db, documento, fichas

COLOR_BARRAS = "#2E6DB4"

# Línea base medida sobre 240 casos del archivo real
LINEA_BASE_CATEGORIA = 0
CASOS_LINEA_BASE = 240

MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
PERIODOS = {"Todo": None, "Últimos 30 días": 30, "Últimos 7 días": 7}

ui.encabezado("Tablero", "Indicadores de la documentación técnica del equipo, calculados desde la base.")

with closing(db.conectar()) as conexion:
    lista = fichas.listar(conexion)

if lista.empty:
    st.info("Todavía no hay fichas. Documente un caso en **Casos pendientes** para ver los indicadores.")
    st.stop()

# Las fechas de la base están en UTC
lista["fecha"] = lista["actualizada_en"].map(documento.fecha_local)
lista["minutos"] = [
    (documento.fecha_local(a) - documento.fecha_local(c)).total_seconds() / 60
    for a, c in zip(lista["actualizada_en"], lista["creada_en"])
]
lista["clasificada"] = lista["categoria"] != config.MARCA_SIN_SUSTENTO

# --- Filtros ---
# En una sola fila, arriba de todo: cambian todos los números y gráficos de la pantalla.
f1, f2 = st.columns([2, 1])
periodo = f1.segmented_control("Periodo", list(PERIODOS), default="Todo", key="tablero_periodo") or "Todo"
responsables = sorted(lista["responsable"].dropna().unique())
responsable = f2.selectbox("Responsable", ["Todos", *responsables], key="tablero_responsable")

if PERIODOS[periodo]:
    desde = datetime.now(ZoneInfo(config.ZONA_HORARIA)) - timedelta(days=PERIODOS[periodo])
    lista = lista[lista["fecha"] >= desde]
if responsable != "Todos":
    lista = lista[lista["responsable"] == responsable]

finales = lista[lista["estado"] == "final"]
borradores = lista[lista["estado"] == "borrador"]

if finales.empty:
    st.info("No hay fichas finales con estos filtros.")
    st.stop()

# --- Indicadores ---
# Tiempo con la mediana y no con el promedio
porcentaje = round(100 * finales["clasificada"].mean())
preguntas, sin_responder = int(finales["preguntas"].sum()), int(finales["sin_responder"].sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Fichas finales", len(finales), border=True,
          help=f"{len(borradores)} borradores sin terminar con estos filtros")
c2.metric("Tiempo para documentar", documento.duracion_texto(finales["minutos"].median() * 60), border=True,
          help="Mediana del tiempo desde que se genera el borrador hasta que se guarda la ficha final")
c3.metric("Categoría diligenciada", f"{porcentaje} %", border=True,
          delta=f"{porcentaje - LINEA_BASE_CATEGORIA:+d} pts frente a la línea base",
          help=f"Fichas finales con categoría de causa. Línea base: {LINEA_BASE_CATEGORIA} % en "
               f"{CASOS_LINEA_BASE} casos del archivo de seguimiento")
c4.metric("Preguntas sin responder", sin_responder, border=True,
          help=f"De {preguntas} preguntas hechas en las fichas finales")

motores = finales["motor"].value_counts()
st.caption(
    f"{preguntas / len(finales):.1f} preguntas por ficha en promedio (máximo {config.MAX_PREGUNTAS}) · "
    "Motor que generó el borrador: " + ", ".join(f"{m} {n}" for m, n in motores.items())
)

# --- Gráficos ---
# Una sola serie en cada gráfico, para que se vea la tendencia. La mediana no se ve afectada por un caso raro.
semana = finales["fecha"].map(lambda f: (f - timedelta(days=f.weekday())).date())
conteo = semana.value_counts()
semanas = pd.date_range(min(conteo.index), max(conteo.index), freq="7D").date
por_semana = pd.DataFrame({
    "Semana": [f"{d.day} {MESES[d.month - 1]}" for d in semanas],
    "Fichas": [int(conteo.get(d, 0)) for d in semanas],
})

# Causas por categoría, de la más a la menos frecuente. Las no clasificadas van aparte.
clasificadas = finales[finales["clasificada"]]
por_categoria = (clasificadas["categoria"].map(ui.nombre_categoria).value_counts()
                 .rename_axis("Categoría").reset_index(name="Fichas"))

g1, g2 = st.columns(2)
with g1.container(border=True):
    st.markdown("**Fichas finales por semana**")
    st.bar_chart(por_semana, x="Semana", y="Fichas", color=COLOR_BARRAS, sort=False, height=260,
                 x_label="Semana (desde el lunes)", y_label="Fichas")
with g2.container(border=True):
    st.markdown("**Causas por categoría**")
    if por_categoria.empty:
        st.caption("Ninguna ficha final tiene categoría todavía.")
    else:
        st.bar_chart(por_categoria, x="Categoría", y="Fichas", color=COLOR_BARRAS, horizontal=True,
                     sort="-Fichas", height=260, x_label="Fichas", y_label="")
    st.caption(f"{len(finales) - len(clasificadas)} fichas finales sin categoría ({config.MARCA_SIN_SUSTENTO}).")

with st.expander("Ver los datos de los gráficos"):
    d1, d2 = st.columns(2)
    d1.dataframe(por_semana, hide_index=True, width="stretch")
    d2.dataframe(por_categoria, hide_index=True, width="stretch")

# --- Casos raros y nuevos ---
# Raro: una causa que casi no se repite, o una que nadie supo clasificar. 
st.subheader("Casos raros y nuevos")
columnas_tabla = {
    "ha": "#HA",
    "tipo": "Tipo",
    "responsable": "Responsable",
    "flujo": "Flujo",
    "causa_texto": st.column_config.TextColumn("Categoría de la causa", width="medium"),
    "motivo": "Por qué aparece",
    "documentada": "Documentada",
}


def preparar(tabla, motivo):
    return tabla.assign(
        flujo=[documento.nombre_flujo(i, n) for i, n in zip(tabla["id_flujo"], tabla["flujo"])],
        causa_texto=[config.MARCA_SIN_SUSTENTO if not c else f"{ui.nombre_categoria(a)} / {s}"
                     for c, a, s in zip(tabla["clasificada"], tabla["categoria"], tabla["subcategoria"])],
        motivo=motivo,
        documentada=tabla["fecha"].map(lambda f: f.strftime("%d/%m/%Y %H:%M")),
    )[list(columnas_tabla)]


repeticiones = clasificadas.groupby(["categoria", "subcategoria"])["id"].transform("count")
unicas = clasificadas[repeticiones == 1]
sin_clasificar = finales[~finales["clasificada"]]
raros = pd.concat([
    preparar(sin_clasificar, "Sin categoría: nadie supo clasificarla"),
    preparar(unicas, "Única ficha con esta causa"),
])

nuevos = finales[finales["fecha"] >= datetime.now(ZoneInfo(config.ZONA_HORARIA)) - timedelta(days=7)]
nuevos = preparar(nuevos.sort_values("fecha", ascending=False), "Documentada en los últimos 7 días")

pestana_raros, pestana_nuevos = st.tabs([f"Raros ({len(raros)})", f"Nuevos ({len(nuevos)})"])
with pestana_raros:
    if raros.empty:
        st.caption("Todas las causas se repiten al menos dos veces y todas las fichas tienen categoría.")
    else:
        st.dataframe(raros, column_config=columnas_tabla, hide_index=True, width="stretch")
with pestana_nuevos:
    if nuevos.empty:
        st.caption("No hay fichas finales en los últimos 7 días.")
    else:
        st.dataframe(nuevos, column_config=columnas_tabla, hide_index=True, width="stretch")
st.caption("Para leer una ficha completa, búsquela por su #HA en **Fichas**.")
