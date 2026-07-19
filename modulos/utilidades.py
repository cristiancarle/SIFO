import os
from datetime import datetime
from config import LOG_DIR


def crear_carpetas():

    os.makedirs(LOG_DIR, exist_ok=True)


def escribir_log(texto):

    crear_carpetas()

    archivo = os.path.join(
        LOG_DIR,
        datetime.now().strftime("%Y-%m-%d") + ".log"
    )

    with open(archivo, "a", encoding="utf-8") as f:

        hora = datetime.now().strftime("%H:%M:%S")

        f.write(f"[{hora}] {texto}\n")