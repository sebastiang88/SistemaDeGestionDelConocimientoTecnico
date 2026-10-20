# -- Guardado y consulta de las fichas (módulos 5 y 6).
# Se guarda junto, cómo una respuesta completa la ficha y cuándo queda final. 

import logging
import sqlite3
import pandas as pd
import config
from core import db

logger = logging.getLogger(__name__)

# Error con un mensaje en pantalla al usuario.
class ErrorFicha(ValueError):
    pass

# --- Módulo 5: guardar ---
# Guarda el caso, el borrador y sus preguntas como una ficha en estado "borrador".
# Devuelve el id de la ficha, todo va en una sola transacción
def guardar_borrador(conexion, caso, borrador):
    try:
        with conexion:
            db.guardar_caso(conexion, caso)
            ficha_id = db.insertar_ficha(conexion, {
                "ha": caso.get("ha"),
                "sintoma": borrador.sintoma,
                "causa": borrador.causa,
                "solucion": borrador.solucion,
                "categoria": borrador.categoria,
                "subcategoria": borrador.subcategoria,
                "estado": "borrador",
                "motor": borrador.motor,
                "modelo": borrador.modelo,
                "marcas_sin_sustento": borrador.marcas_sin_sustento,
                "duracion_ms": borrador.duracion_ms,
            })
            db.insertar_preguntas(conexion, ficha_id, borrador.preguntas)
    except sqlite3.IntegrityError as error:
        
        raise ErrorFicha(f"El caso HA {caso.get('ha')} ya tiene una ficha.") from error

    logger.info("Ficha %d guardada como borrador para HA %s (%d preguntas)",
                ficha_id, caso.get("ha"), len(borrador.preguntas))
    return ficha_id

# Registra las respuestas del responsable y completa la ficha con ellas.
def responder(conexion, ficha_id, respuestas, finalizar):
    preguntas = db.obtener_preguntas(conexion, ficha_id)
    campos = {}
    respondidas = []

    for pregunta in preguntas:
        respuesta = respuestas.get(pregunta["id"])
        if pregunta["campo"] == "categoria":
            if not respuesta:
                continue
            categoria, subcategoria = respuesta
            # El desarrollador puede elegir cualquier categoría del catálogo.
            if subcategoria not in config.CATEGORIAS_CAUSA.get(categoria, ()):
                raise ErrorFicha(f"La subcategoría '{subcategoria}' no pertenece a '{categoria}'.")
            campos["categoria"], campos["subcategoria"] = categoria, subcategoria
            texto = f"{categoria} / {subcategoria}"
        else:
            texto = (respuesta or "").strip()
            if not texto:
                continue
            campos[pregunta["campo"]] = texto
        respondidas.append((pregunta["id"], texto))

    estado = "final" if finalizar else "borrador"
    with conexion:
        for pregunta_id, texto in respondidas:
            db.responder_pregunta(conexion, pregunta_id, texto)
        db.actualizar_ficha(conexion, ficha_id, campos, estado)

    # El total se cuenta de nuevo en la base, una ficha puede responderse en varias visitas.
    total = sum(1 for p in db.obtener_preguntas(conexion, ficha_id) if p["respuesta"] is not None)
    logger.info("Ficha %d: %d respuestas nuevas, %d de %d preguntas respondidas, queda en estado %s",
                ficha_id, len(respondidas), total, len(preguntas), estado)
    
# --- Módulo 6: consultar ---
# Lista de fichas para la pantalla de consulta.
def listar(conexion):
    return pd.DataFrame([dict(fila) for fila in db.listar_fichas(conexion)])

# Una ficha completa con su caso y sus preguntas o None si no existe.
def abrir(conexion, ficha_id):
    ficha = db.obtener_ficha(conexion, ficha_id)
    if ficha is None:
        return None
    return {**dict(ficha), "preguntas": [dict(p) for p in db.obtener_preguntas(conexion, ficha_id)]}