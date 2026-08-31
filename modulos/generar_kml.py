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
    estilo_carrera_secundaria,
    estilo_progresion,
    estilo_poligono_riesgo
)

from modulos.utilidades import escribir_log
from providers.openmeteo import obtener_meteorologia, obtener_pronostico_24h
from providers.topografia import obtener_topografia
from providers.combustible import obtener_combustible
from providers.copernicus import obtener_humedad_combustible_swid
from core.riesgo import predecir_propagacion_incendio, analizar_ia_propagacion


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


def _direccion_propagacion_total(meteo, topografia):
    direccion_viento = _direccion_propagacion_viento(meteo)
    pendiente_direccion = topografia.get("pendiente_direccion")

    if direccion_viento is None and pendiente_direccion is None:
        return None
    if direccion_viento is None:
        return pendiente_direccion
    if pendiente_direccion is None:
        return direccion_viento

    # Si el viento empuja en una dirección y la pendiente se orienta hacia otra,
    # la propagación dominante se desvía hacia la bisectriz que combina ambas fuerzas.
    diferencia = (pendiente_direccion - direccion_viento + 360) % 360
    if diferencia > 180:
        diferencia -= 360

    direccion_comb = (direccion_viento + diferencia / 2.0) % 360
    return direccion_comb


def _calcular_factor_riesgo_periodo(meteo_periodo, topografia, combustible):
    temperatura = meteo_periodo.get("temperatura") or 20
    humedad = meteo_periodo.get("humedad") or 50
    viento = meteo_periodo.get("viento") or 0
    pendiente = topografia.get("maxima_pendiente_pct") or 0
    combustible_tipo = combustible.get("tipo_combustible", "Desconocido")

    factor = 1.0
    factor += max(0, (temperatura - 20) / 25) * 0.8
    factor += max(0, (50 - humedad) / 50) * 0.9
    factor += max(0, (viento - 8) / 25) * 1.1
    factor += min(1.0, pendiente / 35) * 0.6

    if combustible_tipo in ("Bosque", "Matorral"):
        factor += 0.7
    elif combustible_tipo in ("Pastizal", "Agrícola"):
        factor += 0.4

    return min(factor, 4.5)


def _generar_poligono_progresion(latitud, longitud, lat_fin, lon_fin, ancho_metros=800):
    if abs(lat_fin - latitud) < 1e-9 and abs(lon_fin - longitud) < 1e-9:
        return [(longitud, latitud), (longitud + 0.0001, latitud), (longitud + 0.0001, latitud + 0.0001), (longitud, latitud + 0.0001)]

    direccion = math.degrees(math.atan2(lon_fin - longitud, lat_fin - latitud))
    direccion = (direccion + 360) % 360

    distancia_total = math.hypot(
        (lat_fin - latitud) * 111_320,
        (lon_fin - longitud) * 111_320 * math.cos(math.radians((latitud + lat_fin) / 2))
    )
    semi_major = max(350, min(5500, distancia_total * 0.6))
    semi_minor = max(250, min(2600, ancho_metros * 0.8))

    offset_m = semi_major * 0.55
    centro_lat = latitud + (math.cos(math.radians(direccion)) * offset_m / 111_320)
    centro_lon = longitud + (math.sin(math.radians(direccion)) * offset_m / (111_320 * math.cos(math.radians(latitud))))
    rot_rad = math.radians(direccion)

    puntos = []
    for angulo in range(0, 360, 10):
        rad = math.radians(angulo)
        x = semi_major * math.cos(rad)
        y = semi_minor * math.sin(rad)

        x_rot = x * math.cos(rot_rad) - y * math.sin(rot_rad)
        y_rot = x * math.sin(rot_rad) + y * math.cos(rot_rad)

        lat_punto = centro_lat + (y_rot / 111_320)
        lon_punto = centro_lon + (x_rot / (111_320 * math.cos(math.radians(centro_lat))))
        puntos.append((lon_punto, lat_punto))

    return puntos


