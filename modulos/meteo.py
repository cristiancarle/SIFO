"""Meteorología: Open-Meteo (sin clave) y armado de 8 períodos de 3 hs."""
import json
import math
import os
import time
from datetime import datetime, timedelta, timezone

import requests

URL = "https://api.open-meteo.com/v1/forecast"
VARIABLES = ("temperature_2m,relative_humidity_2m,wind_speed_10m,"
             "wind_direction_10m,wind_gusts_10m,precipitation,cloud_cover")
CACHE_SEG = 600
DIR_CACHE = os.environ.get("SIFO_CACHE_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")


class ErrorAPI(Exception):
    """Fallo de una API externa con mensaje apto para el usuario."""


def _media(valores):
    v = [x for x in valores if x is not None]
    return sum(v) / len(v) if v else 0.0


class Meteorologia:
    def __init__(self):
        self.datos = None

    def get_forecast(self, lat, lon):
        """Devuelve el JSON de Open-Meteo (cacheado 10 min por coordenadas)."""
        os.makedirs(DIR_CACHE, exist_ok=True)
        ruta = os.path.join(DIR_CACHE, f"meteo_{lat:.3f}_{lon:.3f}.json")
        if os.path.exists(ruta) and time.time() - os.path.getmtime(ruta) < CACHE_SEG:
            try:
                with open(ruta, encoding="utf-8") as f:
                    self.datos = json.load(f)
                return self.datos
            except (OSError, ValueError):
                pass
        params = {"latitude": lat, "longitude": lon, "hourly": VARIABLES,
                  "timezone": "auto", "forecast_days": 2}
        try:
            r = requests.get(URL, params=params, timeout=20)
            r.raise_for_status()
            datos = r.json()
        except (requests.RequestException, ValueError) as e:
            raise ErrorAPI(f"No se pudo obtener el pronóstico de Open-Meteo: {e}")
        if "hourly" not in datos:
            raise ErrorAPI(f"Open-Meteo devolvió una respuesta inválida: {datos.get('reason', datos)}")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f)
        self.datos = datos
        return datos

    def hora_local_actual(self):
        """Hora local (naive, redondeada hacia abajo) del punto consultado."""
        off = (self.datos or {}).get("utc_offset_seconds", 0)
        ahora = datetime.now(timezone.utc) + timedelta(seconds=off)
        return ahora.replace(minute=0, second=0, microsecond=0, tzinfo=None)

    def periodos(self, t0=None):
        """8 períodos de 3 hs desde t0 (datetime local). Por defecto, la hora actual."""
        if self.datos is None:
            raise ErrorAPI("Primero hay que llamar a get_forecast().")
        h = self.datos["hourly"]
        tiempos = [datetime.fromisoformat(t) for t in h["time"]]
        t0 = t0 or self.hora_local_actual()
        # Si t0 queda fuera del rango, se usa el inicio del pronóstico
        if t0 < tiempos[0] or t0 > tiempos[-1] - timedelta(hours=1):
            t0 = tiempos[0]
        i0 = tiempos.index(t0) if t0 in tiempos else int((t0 - tiempos[0]).total_seconds() // 3600)

        resultado = []
        for k in range(8):
            ini = i0 + 3 * k
            idx = [i for i in range(ini, ini + 3) if i < len(tiempos)]
            if not idx:
                break
            sel = lambda var: [h[var][i] for i in idx]
            vel = sel("wind_speed_10m")
            dirs = sel("wind_direction_10m")
            horario = [{
                "hora_str": tiempos[i].strftime("%H:%M"),
                "temp": h["temperature_2m"][i], "rh": h["relative_humidity_2m"][i],
                "viento": h["wind_speed_10m"][i], "rafaga": h["wind_gusts_10m"][i],
            } for i in idx]
            fin = tiempos[idx[-1]] + timedelta(hours=1)
            resultado.append({
                "inicio_h": 3 * k, "fin_h": 3 * k + 3,
                "hora_inicio_str": tiempos[idx[0]].strftime("%H:%M"),
                "hora_fin_str": fin.strftime("%H:%M"),
                "fecha_inicio": tiempos[idx[0]].strftime("%d/%m/%Y"),
                "temp_med": _media(sel("temperature_2m")),
                "rh_med": _media(sel("relative_humidity_2m")),
                "viento_med_kmh": _media(vel),
                "viento_dir_med_deg": self._dir_media(vel, dirs),
                "rafaga_max_kmh": max([x for x in sel("wind_gusts_10m") if x is not None] or [0.0]),
                "precip_mm": sum(x for x in sel("precipitation") if x is not None),
                "nubes": _media(sel("cloud_cover")),
                "horario": horario,
            })
        return resultado

    @staticmethod
    def _dir_media(vel, dirs):
        """Dirección media vectorial (ponderada por velocidad) de donde VIENE el viento."""
        x = y = 0.0
        for v, d in zip(vel, dirs):
            if v is None or d is None:
                continue
            x += v * math.sin(math.radians(d))
            y += v * math.cos(math.radians(d))
        if abs(x) < 1e-9 and abs(y) < 1e-9:
            validos = [d for d in dirs if d is not None]
            return validos[0] if validos else 0.0
        return math.degrees(math.atan2(x, y)) % 360
