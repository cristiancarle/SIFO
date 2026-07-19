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

# OpenStreetMap
NETWORK_TYPE = "all"

# Google Earth
ICONO_INCENDIO = "http://maps.google.com/mapfiles/kml/shapes/firedept.png"