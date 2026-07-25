import os
import json


def crear_expediente(analisis):
    incendio = analisis["incendio"]

    nombre = f"INC-{incendio['id']:06d}"

    carpeta = os.path.join("analisis", nombre)

    os.makedirs(carpeta, exist_ok=True)

    return carpeta


def guardar_json(carpeta, nombre_archivo, datos):
    ruta = os.path.join(carpeta, nombre_archivo)

    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(
            datos,
            archivo,
            indent=4,
            ensure_ascii=False
        )

    return ruta


def guardar_analisis(analisis):
    carpeta = crear_expediente(analisis)

    guardar_json(carpeta, "analisis.json", analisis)

    if "meteorologia" in analisis:
        guardar_json(carpeta, "meteorologia.json", analisis["meteorologia"])

    if "hidrografia" in analisis:
        guardar_json(carpeta, "hidrografia.json", analisis["hidrografia"])

    return carpeta