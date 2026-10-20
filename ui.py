# -- Piezas de pantalla que comparten varias páginas.

import pandas as pd
import streamlit as st
import config

ETIQUETAS = {"sintoma": "Síntoma", "causa": "Causa", "solucion": "Solución", "categoria": "Categoría de la causa"}

# Muestra un campo con su título.
def mostrar(titulo, valor):
    st.markdown(f"**{titulo}**")
    if valor == config.MARCA_SIN_SUSTENTO:
        st.warning(config.MARCA_SIN_SUSTENTO, icon=":material/help:")
    elif pd.isna(valor) or not str(valor).strip():
        st.caption("Vacío en el archivo")
    else:
        st.write(valor)

# Tarjeta con lo que dice el caso en el archivo de seguimiento.
def mostrar_caso(caso):
    with st.container(border=True):
        st.markdown("#### Lo que dice el caso")
        mostrar("Descripción", caso["descripcion"])
        mostrar("Observaciones", caso["observaciones"])
        mostrar("Causa / Solución", caso["causa_solucion"])

# Categoría y subcategoría en una línea o la marca si no hay.
def categoria_texto(ficha):
    if ficha["categoria"] == config.MARCA_SIN_SUSTENTO:
        return config.MARCA_SIN_SUSTENTO
    return f"{ficha['categoria']} / {ficha['subcategoria']}"

# Nombre de categoría para mostrar,sin los guiones bajos que trae del Excel.
def nombre_categoria(categoria):
    return categoria.replace("_", " ")