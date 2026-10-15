# -- Configuración central de SGCT: rutas, reglas del producto y motor de lenguaje.

#--Este módulo solo define constantes.

from pathlib import Path

# --- Rutas ---
# Se calculan desde la ubicación de este archivo y no desde la carpeta en la que se ejecute el comando, así funcionan igual en local y en Streamlit Community Cloud.

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" 
DB_PATH = DATA_DIR / "sgct.db"
