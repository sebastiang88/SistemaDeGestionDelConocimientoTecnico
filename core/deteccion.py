# -- Detección de los casos que hay que documentar (módulo 2).
# Un caso se documenta si está cerrado, si es de un tipo que se documenta y si todavía no tiene ficha.

import logging

import config
from core import db
from core.carga import normalizar

logger = logging.getLogger(__name__)


# Saca el código del estado: "4.3. Cerrado" -> "4.3".
def codigo_estado(estado):
    return str(estado).split(" ")[0].rstrip(".")

# Deja sólo los casos cerrados (4.3 o 4.4) de un tipo que se documenta.
def filtrar_documentables(casos):
    tipos = casos["tipo"].map(normalizar)
    codigos = casos["estado"].map(codigo_estado)

    # Un tipo que no está en ninguna lista es nuevo: se pone en los logs.
    desconocidos = set(tipos) - config.TIPOS_DOCUMENTABLES - config.TIPOS_EXCLUIDOS - {""}
    if desconocidos:
        logger.warning("Tipos de caso desconocidos, no se documentan: %s", ", ".join(sorted(desconocidos)))

    cerrados = codigos.isin(config.ESTADOS_CERRADOS)
    documentables = tipos.isin(config.TIPOS_DOCUMENTABLES)
    seleccion = casos[cerrados & documentables].reset_index(drop=True)

    logger.info("%d de %d casos son documentables", len(seleccion), len(casos))
    return seleccion

# De los casos documentables, quita los que ya tienen ficha. "Sin ficha" significa sin fila en la tabla ficha, ni borrador ni final.
def quitar_con_ficha(documentables, conexion):
    con_ficha = db.ha_con_ficha(conexion)

    pendientes = documentables[~documentables["ha"].isin(con_ficha)].reset_index(drop=True)
    logger.info("%d casos sin ficha (%d ya documentados)",
                len(pendientes), len(documentables) - len(pendientes))
    return pendientes

# Punto de entrada: de los casos cargados, devuelve los que hay que documentar.
def detectar(casos, conexion):
    return quitar_con_ficha(filtrar_documentables(casos), conexion)