import os

import simplekml

from config import KML_DIR
from config import RADIO_ANALISIS

from modulos.database import obtener_incendio_por_id
from modulos.cartografia import (
    obtener_red_vial,
    clasificar_camino
)

from modulos.estilos import (
    estilo_incendio,
    estilo_ruta,
    estilo_camino,
    estilo_sendero
)

from modulos.utilidades import escribir_log


def generar_kml(id_incendio):

    incendio = obtener_incendio_por_id(id_incendio)

    if incendio is None:

        print("Incendio inexistente.")
        return

    # -----------------------------
    # Datos
    # -----------------------------

    latitud = incendio[6]
    longitud = incendio[7]
    nombre = incendio[3]

    escribir_log(f"Generando mapa de {nombre}")

    # -----------------------------
    # Crear KML
    # -----------------------------

    kml = simplekml.Kml()

    carpeta_incendio = kml.newfolder(name="🔥 Incendio")

    carpeta_rutas = kml.newfolder(name="🛣 Rutas")

    carpeta_caminos = kml.newfolder(name="🚜 Caminos")

    carpeta_senderos = kml.newfolder(name="🚶 Senderos")

    # -----------------------------
    # Punto incendio
    # -----------------------------

    punto = carpeta_incendio.newpoint(
        name=nombre,
        coords=[(longitud, latitud)]
    )

    punto.style = estilo_incendio()

    # -----------------------------
    # Descargar red vial
    # -----------------------------

    print("Descargando OpenStreetMap...")

    caminos = obtener_red_vial(
        latitud,
        longitud,
        RADIO_ANALISIS
    )

    print(f"{len(caminos)} caminos encontrados")

    # -----------------------------
    # Dibujar
    # -----------------------------

    for camino in caminos:

        categoria = clasificar_camino(
            camino["tipo"]
        )

        linea = None

        if categoria == "ruta":

            linea = carpeta_rutas.newlinestring(
                name=camino["nombre"],
                coords=camino["coordenadas"]
            )

            linea.style = estilo_ruta()

        elif categoria == "camino":

            linea = carpeta_caminos.newlinestring(
                name=camino["nombre"],
                coords=camino["coordenadas"]
            )

            linea.style = estilo_camino()

        elif categoria == "sendero":

            linea = carpeta_senderos.newlinestring(
                name=camino["nombre"],
                coords=camino["coordenadas"]
            )

            linea.style = estilo_sendero()

    # -----------------------------
    # Guardar
    # -----------------------------

    os.makedirs(KML_DIR, exist_ok=True)

    archivo = os.path.join(
        KML_DIR,
        f"{nombre}.kml"
    )

    kml.save(archivo)

    escribir_log("Mapa generado correctamente.")

    print()

    print("===================================")
    print("Mapa generado correctamente")
    print(archivo)
    print("===================================")