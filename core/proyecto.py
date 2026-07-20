import os
import json


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