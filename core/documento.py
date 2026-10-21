# -- Documento de la ficha en Word.
# La ficha vive en la base de datos; el Word se arma de nuevo cada vez que se pide, a partir de
# esos datos y de la plantilla plantillas/ficha.docx. 

import io
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage, RichText

import config

logger = logging.getLogger(__name__)

PLANTILLA = config.BASE_DIR / "plantillas" / "ficha.docx"
TIPO_WORD = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# Fecha guardada en la base (UTC, "AAAA-MM-DD HH:MM:SS") -> fecha y hora de Colombia.
def fecha_local(texto):
    utc = datetime.strptime(texto, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return utc.astimezone(ZoneInfo(config.ZONA_HORARIA))


# Fecha que viene del Excel, como texto, a "dd/mm/aaaa". Si no se reconoce, se deja como vino:
# es mejor mostrar el texto original que una fecha mal interpretada.
def fecha_excel(texto):
    if not texto:
        return ""
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(texto).strip(), formato).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return str(texto)

def nombre_flujo(id_flujo, nombre):
    id_flujo = "" if id_flujo is None or str(id_flujo) in ("", "nan") else str(id_flujo).strip()
    nombre = "" if nombre is None or str(nombre) in ("", "nan") else str(nombre).strip()
    return f"{id_flujo} - {nombre}" if id_flujo and nombre else (nombre or id_flujo)

# Segundos en texto corto: "24 s", "3 min 10 s".
def duracion_texto(segundos):
    minutos, segundos = divmod(int(segundos), 60)
    horas, minutos = divmod(minutos, 60)
    if horas:
        return f"{horas} h {minutos} min"
    return f"{minutos} min {segundos} s" if minutos else f"{segundos} s"

# Los datos de la ficha ya listos para mostrarse, en texto. Los usan el Word y la vista en pantalla
def datos_documento(ficha):
    final = ficha["estado"] == "final"
    creada = fecha_local(ficha["creada_en"])
    modificada = fecha_local(ficha["actualizada_en"])

    if ficha["categoria"] == config.MARCA_SIN_SUSTENTO:
        categoria = config.MARCA_SIN_SUSTENTO
    else:
        categoria = f"{ficha['categoria'].replace('_', ' ')} / {ficha['subcategoria']}"

    return {
        "ha": ficha["ha"],
        "estado": "Ficha final" if final else "Borrador",
        "tipo": ficha["tipo"] or "",
        "flujo": nombre_flujo(ficha.get("id_flujo"), ficha["flujo"]),
        "responsable": ficha["responsable"] or "",
        "sprint": ficha.get("sprint") or "",
        "usuario_reporta": ficha.get("usuario_reporta") or "",
        "fecha_recepcion": fecha_excel(ficha.get("fecha_recepcion")),
        "fecha_cierre": fecha_excel(ficha.get("fecha_cierre")),
        "generada": f"{creada:%d/%m/%Y %H:%M}",
        "documentada_en": duracion_texto((modificada - creada).total_seconds()) if final else "Pendiente",
        "motor": f"{ficha['motor']} ({ficha['modelo']})" if ficha["modelo"] else ficha["motor"],
        "sintoma": ficha["sintoma"] or "",
        "causa": ficha["causa"] or "",
        "solucion": ficha["solucion"] or "",
        "categoria": categoria,
        "lecciones": ficha.get("lecciones") or "",
        "evidencias": [{"nombre": e["nombre"], "contenido": e["contenido"]} for e in ficha.get("evidencias", [])],
        "preguntas": [
            {
                "orden": p["orden"],
                "texto": p["texto"],
                "respuesta": p["respuesta"] if p["respuesta"] is not None else "Sin responder",
            }
            for p in ficha["preguntas"]
        ],
    }

# Arma el Word de una ficha y lo devuelve como bytes, listo para descargar. "ficha" es lo que devuelve fichas.abrir().
def generar_word(ficha):
    datos = datos_documento(ficha)
    documento = DocxTemplate(PLANTILLA)
    for campo in ("sintoma", "causa", "solucion", "lecciones"):
        datos[campo] = RichText(datos[campo]) if datos[campo] else ""
    for pregunta in datos["preguntas"]:
        pregunta["respuesta"] = RichText(pregunta["respuesta"])
    for evidencia in datos["evidencias"]:
        evidencia["imagen"] = InlineImage(documento, io.BytesIO(evidencia["contenido"]), width=Mm(150))

    documento.render(datos)
    salida = io.BytesIO()
    documento.save(salida)

    logger.info("Documento Word generado para HA %s", ficha["ha"])
    return salida.getvalue()

# Nombre del archivo descargado.
def nombre_archivo(ficha):
    return f"Ficha_HA_{ficha['ha']}.docx"