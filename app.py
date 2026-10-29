# -- Punto de entrada de la aplicación

import logging
from contextlib import closing

import streamlit as st

import config
import ui
from core import db

# Logs en la consola y en un archivo. 
@st.cache_resource
def configurar_logs():

    nivel_valido = isinstance(logging.getLevelName(config.LOG_NIVEL), int)
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=config.LOG_NIVEL if nivel_valido else "INFO",
        format=config.LOG_FORMATO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
        ],
    )
    if not nivel_valido:
        logging.getLogger(__name__).warning("Nivel de log '%s' no válido, se usa INFO", config.LOG_NIVEL)
    logging.getLogger(__name__).info("Aplicación iniciada")

# Crea las tablas si no existen. La base es PostgreSQL y vive fuera de la app
@st.cache_resource
def preparar_base():
    with closing(db.conectar()) as conexion:
        db.crear_tablas(conexion)
    logging.getLogger(__name__).info("Base de conocimiento: PostgreSQL")

st.set_page_config(page_title="SGCT", page_icon=str(config.BASE_DIR / "assets" / "icono.svg"), layout="wide")
ui.aplicar_estilos()
configurar_logs()

try:
    preparar_base()
except db.ErrorBase as error:
    st.error(str(error), icon=":material/database:")
    st.stop()

# Las maquetas van en una sección aparte del menú.
menu = st.navigation({
    "": [
        st.Page("pantallas/inicio.py", title="Inicio", icon=":material/home:", default=True),
        st.Page("pantallas/casos_pendientes.py", title="Casos pendientes", icon=":material/assignment:"),
        st.Page("pantallas/documentar.py", title="Documentar", icon=":material/edit_note:"),
        st.Page("pantallas/fichas.py", title="Fichas", icon=":material/folder_open:"),
        st.Page("pantallas/tablero.py", title="Tablero", icon=":material/dashboard:"),
    ],
    "Maquetas": [
        st.Page("pantallas/configuracion.py", title="Configuración", icon=":material/settings:"),
    ],
})
menu.run()