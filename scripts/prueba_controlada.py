# -- Prueba controlada (objetivo específico 3): mide qué tan bien extrae el modelo la información del caso
# y si genera contenido sin sustento, comparando el borrador con la respuesta que se conoce de antemano.
#
# Uso, desde la carpeta del proyecto:  python scripts/prueba_controlada.py
#
# Usa el motor configurado (SGCT_PROVEEDOR); toma la clave de Gemini del entorno o de
# .streamlit/secrets.toml, igual que la app. No escribe en la base de datos.
# Los casos son ficticios: los genera scripts/generar_ejemplo.py, que además dice qué información
# trae escrita cada caso. Deja el detalle en resultados/prueba_controlada.csv para revisarlo a mano.

import csv
import os
import random
import re
import statistics
import sys
import tempfile
import time
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

# config lee las variables al importarse: los secretos tienen que estar antes en el entorno.
secretos = RAIZ / ".streamlit" / "secrets.toml"
if secretos.exists():
    for clave, valor in tomllib.loads(secretos.read_text(encoding="utf-8")).items():
        if clave in ("SGCT_PROVEEDOR", "GEMINI_API_KEY"):
            os.environ.setdefault(clave, str(valor))

import config
import generar_ejemplo
from core import carga, deteccion, generacion, proveedor

# Conjunto 1: el mismo archivo de ejemplo de la app. Conjunto 2: otro generado con las mismas reglas.
SEMILLAS = {"Conjunto 1": generar_ejemplo.SEMILLA, "Conjunto 2": generar_ejemplo.SEMILLA + 1}
CAMPOS_TEXTO = ("sintoma", "causa", "solucion")

# La capa gratuita de Gemini limita las solicitudes por minuto: se espera entre un caso y otro.
PAUSA_SEGUNDOS = 4.5 if proveedor.motor_activo() == "gemini" else 0

# Un campo cuenta como bien extraído si contiene al menos la mitad de las palabras con contenido de la
# respuesta esperada. El modelo redacta con sus palabras, así que no se exige el texto idéntico; los casos
# marcados "distinto" se revisan a mano en el CSV.
UMBRAL_COINCIDENCIA = 0.5
PALABRAS_VACIAS = {"para", "como", "pero", "porque", "cuando", "desde", "sobre", "entre", "este", "esta",
                   "estos", "estas", "que", "los", "las", "del", "con", "por", "una", "uno", "unos", "unas",
                   "sus", "son", "fue", "era", "han", "hay", "sin", "más", "mas", "muy", "también"}

SALIDA = RAIZ / "resultados" / "prueba_controlada.csv"


def palabras(texto):
    return {p for p in re.findall(r"\w+", carga.normalizar(texto)) if len(p) >= 4 and p not in PALABRAS_VACIAS}


# Qué parte de las palabras esperadas aparece en lo que escribió el modelo (de 0 a 1).
def coincidencia(esperado, salida):
    esperadas = palabras(esperado)
    return len(esperadas & palabras(salida)) / len(esperadas) if esperadas else 0.0


# Compara un campo de texto con lo esperado. None en "esperado" = el caso no trae esa información.
def evaluar(esperado, salida):
    vacio = salida == config.MARCA_SIN_SUSTENTO
    if esperado is None:
        return ("correcto_vacio", None) if vacio else ("sin_sustento", None)
    if vacio:
        return "omitido", 0.0
    valor = coincidencia(esperado, salida)
    return ("correcto" if valor >= UMBRAL_COINCIDENCIA else "distinto"), valor


def casos_del_conjunto(semilla, carpeta):
    filas, esperados = generar_ejemplo.construir_casos_con_respuestas(random.Random(semilla))
    archivo = Path(carpeta) / f"conjunto_{semilla}.xlsx"
    generar_ejemplo.escribir_excel(filas, archivo)
    # Se carga con carga.py, como lo haría la app, para probar el mismo camino.
    documentables = deteccion.filtrar_documentables(carga.cargar(archivo))
    respuestas = {e["ha"]: e for e in esperados}
    return [(caso, respuestas[caso["ha"]]) for _, caso in documentables.iterrows()]


