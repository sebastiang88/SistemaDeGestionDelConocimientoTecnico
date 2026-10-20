# -- Tablero
# Muestra cómo se vería el tablero completo

import streamlit as st
import ui

st.title("Tablero")
ui.aviso_maqueta("El tablero completo está priorizado para después del MVP (P3).")

# Indicadores que tendría el tablero.
c1, c2, c3, c4 = st.columns(4)
c1.metric("Fichas documentadas", "—", help="Fichas en estado final en el periodo")
c2.metric("Tiempo promedio", "—", help="Desde que se genera el borrador hasta que se guarda la ficha final")
c3.metric("Categoría diligenciada", "—", help="Porcentaje de fichas con categoría de causa; la línea base es 0 %")
c4.metric("Preguntas sin responder", "—", help="Preguntas que quedaron sin responder en fichas finales")

f1, f2 = st.columns(2)
f1.selectbox("Periodo", ["Último mes"], disabled=True)
f2.selectbox("Responsable", ["Todos"], disabled=True)

# Espacios de los gráficos que tendría.
g1, g2 = st.columns(2)
for columna, titulo in ((g1, "Fichas documentadas por semana"), (g2, "Causas más frecuentes por categoría")):
    with columna:
        with st.container(border=True, height=220):
            st.markdown(f"**{titulo}**")
            st.caption("Gráfico disponible en una próxima versión.")
