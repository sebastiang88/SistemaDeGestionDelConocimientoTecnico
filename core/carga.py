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
    "id_flujo": config.COL_ID_FLUJO,
    "flujo": config.COL_FLUJO,
    "categoria_excel": config.COL_CATEGORIA,
    "subcategoria_excel": config.COL_SUBCATEGORIA,
    "sprint": config.COL_SPRINT,
    "usuario_reporta": config.COL_USUARIO_REPORTA,
    "fecha_recepcion": config.COL_FECHA_RECEPCION,
    "fecha_cierre": config.COL_FECHA_CIERRE,
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


# Deja los valores listos para guardar. No usa normalizar(): este texto es el que lee el modelo y el que se muestra en pantalla, así que conserva tildes, mayúsculas y saltos de línea.
def limpiar_casos(datos):
    datos = datos.copy()

    # Del #HA sólo sirve la primera línea, el resto se ignora.
    datos["ha"] = datos["ha"].str.split("\n").str[0].str.strip()

    # Sin #HA no hay cómo identificar ni guardar el caso.
    sin_ha = datos["ha"].isna() | (datos["ha"] == "")
    if sin_ha.any():
        logger.warning("Se descartan %d filas sin %s", sin_ha.sum(), config.COL_HA)
        datos = datos[~sin_ha]

    # El #HA no debería repetirse, pero si pasa se toma la última fila. 
    repetidos = datos["ha"].duplicated(keep="last")
    if repetidos.any():
        logger.warning("%s repetidos, se toma la última fila: %s",
                       config.COL_HA, ", ".join(sorted(set(datos.loc[repetidos, "ha"]))))
        datos = datos[~repetidos]

    # En el resto sólo se quitan los espacios de las puntas, y el texto vacío queda como vacío de pandas (NaN), igual que una celda vacía.
    for columna in COLUMNAS:
        limpia = datos[columna].str.strip()
        datos[columna] = limpia.where(limpia != "")

    return datos.reset_index(drop=True)

# Punto de entrada para las pantallas: lee el archivo y devuelve los casos limpios.
def cargar(archivo):
    casos = limpiar_casos(leer_excel(archivo))
    logger.info("Casos cargados: %d", len(casos))
    return casos
