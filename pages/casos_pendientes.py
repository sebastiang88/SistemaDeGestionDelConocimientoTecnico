# -- Pantalla de los módulos 1 y 2

import json
from contextlib import closing

import streamlit as st

import config
from core import carga, db, deteccion, proveedor

st.title("Casos pendientes de documentar")

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
elif archivo is not None and st.session_state.get("nombre_archivo") != archivo.name:
    origen, nombre = archivo, archivo.name

# La detección se hace sólo al cargar el archivo y se guarda en la sesión. 
if origen is not None:
    try:
        casos = carga.cargar(origen)
        documentables = deteccion.filtrar_documentables(casos)
        with closing(db.conectar()) as conexion:
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
c1, c2, c3 = st.columns(3)
c1.metric("Casos en el archivo", len(st.session_state["casos"]))
c2.metric("Cerrados que se documentan", len(st.session_state["documentables"]))
c3.metric("Sin ficha", len(pendientes))

if pendientes.empty:
    st.success("Todos los casos cerrados ya tienen ficha.")
    st.stop()

# --- Tabla de pendientes ---
# La clave incluye el nombre del archivo para que la selección se borre al cargar otro archivo
st.markdown("**Seleccione un caso en la tabla para ver su borrador.**")
seleccion = st.dataframe(
    pendientes[["ha", "tipo", "responsable", "flujo", "descripcion"]],
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

# --- Caso y borrador lado a lado ---
caso = pendientes.iloc[filas[0]]
borrador = json.loads(proveedor.simular(caso))

# Muestra un campo si está vacío o sin sustento lo muestra.
def mostrar(titulo, valor):
    st.markdown(f"**{titulo}**")
    if valor == config.MARCA_SIN_SUSTENTO:
        st.warning(config.MARCA_SIN_SUSTENTO, icon=":material/help:")
    elif carga.normalizar(valor) == "":
        st.caption("Vacío en el archivo")
    else:
        st.write(valor)

st.subheader(f"HA {caso['ha']}")
izquierda, derecha = st.columns(2)

with izquierda:
    with st.container(border=True):
        st.markdown("#### Lo que dice el caso")
        mostrar("Descripción", caso["descripcion"])
        mostrar("Observaciones", caso["observaciones"])
        mostrar("Causa / Solución", caso["causa_solucion"])

with derecha:
    with st.container(border=True):
        st.markdown("#### Borrador propuesto")
        st.caption("Vista previa con el motor simulado. Todavía no se guarda la ficha ni se usa el modelo de lenguaje.")
        etiquetas = {"sintoma": "Síntoma", "causa": "Causa", "solucion": "Solución"}
        for campo in config.CAMPOS_FICHA:
            mostrar(etiquetas[campo], borrador[campo])
        categoria = borrador["categoria"]
        if categoria != config.MARCA_SIN_SUSTENTO:
            categoria = f"{categoria} / {borrador['subcategoria']}"
        mostrar("Categoría de la causa", categoria)

        if borrador["preguntas"]:
            st.markdown("**Preguntas para el responsable**")
            for numero, pregunta in enumerate(borrador["preguntas"], start=1):
                st.write(f"{numero}. {pregunta['texto']}")