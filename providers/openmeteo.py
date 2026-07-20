import requests


URL = "https://api.open-meteo.com/v1/forecast"


def obtener_meteorologia(latitud, longitud):

    parametros = {

        "latitude": latitud,

        "longitude": longitud,

        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m"
        ]
    }

    respuesta = requests.get(URL, params=parametros, timeout=20)

    respuesta.raise_for_status()

    datos = respuesta.json()["current"]

    return {

        "temperatura": datos["temperature_2m"],

        "humedad": datos["relative_humidity_2m"],

        "viento": datos["wind_speed_10m"],

        "direccion": datos["wind_direction_10m"],

        "rafagas": datos["wind_gusts_10m"]

    }