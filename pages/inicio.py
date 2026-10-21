# -- Pantalla de inicio

import streamlit as st

from core import proveedor

st.title("SGCT — Sistema de Gestión del Conocimiento Técnico")

st.write(
    "Genera el borrador de la ficha técnica de cada caso cerrado a partir de lo que ya está "
    "escrito en el archivo de seguimiento, y pregunta al responsable sólo lo que no se puede "
    "deducir. Máximo tres preguntas."
)

motor = proveedor.motor_activo()
if motor == "simulado":
    st.info("Motor activo: **simulado** (reglas locales, sin conexión a un modelo de lenguaje).")
else:
    st.success(f"Motor activo: **{motor}**.")

st.subheader("Cómo se usa")
st.markdown(
    "1. En **Casos pendientes**, cargue el archivo de seguimiento o use el archivo de ejemplo.\n"
    "2. La plataforma muestra los casos cerrados que todavía no tienen ficha.\n"
    "3. Elija un caso y pulse **Documentar este caso** para generar el borrador.\n"
    "4. Responda las preguntas sobre lo que falta y guarde la ficha.\n"
    "5. Consulte las fichas guardadas en **Fichas**."
)

st.caption("Todos los datos de esta demostración son ficticios.")