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
# Versión fija y no un alias "-latest": el alias cambia de modelo sin aviso y las pruebas dejarían de ser comparables.
GEMINI_MODELO = "gemini-3.8-flash"
