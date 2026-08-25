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

# Configuración GIS
RADIO_ANALISIS = 10000      # metros
PASOS_SIMULACION_MINUTOS = (30, 60, 120, 180, 360)
FACTOR_PROPAGACION_VIENTO = 1.8
DIRECCION_PROPAGACION_GRADOS = 35
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

# Perfil horario más realista para la simulación por tramos temporales
ESCENARIOS_HORARIOS = (
    {"viento_kmh": 18, "direccion_grados": 35, "humedad": 35, "pendiente": 12, "vegetacion": "matorral"},
    {"viento_kmh": 22, "direccion_grados": 42, "humedad": 30, "pendiente": 15, "vegetacion": "matorral"},
    {"viento_kmh": 28, "direccion_grados": 48, "humedad": 26, "pendiente": 18, "vegetacion": "bosque"},
    {"viento_kmh": 34, "direccion_grados": 55, "humedad": 22, "pendiente": 22, "vegetacion": "bosque"},
    {"viento_kmh": 39, "direccion_grados": 62, "humedad": 18, "pendiente": 26, "vegetacion": "pinar"}
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