# -- Carga del archivo de seguimiento en Excel (módulo 1).
# Lee el archivo, ubica las columnas que usa la plataforma y devuelve los casos limpios.

import logging
import unicodedata

import pandas as pd

import config

logger = logging.getLogger(__name__)

# Columnas que se leen, con el nombre que tendrán dentro de la plataforma. Los nombres de la
# izquierda son los mismos de la tabla caso en core/db.

COLUMNAS = {
    "responsable": config.COL_DEV,
    "tipo": config.COL_TIPO,
    "estado": config.COL_ESTADO,
    "descripcion": config.COL_DESCRIPCION,
    "observaciones": config.COL_OBSERVACIONES,
    "causa_solucion": config.COL_CAUSA_SOLUCION,
    "flujo": config.COL_FLUJO,
    "categoria_excel": config.COL_CATEGORIA,
    "subcategoria_excel": config.COL_SUBCATEGORIA,
}


# Error con un mensaje para mostrarse en pantalla al usuario.
class ErrorCarga(ValueError):
    pass


# Deja un valor listo para comparar: sin tildes, en minúsculas y con espacios simples.
# Es la única regla de limpieza del proyecto; se aplica igual a los encabezados del Excel y a los valores de las columnas que se leen.

def normalizar(valor):

    if pd.isna(valor):
        return ""

    texto = str(valor)
    # NFKD separa cada letra de su tilde ("í" -> "i" + marca); luego se descartan las marcas.
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


# Ubica la posición de cada columna que se lee. Devuelve {nombre_interno: posición}.
def ubicar_columnas(encabezados):
    limpios = [normalizar(e) for e in encabezados]
    posiciones = {}
    faltantes = []

    for interno, nombre in COLUMNAS.items():
        buscado = normalizar(nombre)
        if buscado in limpios:
            posiciones[interno] = limpios.index(buscado)
        else:
            faltantes.append(nombre)

    if faltantes:
        raise ErrorCarga(
            f"Al archivo le faltan estas columnas en la fila {config.FILA_ENCABEZADO}: "
            + ", ".join(faltantes)
        )

    dev = posiciones["responsable"]
    buscado_ha = normalizar(config.COL_HA)
    vecinas = [p for p in (dev - 1, dev + 1) if 0 <= p < len(limpios) and limpios[p] == buscado_ha]
    if not vecinas:
        raise ErrorCarga(f"No se encontró la columna {config.COL_HA} junto a la columna {config.COL_DEV}.")
    posiciones["ha"] = vecinas[0]

    return posiciones


# Lee el archivo de seguimiento y devuelve una tabla con sólo las columnas que usa la plataforma,con los nombres internos y todos los valores como texto sin limpiar

def leer_excel(archivo):
    try:
        hoja = pd.read_excel(archivo, header=None, dtype=str)
    except Exception as error:
        logger.warning("No se pudo leer el archivo como Excel: %s", error)
        raise ErrorCarga("No se pudo leer el archivo. Verifique que sea un Excel (.xlsx) válido.") from error

    fila = config.FILA_ENCABEZADO - 1  
    if len(hoja) <= fila:
        raise ErrorCarga(f"El archivo no tiene encabezados en la fila {config.FILA_ENCABEZADO}.")

    posiciones = ubicar_columnas(hoja.iloc[fila].tolist())

    datos = hoja.iloc[fila + 1:, list(posiciones.values())]
    datos.columns = list(posiciones.keys())
    datos = datos[["ha", *COLUMNAS]] 
    datos = datos.dropna(how="all").reset_index(drop=True)

    logger.info("Archivo leído: %d filas", len(datos))
    return datos
