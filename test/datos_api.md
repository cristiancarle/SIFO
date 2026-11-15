# Esquema real de las APIs de datos (verificado en vivo)

Verificado el **2026-11-05** contra los endpoints reales, coordenadas de prueba
`lat=-31.60, lon=-64.45` (Villa Carlos Paz, Córdoba). Muestras completas guardadas en
`test/muestra_meteo.json` y `test/muestra_topo.json`. Ambas APIs son públicas y no
requieren API key.

## 1. Open-Meteo Forecast API — clima horario

- **URL usada**: `https://api.open-meteo.com/v1/forecast?latitude=-31.60&longitude=-64.45&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,cloud_cover&timezone=auto&forecast_days=2`
- **HTTP 200**, JSON sin envoltorio de error.

### Campos de primer nivel

| Campo | Tipo | Ejemplo real |
|---|---|---|
| `latitude` | float | -31.6 |
| `longitude` | float | -64.5 |
| `generationtime_ms` | float | 0.06 |
| `utc_offset_seconds` | int | -10800 |
| `timezone` | string | `"America/Argentina/Cordoba"` |
| `timezone_abbreviation` | string | `-03` |
| `elevation` | float | 621.0 (m — elevación del modelo en el punto) |
| `hourly_units` | objeto string→string | ver abajo |
| `hourly` | objeto con arrays paralelos | ver abajo |

### `hourly_units` (unidades por variable)

| Variable | Unidad |
|---|---|
| `time` | `iso8601` (sin zona: `"2026-11-05T00:00"`) |
| `temperature_2m` | `°C` |
| `relative_humidity_2m` | `%` |
| `wind_speed_10m` | `km/h` |
| `wind_direction_10m` | `°` |
| `wind_gusts_10m` | `km/h` |
| `precipitation` | `mm` |
| `cloud_cover` | `%` |

### `hourly` (arrays paralelos, uno por variable)

Con `forecast_days=2` devuelve **48 entradas** por variable, empezando a las 00:00
local del primer día. Valores reales de la muestra:

- `time`: `["2026-11-05T00:00", "2026-11-05T01:00", ...]`
- `temperature_2m`: `[14.8, 14.1, 13.2, ...]`
- `relative_humidity_2m`: `[68, 71, ...]` (entero)
- `wind_speed_10m`: `[0.6, 1.8, ...]` — dirección meteorológica: **de dónde viene** el viento, 0=N, 90=E
- `wind_direction_10m`: `[326, 336, ...]`
- `wind_gusts_10m`: `[2.5, 3.6, ...]`
- `precipitation`: `[0.0, 0.0, ...]`
- `cloud_cover`: `[2, 1, ...]` (entero 0–100)

**Notas**: los valores pueden ser `null` en horas aún sin dato; parsear con tolerancia.
La hora "actual" no viene marcada: el array arranca a las 00:00 del día 1, por lo que
el índice presente es `datetime.now() - fecha_inicio` en horas.

## 2. OpenTopoData — elevación SRTM 90m

- **URL usada**: `https://api.opentopodata.org/v1/srtm90m?locations=-31.6,-64.45|-31.59,-64.44`
- Formato: `locations` acepta varias separadas por `|` como `lat,lng`. Máx. 100
  ubicaciones por request (límite documentado del servicio público).
- **HTTP 200**.

### Esquema de respuesta real

```json
{
  "results": [
    {"dataset": "srtm90m", "elevation": 625.0, "location": {"lat": -31.6, "lng": -64.45}},
    {"dataset": "srtm90m", "elevation": 642.0, "location": {"lat": -31.59, "lng": -64.44}}
  ],
  "status": "OK"
}
```

| Campo | Tipo | Nota |
|---|---|---|
| `status` | string | `"OK"` en éxito (el resto de la respuesta hay que validarla aparte) |
| `results` | array | un elemento por ubicación, en el mismo orden del request |
| `results[].dataset` | string | nombre del dataset (`"srtm90m"`) |
| `results[].elevation` | float | metros sobre el nivel del mar; `null` si no hay dato |
| `results[].location.lat` / `.lng` | float | eco del punto consultado (nota: la clave es **`lng`**, no `lon`) |

Respuesta de error documentada: HTTP 400 con `{"error": "...", "status": "..."}`.

## Alternativas si algo falla

- **Topografía**: `https://api.opentopodata.org/v1/aster30m` (misma API, dataset
  SRTM30m también existe); fallback externo: Open-Elevation
  (`https://api.open-elevation.com/api/v1/lookup?locations=-31.6,-64.45|-31.59,-64.44`,
  esquema distinto: `{"results": [{"latitude", "longitude", "elevation"}]}`).
- **Clima**: Open-Meteo expone también `/v1/ensemble` y variables adicionales
  (`soil_temperature_0_to_7cm`, etc.) con el mismo esquema de respuesta.

## Script de verificación

`test/apis_verificacion.py` consulta ambas URLs en vivo, imprime un resumen
(temperatura actual, viento en texto N/NE/E..., ráfagas, alturas SRTM) y sale con
`0` solo si ambas responden con datos válidos (`1` si alguna falla).
