# -- Único punto de salida hacia el modelo de lenguaje. Todo pasa por generar().
# Cambiar Gemini por Ollama local sólo toca este archivo: el resto del sistema recibe la respuesta del motor en el mismo formato.

import json
import logging
import re
from dataclasses import dataclass

import pandas as pd

import config

logger = logging.getLogger(__name__)

# Lo que devuelve generar(). es el que respondió de verdad, no el que se pidió. Si Gemini falla y responde el simulado, la ficha queda registrada como "simulado" y la comparación entre motores de la evaluación no se mezcla.
@dataclass
class Respuesta:
    texto: str  # JSON en texto con sintoma, causa, solucion, categoria, subcategoria y preguntas
    motor: str
    modelo: str | None
    duracion_ms: int

# Decide qué motor usar según la configuración, ante cualquier problema usa el simulado.
def motor_activo():
    if config.PROVEEDOR not in config.PROVEEDORES_VALIDOS:
        logger.warning("Proveedor '%s' no válido, se usa el simulado", config.PROVEEDOR)
        return "simulado"

    if config.PROVEEDOR == "gemini" and not config.GEMINI_API_KEY:
        logger.warning("Falta GEMINI_API_KEY, se usa el simulado")
        return "simulado"

    return config.PROVEEDOR


# --- Motor simulado ---
# Aplica reglas sobre los datos del caso y devuelve el mismo JSON que la IA Gemini.

# Una descripción sin sustento no describe el síntoma. El umbral es arbitrario; Gemini no lo necesita porque entiende si el texto dice algo o no.
MIN_PALABRAS_SINTOMA = 5

# La columna Causa/Solucion se escribe a mano por lo tanto es dificil normalizar un patron, por lo tanto se busca un patrón de texto que indique la causa y otro que indique la solución. Si no se encuentra, se marca como sin sustento.
PATRON_CAUSA = re.compile(r"causa\s*[:\-]\s*(.+?)\s*(?=soluci[oó]n\s*[:\-]|$)", re.I | re.S)
PATRON_SOLUCION = re.compile(r"soluci[oó]n\s*[:\-]\s*(.+)", re.I | re.S)

# Preguntas de plantilla, en orden de prioridad: si hay más vacíos que MAX_PREGUNTAS, se pregunta primero lo que sólo el desarrollador sabe.
PREGUNTAS_SIMULADO = {
    "causa": "¿Qué originó la falla? Describe la causa técnica.",
    "solucion": "¿Qué se hizo para corregir la falla?",
    "categoria": "¿En qué categoría y subcategoría del catálogo clasificarías la causa?",
    "sintoma": "¿Qué observó el usuario cuando ocurrió la falla?",
}

# Texto de una celda sin espacios en las puntas
def _texto(valor):
    return "" if pd.isna(valor) else str(valor).strip()

# Busca el patrón en el texto y devuelve lo encontrado o la marca si no está.
def _extraer(patron, texto):
    encontrado = patron.search(texto)
    return encontrado.group(1).strip() if encontrado else config.MARCA_SIN_SUSTENTO

# Arma el borrador de un caso con reglas fijas. "caso" es una fila de la tabla de casos.
def simular(caso):
    sin = config.MARCA_SIN_SUSTENTO

    descripcion = _texto(caso.get("descripcion"))
    sintoma = descripcion if len(descripcion.split()) >= MIN_PALABRAS_SINTOMA else sin

    causa_solucion = _texto(caso.get("causa_solucion"))
    causa = _extraer(PATRON_CAUSA, causa_solucion)
    solucion = _extraer(PATRON_SOLUCION, causa_solucion)

    # La categoría sólo se toma del Excel y si el par existe en el catálogo: el simulado nunca la coloca.
    categoria = _texto(caso.get("categoria_excel"))
    subcategoria = _texto(caso.get("subcategoria_excel"))
    if subcategoria not in config.CATEGORIAS_CAUSA.get(categoria, ()):
        categoria = subcategoria = sin

    campos = {"sintoma": sintoma, "causa": causa, "solucion": solucion, "categoria": categoria}
    preguntas = [
        {"campo": campo, "texto": texto}
        for campo, texto in PREGUNTAS_SIMULADO.items()
        if campos[campo] == sin
    ][:config.MAX_PREGUNTAS]

    borrador = {
        "sintoma": sintoma,
        "causa": causa,
        "solucion": solucion,
        "categoria": categoria,
        "subcategoria": subcategoria,
        "preguntas": preguntas,
    }
    return json.dumps(borrador, ensure_ascii=False)