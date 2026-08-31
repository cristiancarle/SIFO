import os

from modulos.database import obtener_incendio_por_id
from modulos.cartografia import obtener_red_vial
from providers.openmeteo import obtener_meteorologia, obtener_pronostico_24h
from providers.topografia import obtener_topografia
from providers.combustible import obtener_combustible
from providers.copernicus import obtener_humedad_combustible_swid
from config import RADIO_ANALISIS
from core.proyecto import crear_expediente, guardar_json
from core.informe import generar_informe
from core.generar_informe_pdf import generar_informe_pdf
from core.riesgo import (
    validar_coordenadas,
    calcular_riesgo_ambiental,
    generar_recomendaciones,
    predecir_propagacion_incendio,
    analizar_ia_propagacion,
)


def analizar_incendio(id_incendio):
    incendio = obtener_incendio_por_id(id_incendio)
    if incendio is None:
        return None

    datos = {
        "id": incendio[0],
        "fecha": incendio[1],
        "hora": incendio[2],
        "nombre": incendio[3],
        "provincia": incendio[4],
        "localidad": incendio[5],
        "latitud": incendio[6],
        "longitud": incendio[7],
        "descripcion": incendio[8]
    }

    try:
        return _analizar_datos(datos)
    except ValueError as exc:
        print(f"No se pudo analizar el incendio: {exc}")
        return None


def analizar_coordenadas(nombre, provincia, localidad, latitud, longitud, descripcion):
    datos = {
        "id": 0,
        "fecha": "",
        "hora": "",
        "nombre": nombre,
        "provincia": provincia,
        "localidad": localidad,
        "latitud": latitud,
        "longitud": longitud,
        "descripcion": descripcion
    }

    try:
        return _analizar_datos(datos)
    except ValueError as exc:
        print(f"No se pudo analizar la ubicación: {exc}")
        return None


def _analizar_datos(datos):
    valido, error = validar_coordenadas(datos["latitud"], datos["longitud"])
    if not valido:
        raise ValueError(error)

    print("Obteniendo meteorología...")
    meteo = obtener_meteorologia(datos["latitud"], datos["longitud"])

    print("Obteniendo pronóstico a 24 horas...")
    pronostico_24h = obtener_pronostico_24h(datos["latitud"], datos["longitud"])

    print("Obteniendo topografía...")
    topografia = obtener_topografia(datos["latitud"], datos["longitud"])

    print("Obteniendo combustible...")
    combustible = obtener_combustible(datos["latitud"], datos["longitud"])

    print("Obteniendo humedad del combustible SWID...")
    humedad_combustible = obtener_humedad_combustible_swid(
        datos["latitud"],
        datos["longitud"],
        temperatura=meteo.get("temperatura"),
        humedad_relativa=meteo.get("humedad"),
        pendiente_pct=topografia.get("maxima_pendiente_pct"),
    )
    combustible["humedad_combustible"] = humedad_combustible["humedad_combustible"]
    combustible["fuente_humedad_combustible"] = humedad_combustible["fuente"]
    combustible["descripcion_humedad_combustible"] = humedad_combustible["descripcion"]

    print("Calculando pronóstico a 24 horas...")
    pronostico_texto = _generar_pronostico_24h(meteo, topografia, combustible)

    print("Descargando red vial...")
    caminos = obtener_red_vial(datos["latitud"], datos["longitud"], RADIO_ANALISIS)

    riesgo = calcular_riesgo_ambiental(meteo, topografia, combustible)
    recomendaciones = generar_recomendaciones(meteo, topografia, combustible, riesgo["nivel"])
    prediccion = predecir_propagacion_incendio(meteo, topografia, combustible, humedad_combustible["humedad_combustible"])
    analisis_ia = analizar_ia_propagacion(meteo, topografia, combustible, riesgo)

    analisis = {
        "incendio": datos,
        "meteorologia": meteo,
        "topografia": topografia,
        "combustible": combustible,
        "red_vial": caminos,
        "pronostico_24h": pronostico_texto,
        "pronostico_24h_horario": pronostico_24h,
        "riesgo": riesgo,
        "recomendaciones": recomendaciones,
        "prediccion": prediccion,
        "analisis_ia": analisis_ia,
        "ia": analisis_ia,
    }

    carpeta = crear_expediente(analisis)
    guardar_json(carpeta, "analisis.json", analisis)
    guardar_json(carpeta, "analisis_ia.json", analisis_ia)
    guardar_json(carpeta, "meteorologia.json", meteo)
    guardar_json(carpeta, "pronostico_24h.json", pronostico_24h)
    guardar_json(carpeta, "topografia.json", topografia)
    guardar_json(carpeta, "combustible.json", combustible)
    guardar_json(carpeta, "red_vial.json", caminos)
    guardar_json(carpeta, "prediccion.json", prediccion)

    informe = generar_informe(analisis)
    informe_path = os.path.join(carpeta, "informe.txt")
    with open(informe_path, "w", encoding="utf8") as archivo:
        archivo.write(informe)

    print("Generando informe PDF con pronóstico de 24 horas...")
    generar_informe_pdf(analisis, pronostico_24h)

    return analisis, carpeta


def _generar_pronostico_24h(meteo, topografia, combustible):
    viento = meteo.get("viento") or 0
    humedad = meteo.get("humedad")
    categoria_viento = meteo.get("categoria_viento", "")

    partes = []

    if viento >= 25 or categoria_viento in ("Alto", "Extremo"):
        partes.append(
            "El incendio puede intensificarse y desplazarse más rápido en la dirección del viento."
        )
    else:
        partes.append(
            "Las condiciones actuales no muestran vientos extremos; el avance puede ser más contenido, pero el fuego puede mantenerse activo."
        )

    if humedad is not None:
        if humedad < 30:
            partes.append(
                "La baja humedad favorece la propagación y el secado del combustible en las próximas 24 horas."
            )
        elif humedad < 50:
            partes.append(
                "La humedad moderada puede limitar parcialmente la velocidad de avance, pero el incendio aún puede reactivarse."
            )
        else:
            partes.append(
                "La humedad alta ayuda a frenar la propagación, aunque no elimina completamente el riesgo de actividad."
            )
    else:
        partes.append(
            "No hay datos de humedad disponibles para prever mejor el comportamiento del incendio."
        )

    humedad_combustible = combustible.get("humedad_combustible")
    if humedad_combustible is not None:
        if humedad_combustible < 20:
            partes.append(
                "La humedad del combustible está muy baja y favorece la ignición sostenida y la propagación rápida."
            )
        elif humedad_combustible < 30:
            partes.append(
                "La humedad del combustible es moderadamente baja; el fuego puede intensificarse si se mantienen los vientos y la pendiente."
            )

    if topografia.get("maxima_pendiente_pct") is not None and topografia["maxima_pendiente_pct"] > 15:
        partes.append(
            "El terreno pendiente puede canalizar el fuego y generar un avance más intenso en las laderas."
        )

    if combustible.get("tipo_combustible") in ("Bosque", "Matorral"):
        partes.append(
            "La vegetación densa o el matorral sugiere que el incendio puede ganar intensidad y saltar de un sector a otro."
        )
    elif combustible.get("tipo_combustible") in ("Pastizal", "Agrícola"):
        partes.append(
            "Los combustibles ligeros permiten un avance rápido del frente de fuego si se mantienen las condiciones secas."
        )
    else:
        partes.append(
            "El comportamiento puede variar según la evolución del tiempo y la disponibilidad de combustible local."
        )

    return " ".join(partes)
