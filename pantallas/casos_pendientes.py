# -- Pantalla de los módulos 1 y 2

import threading
from contextlib import closing

import streamlit as st

import config
import ui
from core import carga, db, deteccion, documento

ui.encabezado("Casos pendientes", "Cargue el archivo de seguimiento y elija qué caso cerrado documentar.")

# --- Carga del archivo ---
# Los casos se guardan en st.session_state para que no se pierdan cuando Streamlit vuelve a ejecutar la pantalla
columna_subir, columna_ejemplo = st.columns([3, 1])
with columna_subir:
    archivo = st.file_uploader("Archivo de seguimiento (.xlsx)", type=["xlsx"])
with columna_ejemplo:
    st.write("")  
    usar_ejemplo = st.button("Usar archivo de ejemplo", width="stretch")

origen = None
if usar_ejemplo:
    origen, nombre = config.DATA_DIR / "ejemplo" / "casos_ficticios.xlsx", "archivo de ejemplo"
# El cargador conserva el archivo subido en cada ejecución; se carga sólo si es una subida nueva.
elif archivo is not None and archivo.file_id != st.session_state.get("ultima_subida"):
    origen, nombre = archivo, archivo.name
    st.session_state["ultima_subida"] = archivo.file_id
    
@st.cache_resource
def candado_carga():
    return threading.Lock()

# La detección se hace sólo al cargar el archivo y se guarda en la sesión.
if origen is not None:
    with candado_carga():
        ya_cargado = usar_ejemplo and st.session_state.get("nombre_archivo") == nombre and "casos" in st.session_state
        if not ya_cargado:
            try:
                casos = carga.cargar(origen)
                documentables = deteccion.filtrar_documentables(casos)
                with closing(db.conectar()) as conexion:
                    with conexion.transaction():
                        db.actualizar_casos(conexion, casos)
                    pendientes = deteccion.quitar_con_ficha(documentables, conexion)
                st.session_state.update(
                    casos=casos, documentables=documentables, pendientes=pendientes, nombre_archivo=nombre,
                )
            except carga.ErrorCarga as error:
                st.session_state.pop("casos", None)
                st.error(str(error))

if "casos" not in st.session_state:
    st.info("Cargue el archivo de seguimiento o use el archivo de ejemplo para empezar.")
    st.stop()

pendientes = st.session_state["pendientes"]

# --- Resultado de la detección ---
st.caption(f"Archivo: {st.session_state['nombre_archivo']}")
# Los números tienen que sumar a la vista
casos, documentables = st.session_state["casos"], st.session_state["documentables"]
total, n_documentables, n_sin_ficha = len(casos), len(documentables), len(pendientes)
no_aplican = casos[~casos["ha"].isin(documentables["ha"])]
n_evolutivos = int((no_aplican["tipo"].map(carga.normalizar) == "evolutivo").sum())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Casos en el archivo", total, border=True)
c2.metric("Se documentan", n_documentables, border=True,
          help="Incidentes, eventos y controles de cambio cerrados (estado 4.3 o 4.4)")
c3.metric("No aplican", len(no_aplican), border=True,
          help=f"{n_evolutivos} evolutivos y {len(no_aplican) - n_evolutivos} casos todavía abiertos")
c4.metric("Ya tienen ficha", n_documentables - n_sin_ficha, border=True)
c5.metric("Sin ficha", n_sin_ficha, border=True)

if pendientes.empty:
    st.success("Todos los casos cerrados ya tienen ficha.")
    st.stop()

# --- Tabla de pendientes ---
# La clave incluye el nombre del archivo para que la selección se borre al cargar otro archivo
st.markdown("**Seleccione un caso en la tabla para documentarlo.**")
seleccion = st.dataframe(
    pendientes[["ha", "tipo", "responsable", "flujo", "descripcion"]].assign(
        flujo=[documento.nombre_flujo(i, n) for i, n in zip(pendientes["id_flujo"], pendientes["flujo"])]),
    column_config={
        "ha": "#HA",
        "tipo": "Tipo",
        "responsable": "Responsable",
        "flujo": "Flujo",
        "descripcion": st.column_config.TextColumn("Descripción", width="large"),
    },
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    key=f"tabla_{st.session_state['nombre_archivo']}",
)

filas = seleccion.selection.rows
if not filas:
    st.stop()

# --- Caso seleccionado ---
# Aquí sólo se ve el caso, el borrador se genera en Documentar.
caso = pendientes.iloc[filas[0]]
st.subheader(f"HA {caso['ha']}")
ui.mostrar_caso(caso)

if st.button("Documentar este caso", type="primary", icon=":material/edit_note:"):
    st.session_state["ha_a_documentar"] = caso["ha"]
    st.session_state.pop("ficha_id", None)
    st.switch_page("pantallas/documentar.py")