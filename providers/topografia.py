import math
import requests

from config import OPEN_ELEVATION_URL
from core.viento import grados_a_cardinal
from modulos.utilidades import escribir_log


def _grado_longitud(latitud):
    return 111_320 * math.cos(math.radians(latitud))


def obtener_topografia(latitud, longitud, distancia=2000):
    escribir_log("Obteniendo topografía desde Open-Elevation...")

    delta_lat = distancia / 111_320
    delta_lon = distancia / _grado_longitud(latitud)

    ubicaciones = [
        (latitud, longitud),
        (latitud + delta_lat, longitud),
        (latitud - delta_lat, longitud),
        (latitud, longitud + delta_lon),
        (latitud, longitud - delta_lon)
    ]

    try:
        parametros = {
            "locations": "|".join(
                f"{lat},{lon}" for lat, lon in ubicaciones
            )
        }

        respuesta = requests.get(OPEN_ELEVATION_URL, params=parametros, timeout=20)
        respuesta.raise_for_status()

        resultados = respuesta.json().get("results", [])
        elevaciones = [item.get("elevation") for item in resultados]

        if not elevaciones or elevaciones[0] is None:
            raise ValueError("No se obtuvo elevación válida.")

        elevacion_central = elevaciones[0]
        pendientes = []

        diferencial_x = 0.0
        diferencial_y = 0.0
        direcciones = [0, 180, 90, 270]  # Norte, Sur, Este, Oeste

        for idx, elev in enumerate(elevaciones[1:], start=1):
            if elev is None:
                continue

            delta = elev - elevacion_central
            pendientes.append(abs(delta) / distancia)

            if delta > 0:
                rad = math.radians(direcciones[idx - 1])
                diferencial_x += math.sin(rad) * delta
                diferencial_y += math.cos(rad) * delta

        maxima_pendiente = round(max(pendientes) * 100, 1) if pendientes else 0.0

        if maxima_pendiente < 5:
            tipo_terreno = "Plano"
        elif maxima_pendiente < 15:
            tipo_terreno = "Ladera suave"
        else:
            tipo_terreno = "Pendiente pronunciada"

        pendiente_direccion = None
        pendiente_direccion_cardinal = None

        if diferencial_x != 0 or diferencial_y != 0:
            pendiente_direccion = (math.degrees(math.atan2(diferencial_x, diferencial_y)) + 360) % 360
            pendiente_direccion_cardinal = grados_a_cardinal(pendiente_direccion)

        return {
            "elevacion": elevacion_central,
            "muestras": len(elevaciones),
            "distancia_muestra": distancia,
            "maxima_pendiente_pct": maxima_pendiente,
            "tipo_terreno": tipo_terreno,
            "pendiente_direccion": pendiente_direccion,
            "pendiente_direccion_cardinal": pendiente_direccion_cardinal
        }

    except Exception as exc:
        escribir_log(f"Error al obtener topografía: {exc}")
        return {
            "elevacion": None,
            "muestras": 0,
            "distancia_muestra": distancia,
            "maxima_pendiente_pct": None,
            "tipo_terreno": "Desconocido"
        }
