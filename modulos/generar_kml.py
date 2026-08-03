import math
import os

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
    estilo_primaria,
    estilo_secundaria,
    estilo_camino,
    estilo_sendero,
    estilo_viento,
    estilo_carrera_primaria,
    estilo_carrera_secundaria
)

from modulos.utilidades import escribir_log
from providers.openmeteo import obtener_meteorologia
from providers.topografia import obtener_topografia
from providers.combustible import obtener_combustible


def _distancia_posible(meteo, combustible, topografia):
    distancia = 1800
    viento = meteo.get("viento") or 0
    combustible_tipo = combustible.get("tipo_combustible", "Desconocido")
    pendiente = topografia.get("maxima_pendiente_pct") or 0

    if viento >= 40:
        distancia += 2200
    elif viento >= 25:
        distancia += 1400
    elif viento >= 10:
        distancia += 800

    if combustible_tipo in ("Bosque", "Matorral"):
        distancia += 1200
    elif combustible_tipo in ("Pastizal", "Agrícola"):
        distancia += 900

    if pendiente >= 15:
        distancia += 800

    return min(distancia, 6500)


def _calcular_coordenadas(latitud, longitud, distancia, direccion):
    rad = math.radians(direccion)
    delta_lat = math.cos(rad) * distancia / 111320
    factor_longitud = 111320 * math.cos(math.radians(latitud))
    if abs(factor_longitud) < 1e-6:
        factor_longitud = 1e-6
    delta_lon = math.sin(rad) * distancia / factor_longitud
    return latitud + delta_lat, longitud + delta_lon


def _direccion_propagacion_viento(meteo):
    direccion_viento = meteo.get("direccion")
    if direccion_viento is None:
        return None
    return (direccion_viento + 180) % 360


