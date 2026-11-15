# ESPECIFICACIÓN — SIFO — Sistema Inteligente para Incendios Forestales

App web en Python (Flask, sin dependencias exoticas: flask + requests + numpy si está disponible, sino puro Python) que a partir de coordenadas (lat, lon) produce:
1. Meteorología completa para las próximas 24 hs
2. Análisis de topografía (pendiente, orientación, barrancos/quebradas)
3. Humedad del combustible fino muerto (1h)
4. Archivo KML descargable con: foco, línea AZUL de dirección del viento, carreras primarias (rojas) considerando topografía y meteorología, carreras secundarias (naranjas) buscando fondos de barrancos y quebradas con su comportamiento de fuego típico
5. Informe de trabajo para las próximas 24 hs en 8 períodos (t0=0hs, 3, 6, 9, 12, 15, 18, 21hs) con HORA DE ENTRADA y HORA DE SALIDA recomendadas para trabajar estrategias en cada período

## APIs SIN CLAVE (usar solo estas)
- Meteorología: https://api.open-meteo.com/v1/forecast (hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,cloud_cover, timezone=auto, forecast_days=2) — gratis sin key
- Topografía: https://api.opentopodata.org/v1/srtm90m?locations=lat1,lon1|lat2,lon2|... (max 100 puntos por llamada, gratis sin key) — respetar 1 req/seg

## MÓDULOS (cada uno un archivo Python en modulos/)

### modulos/meteo.py — class Meteorologia
- get_forecast(lat, lon) -> dict con hourly arrays
- periodos(t0) -> lista de 8 dicts: {inicio_h, fin_h, hora_inicio_str, hora_fin_str, temp_med, rh_med, viento_med_kmh, viento_dir_med_deg, rafaga_max_kmh, precip_mm, nubes}
- viento por períodos con dirección media vectorial (cuidado con el wrap 350→10)

### modulos/topografia.py — class Topografia
- get_dem(lat, lon, radio_m=3000, lado=25) -> matriz NxN de alturas (llamadas por lotes de 100 puntos a opentopodata, con sleep de 1.1s entre llamadas y caché en disco del resultado)
- calcular() -> dict con: pendiente_max, pendiente_prom, aspecto_grados (orientación de la cuesta dominante), celdas_pendiente_grados, red_de_cauces (lista de polilíneas latlon) detectada con flujo D8 simple sobre el DEM (celdas cóncavas = fondos de barranco/quebrada), extensión de quebradas en metros
- identificar_barrancos() -> lista de polilíneas [(lat,lon),...] de fondos de quebrada ordenadas aguas abajo

### modulos/combustible.py — class Combustible
- humedad_muerta_1h(temp_c, rh_pct) -> % con la relación tipo BEHAVE/Simard: fm = 148.5 * (1 - exp(-0.0445 * rh_pct)) ajustada por temperatura (si T>30 restar 1 punto por cada 5°C sobre 30; si T<10 sumar 1 por cada 5 bajo 10). Documentar la aproximación en comentarios.
- clasificar_riesgo(fm_pct) -> "SECO (<10%) - EXTREMO" | "BAJO (<20%)" | "MODERADO (<30%)" | "ALTO (>30%) - COMBUSTIBLE HÚMEDO"

### modulos/comportamiento.py — class ComportamientoFuego
- dado el viento (dirección, kmh) y la topografía (aspecto, pendientes) calcular por período:
  - direccion_carrera_primaria_deg = dirección hacia la que corre el fuego principal: combinación vectorial de (a) empuje del viento y (b) subida cuesta arriba en la ladera cuyo aspecto (orientación) coincide con la dirección del viento — el fuego corre MÁS RÁPIDO cuesta arriba; en laderas opuestas al viento la influencia es menor
  - lineas_carrera_primaria: polilíneas desde el foco: principal según dirección de máximo potencial + 2 laterales (flancos) si hay laderas opuestas
  - lineas_carrera_secundaria: polilíneas a lo largo de los fondos de quebrada (la quebrada actúa como chimenea: el fuego corre por el fondo con ambos flancos subiendo, velocidad aumentada por encauzamiento del viento — factor 1.3x sobre la base)
  - velocidad_estimada_kmh (referencia BEHAVE simplificada: base 0.5 km/h en pastizal seco x factor viento (viento/10 limitado a 4) x factor pendiente (1 + pendiente%/10 cuando el fuego sube la ladera — corre cuesta arriba; factor 0.7 si corre cuesta abajo))
- reglas de comportamiento en quebradas (documentar en el informe): fuego corre aguas abajo del cauce, se acelera en V cerradas, chimeneas de calor, riesgo extremo para brigadas dentro de la quebrada

### modulos/kml_gen.py — generar_kml(lat, lon, resultados) -> string KML
- Placemark "INICIO DEL FOCO" (icono fuego)
- LineString AZUL: dirección del viento (2km de largo) con etiqueta del período
- LineStrings ROJAS: carreras primarias hacia las laderas a favor del viento y hacia arriba (con extensión proporcional a la velocidad estimada x duración del período, máx 2km)
- LineStrings NARANJAS: carreras secundarias sobre los fondos de barranco (del módulo topografía), con clamped to ground
- Carpeta por período (0hs, 3hs, ... 21hs) o un solo archivo con todas las horas como TimeSpan

### modulos/informe.py — generar_informe(resultados) -> HTML (string)
- Encabezado: coordenadas, fecha/hora de generación (t0), fuente de datos
- 8 bloques de período con formato de ORDEN DE TRABAJO:
  - VENTANA: hora de entrada y hora de salida (ej: 06:00 - 09:00)
  - Meteorología del período
  - Humedad del combustible y riesgo
  - Carreras primarias esperadas (dirección, extensión, velocidad)
  - Carreras secundarias en quebradas (con advertencia de seguridad)
  - RECOMENDACIÓN OPERATIVA: hora de entrada (cuando las condiciones permiten trabajar: rafagas <40km/h, fm no extrema, fuera de quebradas si viento fuerte) y hora de salida (cuando las condiciones se agravan o al cierre de la ventana)
  - Lógica: entrar temprano (ventanas de baja intensidad: madrugada/amanecer con fm alta y viento bajo), salir antes del pico de viento/calor (típicamente 12-17hs), no operar dentro de quebradas durante períodos de viento fuerte o fm extrema

### app.py — servidor Flask en 0.0.0.0:5000
- GET / -> formulario (lat, lon con valores por defecto de ejemplo: -31.60, -64.45 Villa Carlos Paz) + static/index.html
- POST /analizar -> corre todos los módulos, guarda informe HTML en static/salida/, KML en static/salida/, redirige a página de resultados con links al informe y al KML
- GET /salida/<archivo> para descargar

### static/index.html
Formulario simple bonito con título "SIFO — Sistema Inteligente para Incendios Forestales", campos lat/lon, botón ANALIZAR, y el resultado con links.

## IMPORTANTE
- Cachear la respuesta de Open-Meteo 10 min y el DEM para las mismas coordenadas (archivo .cache en la carpeta)
- Errores de API deben producir mensajes claros en el informe
- Todo en español (textos de la UI y del informe)
- Probabilidad de que numpy NO esté instalado: escribir sin numpy o con fallback
- Al terminar, verificar con: python3 -c "import app" y una ejecución de prueba real de todos los módulos con lat=-31.60, lon=-64.45 corriendo la lógica (sin levantar el servidor Flask, solo llamando las funciones) e imprimir un resumen del informe generado. NO levantar el servidor.
