import requests

from config import OVERPASS_API_URL, OVERPASS_RADIUS, USER_AGENT
from modulos.utilidades import escribir_log

TIPOS_COMBUSTIBLE = {
    "wood": "Bosque",
    "forest": "Bosque",
    "scrub": "Matorral",
    "grassland": "Pastizal",
    "heath": "Matorral",
    "meadow": "Pastizal",
    "orchard": "Agrícola",
    "vineyard": "Agrícola",
    "farmland": "Agrícola",
    "farm": "Agrícola",
    "grass": "Pastizal",
    "bushes": "Matorral"
}


def _clasificar_etiquetas(tags):
    natural = tags.get("natural", "").lower()
    landuse = tags.get("landuse", "").lower()

    for valor in (natural, landuse):
        if valor in TIPOS_COMBUSTIBLE:
            return TIPOS_COMBUSTIBLE[valor], valor

    if natural:
        return "Vegetación", natural
    if landuse:
        return "Vegetación", landuse

    return "Desconocido", None


def _construir_consulta(latitud, longitud):
    return (
        f"[out:json][timeout:25];"
        f"(way(around:{OVERPASS_RADIUS},{latitud},{longitud})[natural];"
        f"way(around:{OVERPASS_RADIUS},{latitud},{longitud})[landuse];"
        f"relation(around:{OVERPASS_RADIUS},{latitud},{longitud})[natural];"
        f"relation(around:{OVERPASS_RADIUS},{latitud},{longitud})[landuse];"
        f");out tags center;"
    )


def obtener_combustible(latitud, longitud):
    escribir_log("Consultando combustible en OpenStreetMap...")

    consulta = _construir_consulta(latitud, longitud)
    headers = {"User-Agent": USER_AGENT}

    try:
        respuesta = requests.get(OVERPASS_API_URL, params={"data": consulta}, headers=headers, timeout=60)
        respuesta.raise_for_status()

        datos = respuesta.json().get("elements", [])
        clasificaciones = {}
        detalles = []

        for elemento in datos:
            tags = elemento.get("tags", {})
            tipo, original = _clasificar_etiquetas(tags)
            clasificaciones[tipo] = clasificaciones.get(tipo, 0) + 1
            detalles.append({
                "tipo": tipo,
                "original": original,
                "tags": tags
            })

        if not clasificaciones:
            return {
                "tipo_combustible": "Desconocido",
                "descripcion": "No se encontró información de cobertura vegetal en OpenStreetMap.",
                "cantidad_elementos": 0,
                "detalles": []
            }

        dominante = max(clasificaciones, key=clasificaciones.get)
        descripcion = (
            f"Combustible dominante: {dominante}. "
            f"Se encontraron {sum(clasificaciones.values())} elementos de "
            f"vegetación y uso de suelo alrededor del punto."
        )

        return {
            "tipo_combustible": dominante,
            "descripcion": descripcion,
            "cantidad_elementos": sum(clasificaciones.values()),
            "clasificaciones": clasificaciones,
            "detalles": detalles[:10]
        }

    except Exception as exc:
        escribir_log(f"Error al obtener combustible: {exc}")
        return {
            "tipo_combustible": "Desconocido",
            "descripcion": "No fue posible consultar la cobertura vegetal en este momento.",
            "cantidad_elementos": 0,
            "detalles": []
        }
