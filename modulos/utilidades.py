import os
import re
from datetime import datetime
from config import DATOS_DIR, INFORMES_DIR, KML_DIR, LOG_DIR


def crear_carpetas():

    os.makedirs(DATOS_DIR, exist_ok=True)
    os.makedirs(KML_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(INFORMES_DIR, exist_ok=True)


def escribir_log(texto):

    crear_carpetas()

    archivo = os.path.join(
        LOG_DIR,
        datetime.now().strftime("%Y-%m-%d") + ".log"
    )

    with open(archivo, "a", encoding="utf-8") as f:

        hora = datetime.now().strftime("%H:%M:%S")

        f.write(f"[{hora}] {texto}\n")


def sanitizar_nombre_archivo(nombre, extension):

    nombre_limpio = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", nombre).strip()
    nombre_limpio = nombre_limpio.rstrip(". ")

    if not nombre_limpio:
        nombre_limpio = "incendio"

    if not nombre_limpio.lower().endswith(extension.lower()):
        nombre_limpio = f"{nombre_limpio}{extension}"

    return nombre_limpio