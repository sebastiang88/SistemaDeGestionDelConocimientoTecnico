# -- Configuración
# Muestra la configuración con la que está funcionando la plataforma, sólo para consulta.
import streamlit as st
import config
import ui
from core import proveedor

ui.encabezado("Configuración", "Con qué motor y qué reglas está funcionando la plataforma.")
ui.aviso_maqueta("Muestra la configuración actual, pero no permite cambiarla.")

# --- Lo que está activo (valores reales, sólo lectura) ---
st.subheader("Motor de lenguaje")
motor = proveedor.motor_activo()
c1, c2 = st.columns(2)
c1.text_input("Motor activo", motor, disabled=True)
c2.text_input("Modelo", config.GEMINI_MODELO if motor == "gemini" else "Reglas locales (sin modelo)", disabled=True)
# Nunca se muestra la clave, sólo si existe.
c1.text_input("Clave de Gemini", "Configurada" if config.GEMINI_API_KEY else "No configurada", disabled=True)
c2.text_input("Tiempo máximo de espera", f"{config.TIMEOUT_SEGUNDOS} s", disabled=True)
st.caption("Para cambiar el motor se define la variable SGCT_PROVEEDOR (en Streamlit Cloud, en los secrets).")

st.subheader("Reglas del borrador")
c1, c2 = st.columns(2)
c1.text_input("Máximo de preguntas por ficha", str(config.MAX_PREGUNTAS), disabled=True)
c2.text_input("Marca para lo que no tiene sustento", config.MARCA_SIN_SUSTENTO, disabled=True)

st.subheader("Archivo de seguimiento")
c1, c2 = st.columns(2)
c1.text_input("Fila de los encabezados", str(config.FILA_ENCABEZADO), disabled=True)
c2.text_input("Estados que se documentan", ", ".join(sorted(config.ESTADOS_CERRADOS)), disabled=True)

# --- Lo que vendría después ---
st.subheader("Próximamente")
st.file_uploader("Plantilla propia de ficha (.docx)", type=["docx"], disabled=True)
st.toggle("Notificar al responsable cuando tenga casos pendientes", disabled=True)
st.button("Guardar cambios", disabled=True)