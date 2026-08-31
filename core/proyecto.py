import os
import json
import re
from datetime import datetime


def _normalizar_nombre_expediente(nombre):
    nombre = str(nombre or "incendio").strip()
    nombre = re.sub(r"[^A-Za-z0-9._-]+", "_", nombre)
    nombre = nombre.strip("._-") or "incendio"
    return nombre


def crear_expediente(analisis):

    incendio = analisis["incendio"]

    if incendio.get("id"):
        nombre = f"INC-{incendio['id']:06d}"
    else:
        nombre = f"MANUAL-{_normalizar_nombre_expediente(incendio['nombre'])}"

    carpeta = os.path.join("analisis", _normalizar_nombre_expediente(nombre))

    os.makedirs(carpeta, exist_ok=True)

    return carpeta


def guardar_json(carpeta, nombre_archivo, datos):

    ruta = os.path.join(carpeta, nombre_archivo)

    with open(ruta, "w", encoding="utf8") as archivo:

        json.dump(
            datos,
            archivo,
            indent=4,
            ensure_ascii=False
        )

    return ruta


def guardar_analisis(analisis):

    nombre = analisis["incendio"]["nombre"]

    carpeta = os.path.join(
        "analisis",
        _normalizar_nombre_expediente(nombre)
    )

    os.makedirs(carpeta, exist_ok=True)

    archivo = os.path.join(
        carpeta,
        "analisis.json"
    )

    with open(
        archivo,
        "w",
        encoding="utf8"
    ) as f:

        json.dump(
            analisis,
            f,
            indent=4,
            ensure_ascii=False
        )

    return carpeta