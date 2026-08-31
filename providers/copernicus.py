import os

import requests

COPERNICUS_SWID_URL = os.getenv("COPERNICUS_SWID_URL")


def _extraer_valor_swid(payload):
    if isinstance(payload, dict):
        for clave in (
            "humedad_combustible",
            "fuel_moisture",
            "fuel_moisture_content",
            "swid",
            "soil_water_index",
            "moisture",
            "value",
        ):
            valor = payload.get(clave)
            if valor is not None:
                try:
                    return float(valor)
                except (TypeError, ValueError):
                    continue

        if "data" in payload and isinstance(payload["data"], dict):
            return _extraer_valor_swid(payload["data"])

        if "features" in payload and isinstance(payload["features"], list):
            for feature in payload["features"]:
                valor = _extraer_valor_swid(feature)
                if valor is not None:
                    return valor

    if isinstance(payload, list):
        for item in payload:
            valor = _extraer_valor_swid(item)
            if valor is not None:
                return valor

    return None


def _estimacion_swid(latitud, longitud, temperatura=None, humedad_relativa=None, pendiente_pct=None):
    temperatura = float(temperatura or 25)
    humedad_relativa = float(humedad_relativa or 40)
    pendiente_pct = float(pendiente_pct or 0)

    # Estimación conservadora del contenido de humedad del combustible usando un proxy del SWID.
    # La escala se mantiene en %, similar a lo que se observa en productos operativos de humedad.
    swid = 28 + (humedad_relativa * 0.55) + max(0, 35 - temperatura) * 0.9 - (pendiente_pct * 0.2)
    swid = min(max(swid, 5), 80)
    return round(swid, 1)


def obtener_humedad_combustible_swid(latitud, longitud, temperatura=None, humedad_relativa=None, pendiente_pct=None):
    """Obtiene la humedad del combustible desde Copernicus SWID si es posible,
    y si no, usa un estimador local basado en temperatura, humedad relativa y pendiente."""
    fuente = os.getenv("COPERNICUS_SWID_URL", COPERNICUS_SWID_URL)

    if fuente:
        try:
            respuesta = requests.get(
                fuente,
                params={"lat": latitud, "lon": longitud},
                timeout=20,
            )
            respuesta.raise_for_status()
            payload = respuesta.json()
            valor = _extraer_valor_swid(payload)
            if valor is not None:
                valor = min(max(float(valor), 2), 80)
                return {
                    "humedad_combustible": round(valor, 1),
                    "fuente": "Copernicus SWID",
                    "descripcion": "Humedad del combustible estimada a partir del producto SWID de Copernicus.",
                }
        except Exception:
            pass

    swid = _estimacion_swid(latitud, longitud, temperatura, humedad_relativa, pendiente_pct)
    return {
        "humedad_combustible": swid,
        "fuente": "Estimación local SWID",
        "descripcion": "No fue posible consultar directamente Copernicus SWID; se aplicó una estimación local alineada a la humedad del combustible.",
    }
