# -- Piezas de pantalla que comparten varias páginas.

import pandas as pd
import streamlit as st
import config

ETIQUETAS = {"sintoma": "Síntoma", "causa": "Causa", "solucion": "Solución", "categoria": "Categoría de la causa"}

# Estilos que el tema de Streamlit no cubre. 
ESTILOS = """
<style>
[class*="st-key-tarjeta"] {
    background: #FFFFFF;
    border: 1px solid #D9E1EA;
    border-radius: 0.8rem;
    padding: 1.1rem 1.3rem;
    box-shadow: 0 1px 2px rgba(16, 42, 67, 0.05), 0 4px 14px rgba(16, 42, 67, 0.05);
}
[class*="st-key-hoja"] {
    background: #FFFFFF;
    border: 1px solid #D9E1EA;
    border-top: 6px solid #1F4E79;
    border-radius: 0.5rem;
    padding: 2.2rem 2.6rem;
    box-shadow: 0 10px 30px rgba(16, 42, 67, 0.10);
}
[data-testid="stMetric"] { background: #FFFFFF; }
/* Portada de Inicio. */
.sgct-portada {
    background: linear-gradient(120deg, #0F2A44 0%, #1F4E79 55%, #3A7BBF 100%);
    color: #FFFFFF;
    border-radius: 1rem;
    padding: 2.2rem 2.4rem;
    margin-bottom: 0.4rem;
}
.sgct-portada h1 { color: #FFFFFF; margin: 0 0 0.4rem 0; font-size: 2.1rem; padding: 0; }
.sgct-portada p { color: #D6E4F2; font-size: 1.05rem; margin: 0; max-width: 46rem; line-height: 1.55; }
.sgct-portada .sgct-etiqueta {
    display: inline-block; background: rgba(255, 255, 255, 0.14); color: #FFFFFF;
    padding: 0.2rem 0.7rem; border-radius: 999px; font-size: 0.8rem; margin-bottom: 0.9rem;
}
</style>
"""

# Carga los estilos y el logo. Se llama una vez por ejecución, desde app.py.
def aplicar_estilos():
    st.html(ESTILOS)
    st.logo(str(config.BASE_DIR / "assets" / "logo.svg"), icon_image=str(config.BASE_DIR / "assets" / "icono.svg"))

# Título de pantalla con una línea que explica para qué sirve.
def encabezado(titulo, subtitulo):
    st.title(titulo)
    st.caption(subtitulo)

# Etiqueta de color con el estado de la ficha.
def etiqueta_estado(estado):
    if estado == "final":
        st.badge("Ficha final", color="green", icon=":material/check_circle:")
    else:
        st.badge("Borrador", color="orange", icon=":material/edit:")

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
def mostrar_caso(caso, clave="tarjeta_caso"):
    with st.container(key=clave):
        st.markdown("#### :material/description: Lo que dice el caso")
        mostrar("Descripción", caso["descripcion"])
        mostrar("Observaciones", caso["observaciones"])
        mostrar("Causa / Solución", caso["causa_solucion"])

# Categoría y subcategoría en una línea o la marca si no hay.
def categoria_texto(ficha):
    if ficha["categoria"] == config.MARCA_SIN_SUSTENTO:
        return config.MARCA_SIN_SUSTENTO
    return f"{ficha['categoria']} / {ficha['subcategoria']}"

# Vista en pantalla del documento de la ficha: el mismo contenido y el mismo orden del Word, a partir de documento.datos_documento()
def vista_documento(datos, estado):
    with st.container(key="hoja"):
        st.markdown("## Ficha técnica")
        st.markdown(f"**HA {datos['ha']}**")
        etiqueta_estado(estado)
        st.table(
            pd.DataFrame({
                "Dato": ["Tipo", "Flujo", "Sprint", "Reportado por", "Responsable", "Fecha de recepción",
                         "Fecha de cierre", "Generada", "Documentada en", "Motor"],
                "Valor": [datos["tipo"], datos["flujo"], datos["sprint"], datos["usuario_reporta"],
                          datos["responsable"], datos["fecha_recepcion"], datos["fecha_cierre"],
                          datos["generada"], datos["documentada_en"], datos["motor"]],
            }).set_index("Dato")
        )
        mostrar("Síntoma", datos["sintoma"])
        mostrar("Causa", datos["causa"])
        mostrar("Solución", datos["solucion"])
        mostrar("Categoría de la causa", datos["categoria"])

        # Secciones opcionales: como en el Word, sólo aparecen si se llenaron.
        if datos["lecciones"]:
            mostrar("Lección aprendida / observaciones", datos["lecciones"])
        if datos["evidencias"]:
            st.markdown("**Evidencias**")
            for evidencia in datos["evidencias"]:
                st.image(evidencia["contenido"], caption=evidencia["nombre"])

        if datos["preguntas"]:
            st.markdown("**Preguntas al responsable**")
            for pregunta in datos["preguntas"]:
                st.markdown(f"{pregunta['orden']}. {pregunta['texto']}")
                st.caption(pregunta["respuesta"])

# Aviso que va arriba de cada pantalla de maqueta.
def aviso_maqueta(detalle):
    st.warning(f"**Maqueta.** {detalle} No forma parte de la funcionalidad entregada en el MVP.",
               icon=":material/construction:")

# Nombre de categoría para mostrar sin los guiones bajos que trae del Excel.
def nombre_categoria(categoria):
    return categoria.replace("_", " ")