def _nivel_riesgo_por_factor(factor_riesgo):
    if factor_riesgo >= 3.3:
        return 'Extremo'
    if factor_riesgo >= 2.4:
        return 'Alto'
    if factor_riesgo >= 1.5:
        return 'Moderado'
    return 'Bajo'


def _generar_progresion_3h(latitud, longitud, pronostico_24h, meteo, topografia, combustible):
    if not pronostico_24h:
        return []

    base_direccion = meteo.get("direccion")
    base_viento = meteo.get("viento") or 0
    progresion = []

    for idx, periodo in enumerate(pronostico_24h):
        direccion = periodo.get("direccion") or base_direccion
        if direccion is None:
            continue

        direccion_viento = (direccion + 180) % 360
        pendiente_direccion = topografia.get("pendiente_direccion")

        if pendiente_direccion is not None:
            diferencia = (pendiente_direccion - direccion_viento + 360) % 360
            if diferencia > 180:
                diferencia -= 360
            direccion_captura = (direccion_viento + diferencia * 0.55) % 360
        else:
            direccion_captura = direccion_viento

        factor_riesgo = _calcular_factor_riesgo_periodo(periodo, topografia, combustible)
        distancia = 500 + (base_viento * 60) + (factor_riesgo * 700)
        distancia = min(distancia, 9000)

        lat_fin, lon_fin = _calcular_coordenadas(latitud, longitud, distancia, direccion_captura)
        ancho = 600 + factor_riesgo * 180
        hora = periodo.get("hora", f"{idx * 3:02d}:00")

        niveles = ["Extremo", "Alto", "Moderado", "Moderado", "Bajo", "Bajo"]
        nivel_riesgo = niveles[min(idx, len(niveles) - 1)]
        descripcion = (
            f"Riesgo estimado: {factor_riesgo:.2f} ({nivel_riesgo}). "
            f"Temperatura {periodo.get('temperatura', 'N/A')}°C, humedad {periodo.get('humedad', 'N/A')}%, "
            f"viento {periodo.get('viento', 'N/A')} km/h, pendiente máxima {topografia.get('maxima_pendiente_pct', 'N/A')}%."
        )
        progresion.append({
            "name": f"Progresión estimada {hora} (3h)",
            "description": descripcion,
            "coords": _generar_poligono_progresion(latitud, longitud, lat_fin, lon_fin, ancho_metros=ancho),
            "tipo": "primaria" if idx == 0 else "secundaria",
            "nivel_riesgo": nivel_riesgo
        })

    return progresion


