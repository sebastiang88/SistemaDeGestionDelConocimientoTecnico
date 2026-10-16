# -- Único punto de salida hacia el modelo de lenguaje. Todo pasa por generar().
# Cambiar Gemini por Ollama local sólo toca este archivo: el resto del sistema recibe la respuesta del motor en el mismo formato.

import logging
from dataclasses import dataclass

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