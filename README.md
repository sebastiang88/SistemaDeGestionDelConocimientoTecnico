# SGCT — Sistema de Gestión del Conocimiento Técnico

Plataforma que genera el borrador de la ficha técnica de cada falla resuelta a partir de lo que
ya está escrito en el archivo de seguimiento del equipo y le pregunta al responsable sólo lo que
no se puede deducir: máximo tres preguntas.

Producto mínimo viable de la materia de practicas por la modalidad de emprendimiento, Facultad de Ingeniería, Corporación
Universitaria Iberoamericana.

**Aplicación en línea:** _(pendiente de despliegue en Streamlit Community Cloud)_

> Todos los datos de este repositorio y de la aplicación en línea son **ficticios**. Ningún dato
> real del cliente entra al repositorio, a la plataforma ni a un servicio de IA externo.

## El problema y la hipótesis

El equipo de soporte no documenta las fallas técnicas que resuelve, los comentarios del archivo
de seguimiento informan el estado de la gestión, no la causa ni la solución. En la línea base,
medida sobre 240 casos, la columna de categoría de causa estaba diligenciada en un 0 %.

**Hipótesis:** si una plataforma genera el borrador a partir de lo que ya está escrito y sólo
pregunta lo que falta, el desarrollador documenta, porque responder tres preguntas cuesta menos
que redactar un documento.

**La decisión de diseño que define el producto:** el modelo de lenguaje tiene prohibido completar
con información que no esté en el caso. Lo que no puede sustentar lo marca como `[SIN SUSTENTO]`
y lo convierte en una pregunta. En documentación técnica una causa inventada es peor que un
campo vacío.

## Qué hace

| Pantalla | Módulos |
|---|---|
| **Casos pendientes** | 1. Carga el archivo de seguimiento en Excel · 2. Detecta los casos cerrados sin ficha |
| **Documentar** | 3. Genera el borrador · 4. Hace hasta tres preguntas al responsable · 5. Guarda la ficha |
| **Fichas** | 6. Consulta y abre las fichas guardadas |
| Tablero y Configuración | Maquetas: se muestran como tales y no son funcionalidad entregada |

## Cómo correrlo en local

Requiere Python 3.13.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Arranca con el motor **simulado** (reglas locales, sin clave ni conexión). En **Casos pendientes**
use el botón **Usar archivo de ejemplo**.

### Variables de entorno

| Variable | Para qué | Por defecto |
|---|---|---|
| `SGCT_PROVEEDOR` | Motor de lenguaje: `simulado` o `gemini` | `simulado` |
| `GEMINI_API_KEY` | Clave de la API de Gemini | (sin clave se usa el simulado) |
| `SGCT_LOG_NIVEL` | Nivel de los logs: `DEBUG`, `INFO`, `WARNING` | `INFO` |

Si Gemini falla por cualquier motivo (clave inválida, cuota agotada, sin conexión, respuesta
inutilizable), la plataforma usa el motor simulado y lo registra en el log: la aplicación nunca
queda sin motor. Cada ficha guarda qué motor la generó de verdad.

## Cómo está organizado

```
app.py                 Punto de entrada: logs, base de datos y menú
config.py              Constantes: rutas, columnas del Excel, reglas, motor y catálogo de causas
ui.py                  Piezas de pantalla compartidas
core/                  Lógica, sin interfaz (se puede probar desde la terminal)
  carga.py             Módulo 1: lectura del archivo de seguimiento
  deteccion.py         Módulo 2: casos cerrados sin ficha
  proveedor.py         Único punto de salida hacia el modelo (Gemini y simulado)
  generacion.py        Módulos 3 y 4: prompt, validación del borrador y preguntas
  fichas.py            Módulos 5 y 6: guardar, responder y consultar
  db.py                SQLite: conexión, tablas y consultas
pages/                 Pantallas
scripts/
  generar_ejemplo.py   Genera el archivo ficticio de ejemplo (semilla fija, reproducible)
data/ejemplo/          Archivo de seguimiento ficticio
```

`core/proveedor.py` es el único módulo que habla con el modelo de lenguaje. Reemplazar Gemini
por un modelo local (Ollama) para operar con datos reales sólo requiere cambiar ese archivo.

## Datos

- **Base de datos:** SQLite, con tres tablas: `caso`, `ficha` y `pregunta`. Las preguntas van en
  una tabla aparte para medir cuántas hicieron falta por ficha y cuántas quedaron sin responder.
- **Archivo de ejemplo:** `data/ejemplo/casos_ficticios.xlsx`, 60 casos inventados que imitan la
  estructura del archivo real (encabezados en la fila 7, dos columnas `#HA`, estados numerados).
  Se regenera con `python scripts/generar_ejemplo.py`.
- **Logs:** en la consola y en `logs/sgct.log`.

## Tecnologías

Python, Streamlit, pandas, SQLite, Gemini (Google AI) y Streamlit Community Cloud.

## Autoría

Juan Sebastián Guevara Cruz
Se usaron asistentes de IA para el desarrollo parcial, el diseño, la revisión
del código y las decisiones técnicas son responsabilidad del autor.