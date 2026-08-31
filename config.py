# ==========================================================
# SIFO - Configuración General
# ==========================================================

import os

# Directorios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATOS_DIR = os.path.join(BASE_DIR, "datos")
KML_DIR = os.path.join(BASE_DIR, "kml")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Base de datos
DB = os.path.join(DATOS_DIR, "incendios.db")

# Configuración GIS
RADIO_ANALISIS = 10000      # metros
OVERPASS_RADIUS = 5000      # metros para análisis de combustible

# OpenStreetMap
NETWORK_TYPE = "all"
OVERPASS_API_URL = "https://overpass.kumi.systems/api/interpreter"
USER_AGENT = "SIFO/1.0 (+https://github.com/cristiancarle/SIFO)"

# Open-Elevation
OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"

# Google Earth
ICONO_INCENDIO = "http://maps.google.com/mapfiles/kml/shapes/firedept.png"