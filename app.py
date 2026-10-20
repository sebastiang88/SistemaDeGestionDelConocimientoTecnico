# -- Punto de entrada de la aplicación

import logging
from contextlib import closing

import streamlit as st

import config
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

# Crea las tablas si no existen. En Cloud la base se borra con cada reinicio.
@st.cache_resource
def preparar_base():
    with closing(db.conectar()) as conexion:
        db.crear_tablas(conexion)

st.set_page_config(page_title="SGCT", page_icon=":material/menu_book:", layout="wide")
configurar_logs()
preparar_base()

menu = st.navigation([
    st.Page("pages/inicio.py", title="Inicio", icon=":material/home:", default=True),
    st.Page("pages/casos_pendientes.py", title="Casos pendientes", icon=":material/assignment:"),
    st.Page("pages/documentar.py", title="Documentar", icon=":material/edit_note:"),
])
menu.run()