def _generar_carreras_potenciales(latitud, longitud, meteo, topografia, combustible):
    carreras = []
    distancia_base = _distancia_posible(meteo, combustible, topografia)
    direccion_viento = _direccion_propagacion_viento(meteo)

    if direccion_viento is not None:
        main_coords = [
            (longitud, latitud),
            (_calcular_coordenadas(latitud, longitud, distancia_base, direccion_viento)[1],
             _calcular_coordenadas(latitud, longitud, distancia_base, direccion_viento)[0])
        ]
        carreras.append({
            "name": "Carrera probable por viento",
            "description": (
                "La trayectoria principal toma en cuenta la dirección del viento y su velocidad, "
                "así como el combustible y la topografía cercana."
            ),
            "coords": main_coords,
            "tipo": "primaria"
        })

        for offset in (-25, 25):
            sub_distancia = distancia_base * 0.7
            sub_direccion = (direccion_viento + offset) % 360
            sub_coords = [
                (longitud, latitud),
                (_calcular_coordenadas(latitud, longitud, sub_distancia, sub_direccion)[1],
                 _calcular_coordenadas(latitud, longitud, sub_distancia, sub_direccion)[0])
            ]
            carreras.append({
                "name": f"Carrera secundaria por dispersión ({offset}°)",
                "description": (
                    "La dispersión se deriva de la variabilidad del viento y del combustible, "
                    "abriendo posibles frentes de propagación cercanos a la dirección principal."
                ),
                "coords": sub_coords,
                "tipo": "secundaria"
            })

    pendiente_direccion = topografia.get("pendiente_direccion")
    if pendiente_direccion is not None and pendiente_direccion != direccion_viento:
        pendiente_distancia = min(distancia_base * 0.8, 5500)
        pendiente_coords = [
            (longitud, latitud),
            (_calcular_coordenadas(latitud, longitud, pendiente_distancia, pendiente_direccion)[1],
             _calcular_coordenadas(latitud, longitud, pendiente_distancia, pendiente_direccion)[0])
        ]
        carreras.append({
            "name": "Carrera potencial por pendiente",
            "description": (
                "El fuego tiende a acelerarse en sentido ascendente. Esta trayectoria estima la "
                "propagación hacia el sector de mayor pendiente detectado en el terreno."
            ),
            "coords": pendiente_coords,
            "tipo": "secundaria"
        })

    if combustible.get("tipo_combustible") in ("Bosque", "Matorral") and direccion_viento is not None:
        combust_coords = [
            (longitud, latitud),
            (_calcular_coordenadas(latitud, longitud, distancia_base * 0.9, (direccion_viento + 15) % 360)[1],
             _calcular_coordenadas(latitud, longitud, distancia_base * 0.9, (direccion_viento + 15) % 360)[0])
        ]
        carreras.append({
            "name": "Sector de mayor riesgo por combustible",
            "description": (
                "La presencia de combustible denso aumenta la probabilidad de un avance rápido "
                "en el sector cercano a la dirección de propagación principal."
            ),
            "coords": combust_coords,
            "tipo": "secundaria"
        })

    return carreras


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

    try:
        import simplekml
    except ImportError:
        mensaje = (
            "El paquete 'simplekml' no está instalado. Instale `pip install simplekml` "
            "para generar el archivo KML."
        )
        print(mensaje)
        escribir_log(mensaje)
        return

    kml = simplekml.Kml()

    carpeta_incendio = kml.newfolder(name="🔥 Incendio")

    carpeta_carreras = kml.newfolder(name="🚨 Carreras primarias potenciales")

    carpeta_rutas = kml.newfolder(name="🛣 Rutas principales")

    carpeta_primarias = kml.newfolder(name="🚧 Carreteras primarias")

    carpeta_secundarias = kml.newfolder(name="🛤 Carreteras secundarias")

    carpeta_caminos = kml.newfolder(name="🚜 Caminos")

    carpeta_senderos = kml.newfolder(name="🚶 Senderos")

    carpeta_otros = kml.newfolder(name="📌 Otros caminos")

    # -----------------------------
    # Punto incendio
    # -----------------------------

    punto = carpeta_incendio.newpoint(
        name=nombre,
        coords=[(longitud, latitud)]
    )

    punto.style = estilo_incendio()

    # -----------------------------
    # Obtener datos ambientales para trazar posibles carreras
    # -----------------------------

    meteo = None
    topografia = None
    combustible = None

    try:
        print("Obteniendo meteorología y análisis de terreno...")
        meteo = obtener_meteorologia(latitud, longitud)
        topografia = obtener_topografia(latitud, longitud)
        combustible = obtener_combustible(latitud, longitud)
    except Exception as exc:
        escribir_log(f"No fue posible obtener los datos de análisis adicional: {exc}")

    # -----------------------------
    # Línea de viento (dirección de propagación)
    # -----------------------------

    if meteo and meteo.get("direccion") is not None:
        direccion_viento = (meteo.get("direccion") + 180) % 360
        distancia_viento = min(10000, max(5000, (meteo.get("viento") or 0) * 200))
        viento_coords = [
            (longitud, latitud),
            (
                _calcular_coordenadas(latitud, longitud, distancia_viento, direccion_viento)[1],
                _calcular_coordenadas(latitud, longitud, distancia_viento, direccion_viento)[0]
            )
        ]
        linea_viento = carpeta_carreras.newlinestring(
            name="Dirección del viento",
            coords=viento_coords
        )
        linea_viento.description = "Línea azul que marca la dirección predominante del viento."
        linea_viento.style = estilo_viento()

    if meteo and topografia and combustible:
        carreras = _generar_carreras_potenciales(latitud, longitud, meteo, topografia, combustible)
        for carrera in carreras:
            linea = carpeta_carreras.newlinestring(
                name=carrera["name"],
                coords=carrera["coords"]
            )
            linea.description = carrera["description"]
            if carrera.get("tipo") == "primaria":
                linea.style = estilo_carrera_primaria()
            else:
                linea.style = estilo_carrera_secundaria()

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

        elif categoria == "primaria":

            linea = carpeta_primarias.newlinestring(
                name=camino["nombre"],
                coords=camino["coordenadas"]
            )

            linea.style = estilo_primaria()

        elif categoria == "secundaria":

            linea = carpeta_secundarias.newlinestring(
                name=camino["nombre"],
                coords=camino["coordenadas"]
            )

            linea.style = estilo_secundaria()

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

        else:

            linea = carpeta_otros.newlinestring(
                name=camino["nombre"],
                coords=camino["coordenadas"]
            )

            linea.style = estilo_camino()

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