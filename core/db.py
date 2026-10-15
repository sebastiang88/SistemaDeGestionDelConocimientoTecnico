# -- Acceso a la base de conocimiento en SQLite. 
# Es el único módulo que habla con la base: los demás le piden datos y no escriben SQL.


import logging
import sqlite3
from pathlib import Path

import config

logger = logging.getLogger(__name__)

# Base temporal que vive en memoria y desaparece al cerrar la conexión;
MEMORIA = ":memory:"

#-- Abre una conexión nueva a la base y la devuelve.Cada operación abre su propia conexión y la cierra al terminar: Streamlit atiende a cada usuario en un hilo distinto y una conexión de SQLite sólo funciona en el hilo que la creó.

def conectar(ruta=config.DB_PATH):
    
    if str(ruta) != MEMORIA:
        # git no guarda carpetas vacías, así que data/ puede no existir 
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(ruta)
    # SQLite trae las llaves foráneas apagadas y hay que activarlas en cada conexión;
    # sin esto se podrían guardar preguntas de una ficha que no existe.
    
    conexion.execute("PRAGMA foreign_keys = ON")
    # Permite leer cada fila por nombre de columna (fila["causa"]) y no por posición.
    conexion.row_factory = sqlite3.Row

    logger.debug("Conexión abierta a %s", ruta)
    return conexion
