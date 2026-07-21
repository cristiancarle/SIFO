import os
import json
from datetime import datetime


def crear_expediente(analisis):

    incendio = analisis["incendio"]

    nombre = f"INC-{incendio['id']:06d}"

    carpeta = os.path.join("analisis", nombre)

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
        nombre.replace(" ", "_")
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