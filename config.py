# -- Configuración central de SGCT: rutas, reglas del producto y motor de lenguaje.

#--Este módulo solo define constantes.

import os
from pathlib import Path

# --- Rutas ---
# Se calculan desde la ubicación de este archivo y no desde la carpeta en la que se ejecute el comando, así funcionan igual en local y en Streamlit Community Cloud.

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" 
DB_PATH = DATA_DIR / "sgct.db"

# --- Reglas del producto ---
MAX_PREGUNTAS = 3
MARCA_SIN_SUSTENTO = "[SIN SUSTENTO]"

# --- Motor de lenguaje ---
PROVEEDORES_VALIDOS = ("simulado", "gemini")

# El "or" cubre la variable definida pero vacía, que os.getenv no reemplaza por el valor por defecto.
# Si llega un valor que no está en PROVEEDORES_VALIDOS, core/proveedor.py lo rechaza y usa "simulado".
PROVEEDOR = os.getenv("SGCT_PROVEEDOR", "").strip().lower() or "simulado"

# Es el nombre que el SDK de Google (google-genai) busca por defecto.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Versión fija 
GEMINI_MODELO = "gemini-3.8-flash"

TEMPERATURA = 0.1
TIMEOUT_SEGUNDOS = 30

# --- Configuración de logs ---
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "sgct.log"

LOG_NIVEL = os.getenv("SGCT_LOG_NIVEL", "").strip().upper() or "INFO"
LOG_FORMATO = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# --- Archivo de seguimiento ---
# Fila de los encabezados tal como se ve en Excel 
FILA_ENCABEZADO = 7

# Nombres escritos como aparecen en el Excel. core/carga.py limpia igual estos valores y los encabezados del archivo (sin tildes, minúsculas, espacios simples) antes de compararlos.
COL_HA = "#HA"  #El correcto es la columna al lado de la columna DEV
COL_DEV = "DEV"  
COL_TIPO = "Tipo"
COL_ESTADO = "Estado"

# Texto que lee el modelo para redactar el borrador.
COL_DESCRIPCION = "Descripción incidente"
COL_OBSERVACIONES = "Observaciones"
COL_CAUSA_SOLUCION = "Causa/Solucion"
COL_FLUJO = "nombre_flujo"

# Causa del error.
COL_CATEGORIA = "Categoria Causa"
COL_SUBCATEGORIA = "Sub_Categoría Causa"

# --- Filtros de detección ---
# Lista blanca: un tipo que no esté aquí (Evolutivo o uno nuevo) no se documenta.
# Se comparan ya limpios (sin tildes, minúsculas), igual que los encabezados.
TIPOS_DOCUMENTABLES = frozenset({"incidente", "evento", "control de cambio"})

# Se compara el código y no el texto: "4.3. Cerrado" y "4.4. Cerrado" son los textos que se ven en el Excel, pero el código es lo que importa.
ESTADOS_CERRADOS = frozenset({"4.3", "4.4"})

# --- Catálogo de causas ---
# Categorías escritas como quedan en la celda (con guion bajo, como las listas desplegables del Excel).
# El modelo solo puede elegir de aquí; si no tiene sustento para elegir, marca MARCA_SIN_SUSTENTO.
CATEGORIAS_CAUSA = {
    "Parametrización_de_Accesos_Roles_y_Asignación": (
        "Accesos y usuarios",
        "Grupos, catálogo y módulo administrativo",
        "Asignación y bandejas",
    ),
    "Parametrización_Campos_Reglas_e_Interfaces": (
        "Campos, listas y validaciones",
        "ANS y tiempos",
        "Textos, etiquetas y mensajes de ayuda",
    ),
    "Configuración_Informes": (
        "Contenido del informe detallado",
        "Acceso y descarga de informes",
        "Seguimiento, historial y trazabilidad",
    ),
    "Desarrollo": (
        "Radicación y creación de casos",
        "Ciclo del caso y actividades",
        "Visualización y persistencia de datos",
        "Errores de servicios en producción (monitoreo)",
    ),
    "Configuración_Notificaciones": (
        "Destinatarios",
        "Notificaciones que no llegan",
        "Contenido del correo",
        "Duplicadas o con retraso",
    ),
    "Configuración_Adjuntos": (
        "Formatos y tamaño permitidos",
        "Obligatoriedad del adjunto",
        "Carga y visualización de adjuntos",
        "Plantillas descargables",
        "Carga masiva",
    ),
    "Descripción_insuficiente": (
        "Sin detalle en el registro (ver HA/adjunto)",
    ),
}


