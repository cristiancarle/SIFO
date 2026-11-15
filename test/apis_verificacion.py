#!/usr/bin/env python3
"""Verificación en vivo de las APIs públicas usadas por sistema-incendios.

- Open-Meteo Forecast API (clima horario, sin API key)
- OpenTopoData SRTM 90m (elevación, sin API key)

Devuelve exit code 0 si ambas responden con datos válidos, 1 si alguna falla.
Uso: python3 test/apis_verificacion.py
"""

import json
import sys
import urllib.request
import urllib.error

LAT, LON = -31.60, -64.45  # Villa Carlos Paz, Córdoba

URL_METEO = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,"
    "wind_direction_10m,wind_gusts_10m,precipitation,cloud_cover"
    "&timezone=auto&forecast_days=2"
)
URL_TOPO = (
    "https://api.opentopodata.org/v1/srtm90m"
    f"?locations={LAT},{LON}|-31.59,-64.44"
)

PUNTOS_CARDINALES = [
    ("N", 337.5, 360), ("N", 0, 22.5),
    ("NE", 22.5, 67.5), ("E", 67.5, 112.5), ("SE", 112.5, 157.5),
    ("S", 157.5, 202.5), ("SO", 202.5, 247.5), ("O", 247.5, 292.5),
    ("NO", 292.5, 337.5),
]


def direccion_a_texto(grados):
    """Convierte grados (0=N, 90=E) a punto cardinal en español."""
    g = grados % 360
    for nombre, ini, fin in PUNTOS_CARDINALES:
        if ini <= g < fin:
            return nombre
    return "?"


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "sistema-incendios-test/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def verificar_meteo():
    print("== Open-Meteo Forecast API ==")
    print(f"URL: {URL_METEO}")
    data = http_get_json(URL_METEO)
    hourly = data["hourly"]
    unidades = data["hourly_units"]
    elev = data["elevation"]

    # Índice de la hora más cercana al presente: el array arranca a las 00:00
    # del primer día, así que buscamos la primera hora con datos no nulos.
    temps = hourly["temperature_2m"]
    idx = next((i for i, t in enumerate(temps) if t is not None), 0)

    hora = hourly["time"][idx]
    temp = temps[idx]
    rh = hourly["relative_humidity_2m"][idx]
    ws = hourly["wind_speed_10m"][idx]
    wd = hourly["wind_direction_10m"][idx]
    gust = hourly["wind_gusts_10m"][idx]
    pr = hourly["precipitation"][idx]
    cc = hourly["cloud_cover"][idx]

    print(f"  Zona horaria : {data['timezone']} (elevación modelo: {elev} m)")
    print(f"  Horas en respuesta: {len(hourly['time'])} (forecast_days=2)")
    print(f"  Hora de referencia : {hora}")
    print(f"  Temperatura   : {temp} {unidades['temperature_2m']}")
    print(f"  Humedad rel.  : {rh} {unidades['relative_humidity_2m']}")
    print(f"  Viento        : {ws} {unidades['wind_speed_10m']} "
          f"desde el {direccion_a_texto(wd)} ({wd}°), ráfagas {gust} {unidades['wind_gusts_10m']}")
    print(f"  Precipitación : {pr} {unidades['precipitation']}")
    print(f"  Nubosidad     : {cc} {unidades['cloud_cover']}")

    assert len(hourly["time"]) >= 48, "se esperaban >= 48 horas (2 días)"
    assert temp is not None and wd is not None, "campos horarios vacíos"
    print("  OK\n")
    return data


def verificar_topo():
    print("== OpenTopoData SRTM 90m ==")
    print(f"URL: {URL_TOPO}")
    data = http_get_json(URL_TOPO)
    assert data.get("status") == "OK", f"status != OK: {data}"
    res = data["results"]
    print(f"  Puntos consultados: {len(res)}")
    for r in res:
        loc = r["location"]
        print(f"  ({loc['lat']}, {loc['lng']}) -> {r['elevation']} m  "
              f"[dataset: {r['dataset']}]")
    assert all(r["elevation"] is not None for r in res), "alguna elevación vino None"
    print("  OK\n")
    return data


def main():
    resultados = {}
    errores = []
    for nombre, fn in (("open-meteo", verificar_meteo), ("opentopodata", verificar_topo)):
        try:
            resultados[nombre] = fn()
        except (urllib.error.URLError, AssertionError, KeyError, ValueError) as e:
            errores.append((nombre, e))
            print(f"  FALLO en {nombre}: {e}\n")

    if errores:
        print(f"RESULTADO: FALLO ({len(errores)} API(s) caída(s): "
              f"{', '.join(n for n, _ in errores)})")
        return 1
    print("RESULTADO: OK — ambas APIs responden con datos válidos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