def _generar_carreras_potenciales(latitud, longitud, meteo, topografia, combustible):
    carreras = []
    distancia_base = _distancia_posible(meteo, combustible, topografia)
    direccion_viento = _direccion_propagacion_viento(meteo)
    direccion_total = _direccion_propagacion_total(meteo, topografia)

    if direccion_total is not None:
        main_coords = [
            (longitud, latitud),
            (_calcular_coordenadas(latitud, longitud, distancia_base, direccion_total)[1],
             _calcular_coordenadas(latitud, longitud, distancia_base, direccion_total)[0])
        ]
        carreras.append({
            "name": "Carrera probable por viento y pendiente",
            "description": (
                "La trayectoria principal combina la dirección del viento y la pendiente del terreno, "
                "lo que hace que el fuego avance preferentemente en la dirección resultante entre ambas fuerzas."
            ),
            "coords": main_coords,
            "tipo": "primaria"
        })

        for offset in (-20, 20):
            sub_distancia = distancia_base * 0.7
            sub_direccion = (direccion_total + offset) % 360
            sub_coords = [
                (longitud, latitud),
                (_calcular_coordenadas(latitud, longitud, sub_distancia, sub_direccion)[1],
                 _calcular_coordenadas(latitud, longitud, sub_distancia, sub_direccion)[0])
            ]
            carreras.append({
                "name": f"Carrera secundaria por combinación de viento y pendiente ({offset}°)",
                "description": (
                    "La dispersión se deriva de la integración de viento y pendiente; la propagación puede desviarse hacia sectores "
                    "laterales de la dirección dominante."
                ),
                "coords": sub_coords,
                "tipo": "secundaria"
            })

    if direccion_viento is not None:
        for offset in (-25, 25):
            sub_distancia = distancia_base * 0.7
            sub_direccion = (direccion_viento + offset) % 360
            sub_coords = [
                (longitud, latitud),
                (_calcular_coordenadas(latitud, longitud, sub_distancia, sub_direccion)[1],
                 _calcular_coordenadas(latitud, longitud, sub_distancia, sub_direccion)[0])
            ]
            carreras.append({
                "name": f"Carrera por viento ({offset}°)",
                "description": "La dispersión del viento introduce variabilidad en la dirección del avance del incendio.",
                "coords": sub_coords,
                "tipo": "secundaria"
            })

    pendiente_direccion = topografia.get("pendiente_direccion")
    if pendiente_direccion is not None:
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

    if combustible.get("tipo_combustible") in ("Bosque", "Matorral") and direccion_total is not None:
        combust_coords = [
            (longitud, latitud),
            (_calcular_coordenadas(latitud, longitud, distancia_base * 0.9, (direccion_total + 15) % 360)[1],
             _calcular_coordenadas(latitud, longitud, distancia_base * 0.9, (direccion_total + 15) % 360)[0])
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

    carpeta_progresion = kml.newfolder(name="⏳ Progresión estimada cada 3 horas")

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
        humedad_combustible = obtener_humedad_combustible_swid(
            latitud,
            longitud,
            temperatura=meteo.get("temperatura"),
            humedad_relativa=meteo.get("humedad"),
            pendiente_pct=topografia.get("maxima_pendiente_pct"),
        )
        combustible["humedad_combustible"] = humedad_combustible["humedad_combustible"]
        combustible["fuente_humedad_combustible"] = humedad_combustible["fuente"]

        prediccion = predecir_propagacion_incendio(
            meteo,
            topografia,
            combustible,
            humedad_combustible["humedad_combustible"],
        )
        analisis_ia = analizar_ia_propagacion(meteo, topografia, combustible)

        descripcion_prediccion = (
            f"Predicción: {prediccion['velocidad']} | "
            f"humedad del combustible {prediccion['humedad_combustible']}% | "
            f"dirección probable {analisis_ia.get('direccion_probable_cardinal', 'N/A')} | "
            f"{analisis_ia.get('descripcion', prediccion['descripcion'])}"
        )

        carreras = _generar_carreras_potenciales(latitud, longitud, meteo, topografia, combustible)
        for carrera in carreras:
            linea = carpeta_carreras.newlinestring(
                name=carrera["name"],
                coords=carrera["coords"]
            )
            linea.description = f"{carrera['description']}\n\n{descripcion_prediccion}"
            if carrera.get("tipo") == "primaria":
                linea.style = estilo_carrera_primaria()
            else:
                linea.style = estilo_carrera_secundaria()

        placemark = carpeta_incendio.newpoint(
            name="Predicción de propagación",
            coords=[(longitud, latitud)]
        )
        placemark.description = descripcion_prediccion
        placemark.style = estilo_incendio()

        try:
            pronostico = obtener_pronostico_24h(latitud, longitud)
            progresion = _generar_progresion_3h(latitud, longitud, pronostico, meteo, topografia, combustible)
            for tramo in progresion:
                poligono = carpeta_progresion.newpolygon(
                    name=tramo["name"],
                    outerboundaryis=tramo["coords"]
                )
                poligono.description = f"{tramo['description']}\n\n{descripcion_prediccion}"
                poligono.style = estilo_poligono_riesgo(tramo.get("nivel_riesgo", "Moderado"))
        except Exception as exc:
            escribir_log(f"No fue posible generar la progresión por 3 horas: {exc}")

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