import requests

from core.viento import grados_a_cardinal, direccion_flecha, clasificar_viento

URL = "https://api.open-meteo.com/v1/forecast"


def obtener_meteorologia(latitud, longitud):
    parametros = {
        "latitude": latitud,
        "longitude": longitud,
        "current_weather": True,
        "hourly": "relativehumidity_2m,temperature_2m,windspeed_10m,winddirection_10m",
        "timezone": "auto"
    }

    respuesta = requests.get(URL, params=parametros, timeout=20)
    respuesta.raise_for_status()

    datos = respuesta.json()
    clima_actual = datos.get("current_weather", {})
    humedad = None

    if "hourly" in datos and "relativehumidity_2m" in datos["hourly"]:
        horas = datos["hourly"].get("time", [])
        humedades = datos["hourly"].get("relativehumidity_2m", [])
        if clima_actual.get("time") in horas:
            indice = horas.index(clima_actual["time"])
            if indice < len(humedades):
                humedad = humedades[indice]
        elif humedades:
            humedad = humedades[0]

    return {
        "temperatura": clima_actual.get("temperature"),
        "humedad": humedad,
        "viento": clima_actual.get("windspeed"),
        "direccion": clima_actual.get("winddirection"),
        "direccion_cardinal": grados_a_cardinal(clima_actual.get("winddirection")) if clima_actual.get("winddirection") is not None else None,
        "flecha_viento": direccion_flecha(clima_actual.get("winddirection")) if clima_actual.get("winddirection") is not None else None,
        "categoria_viento": clasificar_viento(clima_actual.get("windspeed")) if clima_actual.get("windspeed") is not None else None,
        "elevacion": datos.get("elevation"),
        "timezone": datos.get("timezone")
    }


def obtener_pronostico_24h(latitud, longitud):
    parametros = {
        "latitude": latitud,
        "longitude": longitud,
        "hourly": "temperature_2m,relativehumidity_2m,windspeed_10m,winddirection_10m",
        "timezone": "auto",
        "forecast_days": 1
    }

    respuesta = requests.get(URL, params=parametros, timeout=20)
    respuesta.raise_for_status()

    datos = respuesta.json()
    hourly = datos.get("hourly", {})

    horas = hourly.get("time", [])
    temperaturas = hourly.get("temperature_2m", [])
    humedades = hourly.get("relativehumidity_2m", [])
    vientos = hourly.get("windspeed_10m", [])
    direcciones = hourly.get("winddirection_10m", [])

    pronostico = []
    for i in range(0, min(24, len(horas)), 3):
        hora_str = horas[i] if i < len(horas) else ""
        temp = temperaturas[i] if i < len(temperaturas) else None
        humedad = humedades[i] if i < len(humedades) else None
        viento = vientos[i] if i < len(vientos) else None
        direccion = direcciones[i] if i < len(direcciones) else None

        pronostico.append({
            "hora": hora_str,
            "temperatura": temp,
            "humedad": humedad,
            "viento": viento,
            "direccion": direccion,
            "direccion_cardinal": grados_a_cardinal(direccion) if direccion is not None else None,
            "flecha_viento": direccion_flecha(direccion) if direccion is not None else None,
            "categoria_viento": clasificar_viento(viento) if viento is not None else None
        })

    return pronostico
