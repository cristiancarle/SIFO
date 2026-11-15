# SIFO — Sistema Inteligente para Incendios Forestales

Aplicación web en Python (Flask) que, a partir de unas coordenadas (latitud / longitud), genera un análisis completo para las próximas **24 horas** destinado a la planificación de trabajos de combate de incendios forestales:

1. **Meteorología completa** (temperatura, humedad relativa, viento y ráfagas, precipitación y nubosidad) para las próximas 24 hs.
2. **Análisis topográfico** de la zona (pendientes, orientación de laderas, detección de barrancos y quebradas mediante flujo D8 sobre un modelo de elevación).
3. **Humedad del combustible fino muerto (1 hora)** estimada a partir de temperatura y humedad relativa, con clasificación de riesgo.
4. **Archivo KML descargable** (Google Earth) con:
   - el foco inicial,
   - línea **azul** con la dirección del viento,
   - carreras **primarias (rojas)** del fuego considerando viento + pendiente,
   - carreras **secundarias (naranjas)** por el fondo de quebradas y barrancos (efecto chimenea),
   organizado en carpetas por período (0, 3, 6, 9, 12, 15, 18 y 21 hs).
5. **Informe operativo de 24 hs en 8 períodos** (3 hs cada uno), en formato de *orden de trabajo*, con **HORA DE ENTRADA** y **HORA DE SALIDA** recomendadas para cada ventana.

La documentación operativa (cómo interpretar el informe desde el punto de vista de brigada) está en **MANUAL_OPERATIVO.md**.

## Requisitos

- Python 3.8 o superior
- `flask`
- `requests`
- `numpy` (**opcional** — el sistema funciona sin él, con implementación en Python puro)

```bash
pip install flask requests
# opcional:
pip install numpy
```

No se requiere ninguna otra dependencia.

## Instalación

```bash
git clone <repo> sistema-incendios
cd sistema-incendios
pip install -r requirements.txt   # o instalar a mano flask y requests
python3 -c "import app"           # verificación rápida
```

## Uso

```bash
python3 app.py
```

El servidor queda escuchando en `http://0.0.0.0:5000`. Abrir en el navegador y cargar coordenadas en el formulario.

### Ejemplo con coordenadas reales

Valores por defecto del formulario: **Villa Carlos Paz, Córdoba** → lat `-31.60`, lon `-64.45`.

Otros ejemplos útiles para probar:

| Zona | Latitud | Longitud |
|---|---|---|
| Villa Carlos Paz (Córdoba) | -31.60 | -64.45 |
| Cerro Uritorco (Córdoba) | -30.86 | -64.53 |
| El Bolsón (Río Negro) | -41.97 | -71.53 |
| Calamuchita, Santa Rosa (Córdoba) | -32.28 | -64.45 |

Flujo de uso:

1. Ingresar latitud y longitud del foco.
2. Presionar **ANALIZAR**.
3. Descargar de la página de resultados:
   - `informe_XXXX.html` — el informe operativo de 24 hs (8 períodos);
   - `carreras_XXXX.kml` — para abrir en Google Earth y ver foco, viento y carreras sobre el terreno.

## Estructura del proyecto

```
sistema-incendios/
├── app.py               # Servidor Flask (rutas / , /analizar, /salida/<archivo>)
├── ESPECIFICACION.md    # Especificación técnica completa
├── README.md            # Este archivo
├── MANUAL_OPERATIVO.md  # Manual para personal de brigadas
├── static/
│   ├── index.html       # Formulario de coordenadas
│   └── salida/          # Informes HTML y KML generados
└── modulos/
    ├── meteo.py         # Meteorología (Open-Meteo), armado de 8 períodos
    ├── topografia.py    # DEM, pendientes, aspecto, red de cauces (D8)
    ├── combustible.py   # Humedad del combustible fino muerto 1h (relación tipo Simard/BEHAVE)
    ├── comportamiento.py# Dirección y velocidad de carreras primarias y secundarias
    ├── kml_gen.py       # Generación del KML (foco, viento, carreras)
    └── informe.py       # Informe HTML por períodos con recomendaciones operativas
```

## Fuentes de datos (APIs sin clave)

El sistema usa únicamente APIs gratuitas que **no requieren clave de acceso**:

### Meteorología — Open-Meteo

- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Parámetros usados: `temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`, `wind_direction_10m`, `wind_gusts_10m`, `precipitation`, `cloud_cover`, `timezone=auto`, `forecast_days=2`.
- Sin clave, sin registro. La respuesta se cachea 10 minutos.

### Topografía — OpenTopodata

- Endpoint: `https://api.opentopodata.org/v1/srtm90m?locations=lat1,lon1|lat2,lon2|...`
- Modelo SRTM 90 m. Máximo 100 puntos por llamada; el sistema respeta el límite de 1 solicitud por segundo y cachea el DEM en disco para las mismas coordenadas (archivo `.cache`).

> Ambas APIs requieren conexión a internet. Si falla la consulta, el sistema produce un mensaje de error claro en el informe en lugar de datos incorrectos.

## Notas técnicas

- El promedio vectorial de la dirección del viento maneja el wrap 350°→10°.
- La humedad del combustible se estima con la relación tipo BEHAVE/Simard `fm = 148.5 * (1 - exp(-0.0445 * RH))` ajustada por temperatura (ver comentarios en `modulos/combustible.py`).
- Las carreras secundarias por quebrada aplican un factor de encauzamiento de viento de **1.3x** sobre la velocidad base (la quebrada actúa como chimenea de calor).
- La velocidad de propagación es una referencia BEHAVE simplificada: base 0.5 km/h en pastizal seco × factor viento × factor pendiente. Es una **estimación de planificación**, no un modelo de predicción certificado.
