# -- Pantalla de inicio: portada con lo que hace la plataforma, sus números en vivo y cómo se usa.

from contextlib import closing

import pandas as pd
import streamlit as st

import config
from core import db, documento, fichas, proveedor

# --- Portada ---
motor = proveedor.motor_activo()
etiqueta_motor = "Motor simulado · reglas locales" if motor == "simulado" else f"Motor {motor} · {config.GEMINI_MODELO}"
st.html(f"""
<div class="sgct-portada">
  <span class="sgct-etiqueta">{etiqueta_motor}</span>
  <h1>Sistema de Gestión del Conocimiento Técnico</h1>
  <p>Genera el borrador de la ficha técnica de cada caso cerrado a partir de lo que ya está escrito
  en el archivo de seguimiento, y pregunta al responsable sólo lo que no se puede deducir:
  máximo {config.MAX_PREGUNTAS} preguntas.</p>
</div>
""")

# --- La base de conocimiento en números ---
# Se calculan en vivo desde la base: son los mismos datos de la evaluación.
with closing(db.conectar()) as conexion:
    lista = fichas.listar(conexion)

finales = lista[lista["estado"] == "final"] if not lista.empty else lista
if finales.empty:
    tiempo_promedio = "—"
else:
    segundos = [
        (documento.fecha_local(f.actualizada_en) - documento.fecha_local(f.creada_en)).total_seconds()
        for f in finales.itertuples()
    ]
    tiempo_promedio = documento.duracion_texto(pd.Series(segundos).median())
pendientes = st.session_state.get("pendientes")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Fichas finales", len(finales), border=True)
c2.metric("Borradores", 0 if lista.empty else int((lista["estado"] == "borrador").sum()), border=True)
c3.metric("Tiempo para documentar", tiempo_promedio, border=True,
          help="Mediana del tiempo desde que se genera el borrador hasta que se guarda la ficha final")
c4.metric("Casos pendientes", "—" if pendientes is None else len(pendientes), border=True,
          help="Se calcula al cargar el archivo de seguimiento en Casos pendientes")

# --- Cómo se usa ---
st.subheader("Cómo se usa")
pasos = [
    (":material/upload_file:", "Cargue", "el archivo de seguimiento, o use el de ejemplo, en **Casos pendientes**."),
    (":material/auto_awesome:", "Genere", "el borrador de un caso cerrado: lo que no tiene sustento queda marcado."),
    (":material/forum:", "Responda", f"hasta {config.MAX_PREGUNTAS} preguntas sobre lo que falta y guarde la ficha."),
    (":material/download:", "Consulte", "las fichas en **Fichas** y descárguelas en Word."),
]
for columna, (icono, verbo, texto) in zip(st.columns(4), pasos):
    with columna.container(key=f"tarjeta_paso_{verbo}", height="stretch"):
        st.markdown(f"### {icono}")
        st.markdown(f"**{verbo}** {texto}")

st.page_link("pantallas/casos_pendientes.py", label="Empezar con Casos pendientes", icon=":material/arrow_forward:")
st.caption("Todos los datos de esta demostración son ficticios.")