def main():
    print(f"Motor: {proveedor.motor_activo()}" + (f" ({config.GEMINI_MODELO})" if proveedor.motor_activo() == "gemini" else ""))
    registros = []
    with tempfile.TemporaryDirectory() as carpeta:
        for nombre, semilla in SEMILLAS.items():
            casos = casos_del_conjunto(semilla, carpeta)
            print(f"{nombre}: {len(casos)} casos documentables")
            for n, (caso, esperado) in enumerate(casos, start=1):
                borrador = generacion.generar_borrador(caso)
                base = {"conjunto": nombre, "ha": caso["ha"], "motor": borrador.motor,
                        "duracion_ms": borrador.duracion_ms, "preguntas": len(borrador.preguntas)}
                for campo in CAMPOS_TEXTO:
                    resultado, valor = evaluar(esperado[campo], getattr(borrador, campo))
                    registros.append({**base, "campo": campo, "esperado": esperado[campo] or "",
                                      "salida": getattr(borrador, campo), "resultado": resultado,
                                      "coincidencia": "" if valor is None else round(valor, 2)})
                # Categoría: se compara el par completo con la clasificación verdadera del caso.
                par = (borrador.categoria, borrador.subcategoria)
                if esperado["categoria_en_archivo"]:
                    resultado = "del_archivo"
                elif borrador.categoria == config.MARCA_SIN_SUSTENTO:
                    resultado = "omitido"
                else:
                    resultado = "correcto" if par == (esperado["categoria"], esperado["subcategoria"]) else "distinto"
                registros.append({**base, "campo": "categoria", "esperado": " / ".join(
                    (esperado["categoria"], esperado["subcategoria"])), "salida": " / ".join(par),
                    "resultado": resultado, "coincidencia": ""})
                print(f"  {n:2d}/{len(casos)} HA {caso['ha']} · {borrador.motor} · {borrador.duracion_ms / 1000:.1f} s")
                time.sleep(PAUSA_SEGUNDOS)

    SALIDA.parent.mkdir(exist_ok=True)
    with open(SALIDA, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(registros[0]))
        escritor.writeheader()
        escritor.writerows(registros)

    resumir(registros)
    print(f"\nDetalle: {SALIDA}")


def resumir(registros):
    texto = [r for r in registros if r["campo"] in CAMPOS_TEXTO]
    con_info = [r for r in texto if r["esperado"]]
    sin_info = [r for r in texto if not r["esperado"]]
    contar = lambda filas, resultado: sum(1 for r in filas if r["resultado"] == resultado)

    casos = {(r["conjunto"], r["ha"]): r for r in registros}.values()
    motores = {}
    for r in casos:
        motores[r["motor"]] = motores.get(r["motor"], 0) + 1

    print("\n=== Resultados ===")
    print(f"Casos: {len(casos)} · motor que respondió: {motores}")
    print(f"Campos de texto evaluados: {len(texto)} (síntoma, causa y solución de cada caso)")
    print(f"\nCampos con información en el caso: {len(con_info)}")
    print(f"  extraídos correctamente: {contar(con_info, 'correcto')} "
          f"({100 * contar(con_info, 'correcto') / len(con_info):.1f} %)   umbral: 80 % o más")
    print(f"  marcados sin sustento aunque había información: {contar(con_info, 'omitido')}")
    print(f"  escritos pero distintos de lo esperado (revisar a mano): {contar(con_info, 'distinto')}")
    print(f"\nCampos sin información en el caso: {len(sin_info)}")
    print(f"  marcados [SIN SUSTENTO] (correcto): {contar(sin_info, 'correcto_vacio')}")
    print(f"  completados sin sustento: {contar(sin_info, 'sin_sustento')} "
          f"({100 * contar(sin_info, 'sin_sustento') / len(sin_info):.1f} % de estos campos; "
          f"{100 * contar(sin_info, 'sin_sustento') / len(texto):.1f} % de todos)   umbral: menos del 5 %")

    categoria = [r for r in registros if r["campo"] == "categoria"]
    propuestas = [r for r in categoria if r["resultado"] in ("correcto", "distinto")]
    print(f"\nCategoría ({len(categoria)} casos): {contar(categoria, 'del_archivo')} venían del archivo, "
          f"{len(propuestas)} propuestas por el modelo ({contar(categoria, 'correcto')} correctas), "
          f"{contar(categoria, 'omitido')} marcadas sin sustento")

    por_caso = list(casos)
    print(f"\nPreguntas por caso: {statistics.mean(r['preguntas'] for r in por_caso):.1f} en promedio")
    print(f"Tiempo de generación: mediana {statistics.median(r['duracion_ms'] for r in por_caso) / 1000:.1f} s")


if __name__ == "__main__":
    main()
