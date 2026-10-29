# -- Pantalla del módulo 6: consultar y abrir las fichas guardadas.

from contextlib import closing

import pandas as pd
import streamlit as st
import config
import ui
from core import carga, db, documento, fichas

# Fecha guardada en UTC -> hora de Colombia.
def hora_local(fechas):
    return pd.to_datetime(fechas).dt.tz_localize("UTC").dt.tz_convert(config.ZONA_HORARIA)

ui.encabezado("Fichas", "La base de conocimiento: consulte, abra y descargue las fichas en Word.")

with closing(db.conectar()) as conexion:
    lista = fichas.listar(conexion)

if lista.empty:
    st.info("Todavía no hay fichas. Documente un caso para crear la primera.")
    st.page_link("pantallas/casos_pendientes.py", label="Ir a Casos pendientes", icon=":material/assignment:")
    st.stop()

# --- Resumen ---
c1, c2, c3 = st.columns(3)
c1.metric("Fichas finales", int((lista["estado"] == "final").sum()), border=True)
c2.metric("Borradores", int((lista["estado"] == "borrador").sum()), border=True)
c3.metric("Preguntas sin responder", int(lista["sin_responder"].sum()), border=True)

# --- Búsqueda y filtros ---
total = len(lista)
lista["flujo"] = [documento.nombre_flujo(i, n) for i, n in zip(lista["id_flujo"], lista["flujo"])]
with st.container(key="tarjeta_filtros"):
    busqueda = st.text_input(
        "Buscar",
        placeholder="Número de HA o palabras clave: plantilla, ANS, correo, permisos…",
        icon=":material/search:",
    )
    f1, f2, f3 = st.columns([1.2, 1, 1])
    estado = f1.segmented_control("Estado", ["Todas", "Finales", "Borradores"], default="Todas")
    tipos = f2.multiselect("Tipo", sorted(lista["tipo"].dropna().unique()), placeholder="Todos")
    responsables = f3.multiselect("Responsable", sorted(lista["responsable"].dropna().unique()), placeholder="Todos")

    f4, f5, f6 = st.columns([1.2, 1, 1])
    flujos = f4.multiselect("Flujo", sorted(lista["flujo"].dropna().unique()), placeholder="Todos")
    categorias = sorted(c for c in lista["categoria"].dropna().unique() if c != config.MARCA_SIN_SUSTENTO)
    elegidas = f5.multiselect("Categoría de la causa", categorias, format_func=ui.nombre_categoria, placeholder="Todas")
    subcategorias = sorted(lista.loc[lista["categoria"].isin(elegidas), "subcategoria"].dropna().unique())
    subelegidas = f6.multiselect(
        "Subcategoría", subcategorias, disabled=not elegidas,
        placeholder="Todas" if elegidas else "Elija antes una categoría",
        key=f"filtro_subcategoria_{'|'.join(elegidas)}",
    )

if estado == "Finales":
    lista = lista[lista["estado"] == "final"]
elif estado == "Borradores":
    lista = lista[lista["estado"] == "borrador"]
if tipos:
    lista = lista[lista["tipo"].isin(tipos)]
if responsables:
    lista = lista[lista["responsable"].isin(responsables)]
if elegidas:
    lista = lista[lista["categoria"].isin(elegidas)]
if subelegidas:
    lista = lista[lista["subcategoria"].isin(subelegidas)]
if flujos:
    lista = lista[lista["flujo"].isin(flujos)]

if busqueda.strip():
    campos_texto = ["ha", "descripcion", "sintoma", "causa", "solucion", "categoria", "subcategoria", "lecciones", "flujo"]
    texto = lista[campos_texto].fillna("").astype(str).agg(" ".join, axis=1).map(carga.normalizar)
    palabras = carga.normalizar(busqueda).split()
    lista = lista[texto.map(lambda t: all(p in t for p in palabras))]

lista = lista.reset_index(drop=True)
st.caption(f"{len(lista)} de {total} fichas")
if lista.empty:
    st.info("Ninguna ficha coincide con la búsqueda o los filtros.")
    st.stop()

tabla = lista[["ha", "tipo", "flujo", "responsable", "estado", "motor", "sin_responder", "actualizada_en"]].copy()
tabla["estado"] = tabla["estado"].str.capitalize()
tabla["actualizada_en"] = hora_local(tabla["actualizada_en"]).dt.strftime("%Y-%m-%d %H:%M")

st.markdown("**Seleccione una ficha para abrirla.**")
seleccion = st.dataframe(
    tabla,
    column_config={
        "ha": "#HA",
        "tipo": "Tipo",
        "flujo": "Flujo",
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
    key="tabla_fichas_" + str(abs(hash((busqueda, estado, *tipos, *responsables, *elegidas, *flujos)))),
)

filas = seleccion.selection.rows
if not filas:
    st.stop()

# --- Ficha abierta ---
# El documento se arma de nuevo cada vez que se abre una ficha, a partir de los datos de la base
with closing(db.conectar()) as conexion:
    ficha = fichas.abrir(conexion, int(lista.loc[filas[0], "id"]))

final = ficha["estado"] == "final"
datos = documento.datos_documento(ficha)

boton_word, boton_borrador, _ = st.columns([1, 1, 2])
boton_word.download_button(
    "Descargar en Word",
    data=documento.generar_word(ficha),
    file_name=documento.nombre_archivo(ficha),
    mime=documento.TIPO_WORD,
    type="primary",
    icon=":material/download:",
    width="stretch",
)
if not final and boton_borrador.button("Continuar este borrador", icon=":material/edit_note:", width="stretch"):
    st.session_state["ficha_id"] = ficha["id"]
    st.session_state.pop("ha_a_documentar", None)
    st.switch_page("pantallas/documentar.py")

ui.vista_documento(datos, ficha["estado"])

with st.expander("Ver el caso original"):
    ui.mostrar_caso(ficha)