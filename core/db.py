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


# Las reglas van también en la base, si un módulo tiene un error,
# la base lo frena antes de que dañen los datos de la evaluación.

ESQUEMA = """
CREATE TABLE IF NOT EXISTS caso (
    ha                  TEXT PRIMARY KEY,
    tipo                TEXT,
    estado              TEXT,
    responsable         TEXT,
    flujo               TEXT,
    descripcion         TEXT,
    observaciones       TEXT,
    causa_solucion      TEXT,
    categoria_excel     TEXT,
    subcategoria_excel  TEXT,
    cargado_en          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ficha (
    id                  INTEGER PRIMARY KEY,
    ha                  TEXT NOT NULL UNIQUE REFERENCES caso(ha),
    sintoma             TEXT,
    causa               TEXT,
    solucion            TEXT,
    categoria           TEXT,
    subcategoria        TEXT,
    estado              TEXT NOT NULL DEFAULT 'borrador'
                        CHECK (estado IN ('borrador', 'final')),
    motor               TEXT NOT NULL,
    modelo              TEXT,
    marcas_sin_sustento INTEGER NOT NULL DEFAULT 0,
    duracion_ms         INTEGER,
    creada_en           TEXT NOT NULL DEFAULT (datetime('now')),
    actualizada_en      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pregunta (
    id                  INTEGER PRIMARY KEY,
    ficha_id            INTEGER NOT NULL REFERENCES ficha(id) ON DELETE CASCADE,
    orden               INTEGER NOT NULL,
    campo               TEXT NOT NULL,
    texto               TEXT NOT NULL,
    respuesta           TEXT,
    respondida_en       TEXT
);
"""

def crear_tablas(conexion):
    conexion.executescript(ESQUEMA)
    logger.info("Tablas de la base verificadas")

# Devuelve el conjunto de #HA que ya tienen ficha, sea borrador o final.
def ha_con_ficha(conexion):
    filas = conexion.execute("SELECT ha FROM ficha").fetchall()
    return {fila["ha"] for fila in filas}

# --- Escritura ---
# Estas funciones no hacen commit: quien las llama (fichas.py) agrupa varias en una sola transacción, para que nunca quede una ficha guardada sin sus preguntas.
COLUMNAS_CASO = ("ha", "tipo", "estado", "responsable", "flujo", "descripcion",
                 "observaciones", "causa_solucion", "categoria_excel", "subcategoria_excel")

# Guarda el caso tal como venía en el Excel, si ya existe, lo actualiza.
def guardar_caso(conexion, caso):
    columnas = ", ".join(COLUMNAS_CASO)
    valores = ", ".join(f":{c}" for c in COLUMNAS_CASO)
    actualizar = ", ".join(f"{c} = excluded.{c}" for c in COLUMNAS_CASO if c != "ha")
    conexion.execute(
        f"INSERT INTO caso ({columnas}) VALUES ({valores}) "
        f"ON CONFLICT(ha) DO UPDATE SET {actualizar}, cargado_en = datetime('now')",
        {c: caso.get(c) for c in COLUMNAS_CASO},
    )

# Crea la ficha y devuelve su id.
def insertar_ficha(conexion, ficha):
    cursor = conexion.execute(
        "INSERT INTO ficha (ha, sintoma, causa, solucion, categoria, subcategoria, estado, "
        "motor, modelo, marcas_sin_sustento, duracion_ms) "
        "VALUES (:ha, :sintoma, :causa, :solucion, :categoria, :subcategoria, :estado, "
        ":motor, :modelo, :marcas_sin_sustento, :duracion_ms)",
        ficha,
    )
    return cursor.lastrowid

# Guarda las preguntas de una ficha en el orden en que se hicieron.
def insertar_preguntas(conexion, ficha_id, preguntas):
    conexion.executemany(
        "INSERT INTO pregunta (ficha_id, orden, campo, texto) VALUES (?, ?, ?, ?)",
        [(ficha_id, orden, p["campo"], p["texto"]) for orden, p in enumerate(preguntas, start=1)],
    )

# Registra la respuesta a una pregunta y cuándo se respondió.
def responder_pregunta(conexion, pregunta_id, respuesta):
    conexion.execute(
        "UPDATE pregunta SET respuesta = ?, respondida_en = datetime('now') WHERE id = ?",
        (respuesta, pregunta_id),
    )

# Actualiza los campos de la ficha que vengan en "campos" y su estado.
def actualizar_ficha(conexion, ficha_id, campos, estado):
    permitidos = ("sintoma", "causa", "solucion", "categoria", "subcategoria")
    asignaciones = "".join(f"{c} = :{c}, " for c in campos if c in permitidos)
    conexion.execute(
        f"UPDATE ficha SET {asignaciones}estado = :estado, actualizada_en = datetime('now') WHERE id = :id",
        {**{c: v for c, v in campos.items() if c in permitidos}, "estado": estado, "id": ficha_id},
    )

# --- Lectura ---
# Una ficha con los datos de su caso, o None si no existe.
def obtener_ficha(conexion, ficha_id):
    return conexion.execute(
        "SELECT f.*, c.tipo, c.responsable, c.flujo, c.descripcion, c.observaciones, c.causa_solucion "
        "FROM ficha f JOIN caso c ON c.ha = f.ha WHERE f.id = ?",
        (ficha_id,),
    ).fetchone()

# Las preguntas de una ficha en orden.
def obtener_preguntas(conexion, ficha_id):
    return conexion.execute(
        "SELECT * FROM pregunta WHERE ficha_id = ? ORDER BY orden", (ficha_id,)
    ).fetchall()

# Todas las fichas con lo necesario para la lista de consulta, la más reciente primero.
def listar_fichas(conexion):
    return conexion.execute(
        "SELECT f.id, f.ha, c.tipo, c.responsable, f.estado, f.motor, f.marcas_sin_sustento, "
        "       f.creada_en, f.actualizada_en, "
        "       COUNT(p.id) AS preguntas, "
        "       SUM(CASE WHEN p.id IS NOT NULL AND p.respuesta IS NULL THEN 1 ELSE 0 END) AS sin_responder "
        "FROM ficha f JOIN caso c ON c.ha = f.ha LEFT JOIN pregunta p ON p.ficha_id = f.id "
        "GROUP BY f.id ORDER BY f.actualizada_en DESC, f.id DESC"
    ).fetchall()