# -- Pantalla de inicio: qué es la plataforma, por qué existe, sus números en vivo, qué hay en cada pantalla y un ejemplo de ficha.

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
n_borradores = 0 if lista.empty else int((lista["estado"] == "borrador").sum())

# --- Por dónde empezar ---
# En el test de humo los tres participantes dijeron que al entrar no sabían por dónde empezar, y fue la
# afirmación peor calificada. El primer paso queda arriba, con un botón, y no al final de la página.
with st.container(key="tarjeta_empezar"):
    texto, boton = st.columns([3, 1], vertical_alignment="center")
    texto.markdown("**¿Por dónde empezar?** Vaya a **Casos pendientes**, cargue el archivo de seguimiento "
                   "(o use el de ejemplo) y elija el caso cerrado que va a documentar.")
    if boton.button("Empezar", type="primary", icon=":material/arrow_forward:", width="stretch"):
        st.switch_page("pantallas/casos_pendientes.py")
    if n_borradores:
        texto.caption(f"Hay {n_borradores} borradores sin terminar: puede retomarlos en **Documentar**.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Fichas finales", len(finales), border=True)
c2.metric("Borradores", n_borradores, border=True)
c3.metric("Tiempo para documentar", tiempo_promedio, border=True,
          help="Mediana del tiempo desde que se genera el borrador hasta que se guarda la ficha final")
c4.metric("Casos pendientes", "—" if pendientes is None else len(pendientes), border=True,
          help="Se calcula al cargar el archivo de seguimiento en Casos pendientes")

# --- Por qué existe ---
# Quien entra por primera vez (un desarrollador nuevo, un evaluador) ve qué problema resuelve antes de usarla.
st.subheader("Por qué existe")
razones = [
    (":material/report:", "El problema",
     f"El equipo resuelve fallas todos los días, pero no las documenta por falta de tiempo. En "
     f"{config.LINEA_BASE_CASOS} casos cerrados, la categoría de la causa estaba vacía en el "
     f"{100 - config.LINEA_BASE_CATEGORIA} %: lo que se aprendió al resolverlos se pierde."),
    (":material/lightbulb:", "La propuesta",
     f"En lugar de pedir un documento, la plataforma arma el borrador con lo que ya está escrito en el caso "
     f"y pregunta sólo lo que falta: máximo {config.MAX_PREGUNTAS} preguntas. Responder tres preguntas "
     f"cuesta menos que redactar una ficha."),
    (":material/verified:", "La regla",
     f"El modelo de lenguaje no puede inventar. Lo que el caso no dice queda marcado como "
     f"**{config.MARCA_SIN_SUSTENTO}** y se convierte en una pregunta para quien lo resolvió: una causa "
     f"inventada es peor que un campo vacío."),
]
for columna, (icono, titulo, texto) in zip(st.columns(3), razones):
    with columna.container(key=f"tarjeta_razon_{titulo}", height="stretch"):
        st.markdown(f"### {icono}")
        st.markdown(f"**{titulo}**")
        st.markdown(texto)

# --- Qué hay en cada pantalla ---
# En las pruebas no era claro si los casos se buscaban en Casos pendientes o en Fichas: cada tarjeta dice
# qué se hace en esa pantalla y lleva a ella. Van en el orden en que se usan.
st.subheader("Qué hay en cada pantalla")
pantallas = [
    ("pantallas/casos_pendientes.py", ":material/assignment:", "1. Casos pendientes",
     "Cargue el archivo de seguimiento, o use el de ejemplo. Aparecen los casos cerrados que todavía no "
     "tienen ficha. Elija el que va a documentar."),
    ("pantallas/documentar.py", ":material/edit_note:", "2. Documentar",
     f"Genere el borrador del caso, responda hasta {config.MAX_PREGUNTAS} preguntas y guarde la ficha. "
     "Puede dejarla como borrador y seguir después, o descartarla si tomó el caso por error."),
    ("pantallas/fichas.py", ":material/folder_open:", "3. Fichas",
     "La base de conocimiento: busque por palabra clave, filtre por tipo, flujo o causa, abra cualquier "
     "ficha y descárguela en Word."),
    ("pantallas/tablero.py", ":material/dashboard:", "4. Tablero",
     "Los indicadores del equipo: fichas por semana, tiempo para documentar, causas más frecuentes y los "
     "casos raros o nuevos."),
]
for columna, (pagina, icono, titulo, texto) in zip(st.columns(4), pantallas):
    with columna.container(key=f"tarjeta_pantalla_{titulo[0]}", height="stretch"):
        st.markdown(f"### {icono}")
        st.markdown(f"**{titulo}**")
        st.markdown(texto)
        st.page_link(pagina, label="Ir", icon=":material/arrow_forward:")

# --- Cómo es una ficha ---
# Un ejemplo terminado, como pidieron en el test de humo, con el origen de cada campo: así se entiende qué
# hace la plataforma y qué pone el desarrollador.
st.subheader("Cómo es una ficha")
explicacion, ejemplo = st.columns([2, 3])
with explicacion:
    st.markdown(
        "Cada ficha responde cuatro preguntas sobre una falla resuelta: **qué se vio**, **por qué pasó**, "
        "**cómo se corrigió** y **a qué tipo de causa pertenece**, según el catálogo del equipo.")
    st.markdown(
        "La plataforma toma del caso lo que ya está escrito y pregunta el resto. En el ejemplo, el caso sólo "
        "decía qué se vio: la causa, la solución y la categoría las respondió el desarrollador en tres preguntas.")
    st.markdown(
        "Además se puede agregar una lección aprendida e imágenes de evidencia. La ficha se descarga en Word.")
with ejemplo.container(key="tarjeta_ejemplo"):
    st.markdown("**HA 7701406 · Reclamos** · ejemplo con datos ficticios")
    campos_ejemplo = [
        ("Síntoma", "El campo 'Número de producto' acepta letras y se están radicando reclamos con datos "
                    "inválidos.", "Tomado del caso"),
        ("Causa", "La validación del campo se perdió al migrar el formulario y quedó como texto libre.",
         "Respondido por el desarrollador"),
        ("Solución", "Se agregó la validación numérica y de longitud al campo en el formulario.",
         "Respondido por el desarrollador"),
        ("Categoría de la causa", "Parametrización Campos Reglas e Interfaces / Campos, listas y validaciones",
         "Elegido del catálogo por el desarrollador"),
    ]
    for titulo, valor, origen in campos_ejemplo:
        st.markdown(f"**{titulo}**")
        st.markdown(valor)
        st.caption(origen)

st.caption("Todos los datos de esta demostración son ficticios.")