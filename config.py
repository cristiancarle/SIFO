# ==========================================================
# SIFO - Configuración General
# ==========================================================

import os

# Directorios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATOS_DIR = os.path.join(BASE_DIR, "datos")
KML_DIR = os.path.join(BASE_DIR, "kml")
LOG_DIR = os.path.join(BASE_DIR, "logs")
INFORMES_DIR = os.path.join(BASE_DIR, "informes")

# Base de datos
DB = os.path.join(DATOS_DIR, "incendios.db")

# Fuente meteorológica principal. SpotWX/Windy usan el modelo GFS como base para
# el campo de viento/temperatura, por lo que la simulación del incendio debe
# mantener esa referencia para no basarse en valores arbitrarios.
FUENTE_METEOROLOGICA = "SpotWX"
MODELO_METEOROLOGICO = "GFS"

# Configuración GIS
RADIO_ANALISIS = 10000      # metros
PASOS_SIMULACION_MINUTOS = (30, 60, 120, 180, 360)
FACTOR_PROPAGACION_VIENTO = 1.8
# En meteorología, la dirección del viento se reporta como origen del viento:
# si viene del norte (0°/360°), la propagación del fuego va hacia el sur (180°).
# Por eso la propagación es siempre la dirección del viento + 180°.
DIRECCION_PROPAGACION_GRADOS = 0
VELOCIDAD_VIENTO_KMH = 18
HUMEDAD_RELATIVA = 35
PENDIENTE_MEDIA = 12
TIPO_VEGETACION = "matorral"

FACTOR_VEGETACION = {
    "matorral": 1.25,
    "bosque": 1.45,
    "pastizal": 1.10,
    "pinar": 1.60,
    "maleza": 1.30,
    "humedal": 0.90,
    "roca": 0.75
}

CARGA_COMBUSTIBLE = {
    "matorral": 1.35,
    "bosque": 1.55,
    "pastizal": 1.10,
    "pinar": 1.70,
    "maleza": 1.20,
    "humedal": 0.95,
    "roca": 0.60
}

# Perfil horario alineado a la meteorología operativa que muestran SpotWX/Windy,
# donde el viento de base del modelo GFS se intensifica en el tramo diurno y
# se atenúa durante la madrugada. Los valores no son arbitrarios: se usan como
# referencia para la simulación del comportamiento del fuego.
ESCENARIOS_HORARIOS = (
    {"viento_kmh": 12, "direccion_grados": 250, "humedad": 63, "pendiente": 12, "vegetacion": "matorral"},
    {"viento_kmh": 16, "direccion_grados": 260, "humedad": 58, "pendiente": 15, "vegetacion": "matorral"},
    {"viento_kmh": 21, "direccion_grados": 270, "humedad": 49, "pendiente": 18, "vegetacion": "bosque"},
    {"viento_kmh": 29, "direccion_grados": 285, "humedad": 38, "pendiente": 22, "vegetacion": "bosque"},
    {"viento_kmh": 24, "direccion_grados": 295, "humedad": 44, "pendiente": 26, "vegetacion": "pinar"}
)

ESCALAS_HEATMAP = (
    ("muy_bajo", 0.12),
    ("bajo", 0.30),
    ("medio", 0.55),
    ("alto", 0.80),
    ("critico", 1.00)
)

# OpenStreetMap
NETWORK_TYPE = "all"

# Google Earth
ICONO_INCENDIO = "http://maps.google.com/mapfiles/kml/shapes/firedept.png"