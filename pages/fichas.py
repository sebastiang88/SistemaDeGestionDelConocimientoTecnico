# -- Pantalla del módulo 6: consultar y abrir las fichas guardadas.

from contextlib import closing

import pandas as pd
import streamlit as st
import config
import ui
from core import db, fichas

# Fecha guardada en UTC -> hora de Colombia.
def hora_local(fechas):
    return pd.to_datetime(fechas).dt.tz_localize("UTC").dt.tz_convert(config.ZONA_HORARIA)

# Segundos en texto corto.
def duracion_texto(segundos):
    minutos, segundos = divmod(int(segundos), 60)
    return f"{minutos} min {segundos} s" if minutos else f"{segundos} s"

st.title("Fichas")

with closing(db.conectar()) as conexion:
    lista = fichas.listar(conexion)

if lista.empty:
    st.info("Todavía no hay fichas. Documente un caso para crear la primera.")
    st.page_link("pages/casos_pendientes.py", label="Ir a Casos pendientes", icon=":material/assignment:")
    st.stop()

# --- Resumen ---
c1, c2, c3 = st.columns(3)
c1.metric("Fichas finales", int((lista["estado"] == "final").sum()))
c2.metric("Borradores", int((lista["estado"] == "borrador").sum()))
c3.metric("Preguntas sin responder", int(lista["sin_responder"].sum()))

# --- Lista ---
filtro = st.segmented_control("Mostrar", ["Todas", "Finales", "Borradores"], default="Todas")
if filtro == "Finales":
    lista = lista[lista["estado"] == "final"]
elif filtro == "Borradores":
    lista = lista[lista["estado"] == "borrador"]
lista = lista.reset_index(drop=True)

tabla = lista[["ha", "tipo", "responsable", "estado", "motor", "sin_responder", "actualizada_en"]].copy()
tabla["estado"] = tabla["estado"].str.capitalize()
tabla["actualizada_en"] = hora_local(tabla["actualizada_en"]).dt.strftime("%Y-%m-%d %H:%M")

st.markdown("**Seleccione una ficha para abrirla.**")
seleccion = st.dataframe(
    tabla,
    column_config={
        "ha": "#HA",
        "tipo": "Tipo",
        "responsable": "Responsable",
        "estado": "Estado",
        "motor": "Motor",
        "sin_responder": st.column_config.NumberColumn("Sin responder", help="Preguntas que quedaron sin responder"),
        "actualizada_en": "Última modificación",
    },
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    key=f"tabla_fichas_{filtro}",
)

filas = seleccion.selection.rows
if not filas:
    st.stop()

# --- Ficha abierta ---
with closing(db.conectar()) as conexion:
    ficha = fichas.abrir(conexion, int(lista.loc[filas[0], "id"]))

final = ficha["estado"] == "final"
st.subheader(f"HA {ficha['ha']} — {'Ficha final' if final else 'Borrador'}")

creada, modificada = hora_local(pd.Series([ficha["creada_en"], ficha["actualizada_en"]]))
modelo = f" ({ficha['modelo']})" if ficha["modelo"] else ""
detalle = f"Generada con el motor {ficha['motor']}{modelo} el {creada:%Y-%m-%d a las %H:%M}."
if final:
    # Desde que se generó el borrador hasta que se guardó como final.
    detalle += f" Documentada en {duracion_texto((modificada - creada).total_seconds())}."
st.caption(detalle)

izquierda, derecha = st.columns(2)
with izquierda:
    ui.mostrar_caso(ficha)
with derecha:
    with st.container(border=True):
        st.markdown("#### Ficha")
        for campo in config.CAMPOS_FICHA:
            ui.mostrar(ui.ETIQUETAS[campo], ficha[campo])
        ui.mostrar(ui.ETIQUETAS["categoria"], ui.categoria_texto(ficha))

if ficha["preguntas"]:
    st.markdown("**Preguntas al responsable**")
    for pregunta in ficha["preguntas"]:
        st.markdown(f"{pregunta['orden']}. {pregunta['texto']}")
        st.caption(f"Respuesta: {pregunta['respuesta']}" if pregunta["respuesta"] is not None else "Sin responder")

if not final and st.button("Continuar este borrador", type="primary", icon=":material/edit_note:"):
    st.session_state["ficha_id"] = ficha["id"]
    st.session_state.pop("ha_a_documentar", None)
    st.switch_page("pages/documentar.py")