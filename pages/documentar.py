# -- Pantalla de los módulos 3, 4 y 5: generar el borrador, responder las preguntas y guardar.

from contextlib import closing

import streamlit as st
import config
import ui
from core import db, deteccion, fichas, generacion


# Deja la pantalla lista para elegir otro caso.
def soltar_caso():
    st.session_state.pop("ficha_id", None)
    st.session_state.pop("ha_a_documentar", None)
    
st.title("Documentar un caso")

ficha_id = st.session_state.get("ficha_id")
ha = st.session_state.get("ha_a_documentar")

# --- 1. Nada elegido ---
if ficha_id is None and ha is None:
    if aviso := st.session_state.pop("aviso", None):
        st.success(aviso)
    st.info("Elija un caso en **Casos pendientes** para documentarlo.")
    st.page_link("pages/casos_pendientes.py", label="Ir a Casos pendientes", icon=":material/assignment:")

    with closing(db.conectar()) as conexion:
        lista = fichas.listar(conexion)
    borradores = lista[lista["estado"] == "borrador"] if not lista.empty else lista
    if not borradores.empty:
        st.subheader("O continúe un borrador")
        descripcion = {
            fila.id: f"HA {fila.ha} — {fila.sin_responder} sin responder"
            for fila in borradores.itertuples()
        }
        elegido = st.selectbox("Borrador", list(descripcion), format_func=descripcion.get,
                               index=None, placeholder="Elija un borrador")
        if elegido is not None:
            st.session_state["ficha_id"] = int(elegido)
            st.rerun()
    st.stop()

# --- 2. Caso elegido, todavía sin ficha ---
if ficha_id is None:
    pendientes = st.session_state.get("pendientes")
    fila = pendientes[pendientes["ha"] == ha] if pendientes is not None else None
    if fila is None or fila.empty:
        st.warning(f"El caso HA {ha} ya no está entre los pendientes. Vuelva a Casos pendientes.")
        soltar_caso()
        st.stop()

    caso = fila.iloc[0]
    st.subheader(f"HA {ha}")
    ui.mostrar_caso(caso)

    # El borrador se guarda apenas se genera, así no se pierde la llamada al modelo si el usuario cierra la pantalla
    if st.button("Generar borrador", type="primary", icon=":material/auto_awesome:"):
        with st.spinner("Generando el borrador…"):
            borrador = generacion.generar_borrador(caso)
            try:
                with closing(db.conectar()) as conexion:
                    nuevo_id = fichas.guardar_borrador(conexion, caso, borrador)
                    # El caso ya tiene ficha: sale de la lista de pendientes.
                    st.session_state["pendientes"] = deteccion.quitar_con_ficha(
                        st.session_state["documentables"], conexion)
            except fichas.ErrorFicha as error:
                st.error(str(error))
                st.stop()
        st.session_state["ficha_id"] = nuevo_id
        st.session_state.pop("ha_a_documentar", None)
        st.rerun()

    if st.button("Elegir otro caso"):
        soltar_caso()
        st.switch_page("pages/casos_pendientes.py")
    st.stop()

# --- 3. Ficha en curso ---
with closing(db.conectar()) as conexion:
    ficha = fichas.abrir(conexion, ficha_id)
if ficha is None:
    st.error("No se encontró la ficha.")
    soltar_caso()
    st.stop()

final = ficha["estado"] == "final"
st.subheader(f"HA {ficha['ha']}")
modelo = f" ({ficha['modelo']})" if ficha["modelo"] else ""
st.caption(f"Borrador generado con el motor {ficha['motor']}{modelo} en {ficha['duracion_ms'] / 1000:.1f} s.")
if final:
    st.success("Ficha final guardada.", icon=":material/check_circle:")

izquierda, derecha = st.columns(2)
with izquierda:
    ui.mostrar_caso(ficha)
with derecha:
    with st.container(border=True):
        st.markdown("#### Ficha" if final else "#### Borrador propuesto")
        for campo in config.CAMPOS_FICHA:
            ui.mostrar(ui.ETIQUETAS[campo], ficha[campo])
        ui.mostrar(ui.ETIQUETAS["categoria"], ui.categoria_texto(ficha))

# --- Preguntas ---
st.subheader("Preguntas para el responsable")
if not ficha["preguntas"]:
    st.write("El borrador no tiene vacíos: no hay nada que preguntar.")

respuestas = {}
for pregunta in ficha["preguntas"]:
    titulo = f"{pregunta['orden']}. {pregunta['texto']}"
    if pregunta["respuesta"] is not None:
        st.markdown(f"**{titulo}**")
        st.caption(f"Respondida: {pregunta['respuesta']}")
    elif final:
        st.markdown(f"**{titulo}**")
        st.caption("Sin responder")
    elif pregunta["campo"] == "categoria":
        categoria = st.selectbox(titulo, list(config.CATEGORIAS_CAUSA), format_func=ui.nombre_categoria,
                                 index=None, placeholder="Elija una categoría", key=f"cat_{pregunta['id']}")
        subcategoria = st.selectbox("Subcategoría", config.CATEGORIAS_CAUSA.get(categoria, ()),
                                    index=None, placeholder="Elija una subcategoría",
                                    disabled=categoria is None, key=f"sub_{pregunta['id']}")
        if categoria and subcategoria:
            respuestas[pregunta["id"]] = (categoria, subcategoria)
    else:
        respuestas[pregunta["id"]] = st.text_area(titulo, placeholder="Escriba la respuesta",
                                                  key=f"resp_{pregunta['id']}")
# --- Guardar ---
if final:
    if st.button("Documentar otro caso", type="primary"):
        soltar_caso()
        st.switch_page("pages/casos_pendientes.py")
    st.stop()

sin_responder = sum(1 for p in ficha["preguntas"] if p["respuesta"] is None)
if sin_responder:
    st.caption(f"Puede guardar la ficha final aunque queden preguntas sin responder: "
               f"esos campos quedarán como {config.MARCA_SIN_SUSTENTO}.")

columna_despues, columna_final, _ = st.columns([1, 1, 2])
seguir_despues = columna_despues.button("Guardar y seguir después", width="stretch")
guardar_final = columna_final.button("Guardar ficha final", type="primary", width="stretch")

if seguir_despues or guardar_final:
    try:
        with closing(db.conectar()) as conexion:
            fichas.responder(conexion, ficha_id, respuestas, finalizar=guardar_final)
    except fichas.ErrorFicha as error:
        st.error(str(error))
        st.stop()
    if seguir_despues:
        st.session_state["aviso"] = f"Borrador de HA {ficha['ha']} guardado. Puede continuarlo desde esta pantalla."
        soltar_caso()
    st.rerun()