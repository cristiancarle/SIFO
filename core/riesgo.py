import json
import math
import os
from urllib import error, request

from core.viento import grados_a_cardinal


def validar_coordenadas(latitud, longitud):
    """Valida que las coordenadas estén dentro del rango geográfico permitido."""
    try:
        latitud = float(latitud)
        longitud = float(longitud)
    except (TypeError, ValueError):
        return False, "Las coordenadas deben ser valores numéricos válidos."

    if not -90 <= latitud <= 90:
        return False, "La latitud debe estar entre -90 y 90 grados."

    if not -180 <= longitud <= 180:
        return False, "La longitud debe estar entre -180 y 180 grados."

    return True, None


def _cardinal_a_grados(cardinal):
    if cardinal is None:
        return None

    mapa = {
        "Norte": 0,
        "Noreste": 45,
        "Este": 90,
        "Sudeste": 135,
        "Sur": 180,
        "Sudoeste": 225,
        "Oeste": 270,
        "Noroeste": 315,
    }

    clave = str(cardinal).strip().lower()
    for nombre, valor in mapa.items():
        if nombre.lower() == clave:
            return valor
    return None


def _normalizar_direccion(valor):
    if valor is None:
        return None

    try:
        numero = float(valor)
        return numero % 360
    except (TypeError, ValueError):
        return _cardinal_a_grados(valor)


def _promediar_angulos(grado_a, grado_b, peso_a=1.0, peso_b=1.0):
    if grado_a is None:
        return grado_b
    if grado_b is None:
        return grado_a

    rad_a = math.radians(grado_a)
    rad_b = math.radians(grado_b)
    x = (math.sin(rad_a) * peso_a) + (math.sin(rad_b) * peso_b)
    y = (math.cos(rad_a) * peso_a) + (math.cos(rad_b) * peso_b)
    angulo = math.degrees(math.atan2(x, y))
    return (angulo + 360) % 360


def _obtener_direccion_de_propagacion(meteo):
    if not isinstance(meteo, dict):
        return None

    direccion = _normalizar_direccion(meteo.get("direccion"))
    if direccion is not None:
        return (direccion + 180) % 360

    cardinal = meteo.get("direccion_cardinal")
    if cardinal is not None:
        direccion = _cardinal_a_grados(cardinal)
        if direccion is not None:
            return (direccion + 180) % 360

    return None


def _obtener_direccion_pendiente(topografia):
    if not isinstance(topografia, dict):
        return None

    direccion = _normalizar_direccion(topografia.get("pendiente_direccion"))
    if direccion is not None:
        return direccion

    cardinal = topografia.get("pendiente_direccion_cardinal")
    if cardinal is not None:
        return _cardinal_a_grados(cardinal)

    return None


def _llm_analisis_ia(prompt):
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY")
    if not api_key:
        return None

    base_url = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    endpoint = f"{base_url.rstrip('/')}/chat/completions"

    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {
                "role": "system",
                "content": "Sos un analista experto de incendios forestales. Respondé en español con un resumen breve, claro y operativo.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=25) as respuesta:
            contenido = json.loads(respuesta.read().decode("utf-8"))
        texto = contenido.get("choices", [{}])[0].get("message", {}).get("content")
        return texto.strip() if isinstance(texto, str) and texto.strip() else None
    except (error.HTTPError, error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def analizar_ia_propagacion(meteo, topografia, combustible, riesgo=None):
    """Combina viento y pendiente para producir un análisis de dirección de propagación y riesgo operacional."""
    meteo = meteo or {}
    topografia = topografia or {}
    combustible = combustible or {}

    viento = float(meteo.get("viento") or 0)
    humedad = float(meteo.get("humedad") or 0)
    pendiente = float(topografia.get("maxima_pendiente_pct") or 0)
    humedad_combustible = _resolver_humedad_combustible(meteo, combustible)
    if humedad_combustible is None:
        humedad_combustible = max(5.0, humedad * 0.6)

    direccion_viento = _obtener_direccion_de_propagacion(meteo)
    direccion_pendiente = _obtener_direccion_pendiente(topografia)

    if direccion_viento is None and direccion_pendiente is None:
        direccion_final = 0
    elif direccion_viento is None:
        direccion_final = direccion_pendiente
    elif direccion_pendiente is None:
        direccion_final = direccion_viento
    else:
        peso_viento = 0.65 + min(viento / 40.0, 1.0) * 0.35
        peso_pendiente = 0.35 + min(pendiente / 35.0, 1.0) * 0.5
        direccion_final = _promediar_angulos(
            direccion_viento,
            direccion_pendiente,
            peso_a=peso_viento,
            peso_b=peso_pendiente,
        )

    direccion_cardinal = None
    if direccion_final is not None:
        direccion_cardinal = grados_a_cardinal(direccion_final)

    aceleracion = 1.0
    aceleracion += max(0.0, (viento - 10) / 25.0) * 1.2
    aceleracion += min(1.0, pendiente / 35.0) * 0.8
    aceleracion += max(0.0, (45 - humedad) / 30.0) * 0.6
    aceleracion += max(0.0, (30 - humedad_combustible) / 18.0) * 0.9
    if combustible.get("tipo_combustible") in ("Bosque", "Matorral"):
        aceleracion += 0.7
    elif combustible.get("tipo_combustible") in ("Pastizal", "Agrícola"):
        aceleracion += 0.4

    aceleracion = round(min(aceleracion, 5.8), 2)
    if aceleracion >= 4.2:
        nivel_aceeleracion = "muy alta"
    elif aceleracion >= 3.0:
        nivel_aceeleracion = "alta"
    elif aceleracion >= 2.0:
        nivel_aceeleracion = "moderada"
    else:
        nivel_aceeleracion = "baja"

    if direccion_viento is not None and direccion_pendiente is not None:
        descripcion = (
            f"El análisis combina la dirección del viento ({int(round(direccion_viento))}°) con la pendiente "
            f"({int(round(direccion_pendiente))}°). La propagación probable se orientará hacia el sector "
            f"{direccion_cardinal} con una aceleración {nivel_aceeleracion}. "
            "Si el viento se mantiene y el combustible sigue seco, el avance puede intensificarse en ese eje."
        )
    elif direccion_viento is not None:
        descripcion = (
            f"La dirección dominante del fuego se deriva principalmente del viento, que empuja hacia el sector "
            f"{direccion_cardinal}. La pendiente todavía puede reforzar o desviar el frente en función del terreno."
        )
    elif direccion_pendiente is not None:
        descripcion = (
            f"El comportamiento principal responde a la pendiente que orienta la propagación hacia {direccion_cardinal}. "
            "El fuego puede acelerarse al subir por la ladera si el combustible es seco y continuo."
        )
    else:
        descripcion = (
            "No hay información suficiente para definir con precisión una dirección dominante, pero el riesgo sigue aumentado "
            "por la temperatura, la sequedad del combustible y la intensidad del viento."
        )

    prompt = (
        "Estoy analizando un incendio forestal con estos datos: "
        f"viento {viento} km/h, humedad relativa {humedad}%, pendiente {pendiente}% , "
        f"tipo de combustible {combustible.get('tipo_combustible', 'Desconocido')}, "
        f"humedad del combustible {humedad_combustible:.1f}%, dirección del viento {direccion_viento}°, "
        f"dirección de pendiente {direccion_pendiente}°. "
        "Explica en español qué dirección tiene mayor probabilidad de avance del fuego, cómo se combina viento y pendiente, "
        "y qué acciones preventivas se deberían priorizar."
    )
    respuesta_ia = _llm_analisis_ia(prompt)

    return {
        "modelo": "IA asistida" if respuesta_ia else "heuristico",
        "motor": "openai-compatible" if respuesta_ia else "reglas-de-incendio",
        "direccion_probable_grados": round(direccion_final, 1) if direccion_final is not None else None,
        "direccion_probable_cardinal": direccion_cardinal,
        "factor_aceeleracion": aceleracion,
        "nivel_aceeleracion": nivel_aceeleracion,
        "descripcion": descripcion,
        "respuesta_ia": respuesta_ia or descripcion,
        "viento_impacta_hacia": direccion_viento,
        "pendiente_hacia": direccion_pendiente,
        "riesgo": riesgo or {},
    }


def _resolver_humedad_combustible(meteo, combustible):
    if isinstance(combustible, dict):
        for clave in ("humedad_combustible", "fuel_moisture", "fuel_moisture_content", "swid"):
            valor = combustible.get(clave)
            if valor is not None:
                try:
                    return float(valor)
                except (TypeError, ValueError):
                    pass

    if isinstance(meteo, dict):
        for clave in ("humedad_combustible", "fuel_moisture", "swid"):
            valor = meteo.get(clave)
            if valor is not None:
                try:
                    return float(valor)
                except (TypeError, ValueError):
                    pass

    humedad_relativa = meteo.get("humedad") if isinstance(meteo, dict) else None
    if humedad_relativa is not None:
        try:
            return max(5.0, float(humedad_relativa) * 0.6)
        except (TypeError, ValueError):
            pass

    return None


def predecir_propagacion_incendio(meteo, topografia, combustible, humedad_combustible=None):
    """Predice la evolución del incendio considerando humedad del combustible y la dinámica de vientos de día/noche."""
    temperatura = float(meteo.get("temperatura") or 25)
    humedad_relativa = float(meteo.get("humedad") or 40)
    viento = float(meteo.get("viento") or 0)
    pendiente = float(topografia.get("maxima_pendiente_pct") or 0)
    is_day = bool(meteo.get("is_day") in (1, True, "1", "true", "True"))

    humedad_combustible = humedad_combustible
    if humedad_combustible is None:
        humedad_combustible = _resolver_humedad_combustible(meteo, combustible)
    if humedad_combustible is None:
        humedad_combustible = max(5.0, humedad_relativa * 0.6)

    factor = 1.0
    factor += max(0, (temperatura - 24) / 15) * 0.8
    factor += max(0, (45 - humedad_relativa) / 35) * 0.9
    factor += max(0, (viento - 8) / 18) * 1.1
    factor += min(1.0, pendiente / 35) * 0.7
    factor += max(0, (30 - humedad_combustible) / 12) * 0.8

    if combustible.get("tipo_combustible") in ("Bosque", "Matorral"):
        factor += 0.7
    elif combustible.get("tipo_combustible") in ("Pastizal", "Agrícola"):
        factor += 0.4

    if is_day and pendiente >= 15:
        factor += 1.0
        descripcion = (
            "Es de día y el incendio está en una zona de ladera con pendiente relevante; "
            "los vientos térmicos ascendentes pueden acelerar el avance hacia arriba, especialmente si el combustible está muy seco."
        )
        velocidad = "Muy rápida"
    elif not is_day and pendiente >= 20:
        factor += 1.1
        descripcion = (
            "Es de noche y la pendiente es pronunciada; aun con temperatura ambiente baja, el combustible seco y los vientos fríos descendentes pueden mantener una propagación peligrosa hacia abajo."
        )
        velocidad = "Muy rápida"
    elif viento >= 25:
        descripcion = (
            "El viento favorece la propagación y el fuego puede desplazarse con rapidez si la humedad del combustible sigue baja."
        )
        velocidad = "Rápida"
    elif humedad_combustible > 30:
        descripcion = (
            "La humedad del combustible aún es moderada y limita la velocidad de propagación, aunque el frente puede mantenerse activo."
        )
        velocidad = "Moderada"
    else:
        descripcion = (
            "El comportamiento del incendio es variable: el combustible seco y la topografía favorecen una expansión sostenida."
        )
        velocidad = "Moderada"

    factor = round(min(factor, 5.5), 2)
    if factor >= 4.2:
        velocidad = "Muy rápida"
    elif factor >= 3.0:
        velocidad = "Rápida"
    elif factor >= 2.0:
        velocidad = "Moderada"
    else:
        velocidad = "Lenta"

    return {
        "factor": factor,
        "velocidad": velocidad,
        "humedad_combustible": round(humedad_combustible, 1),
        "descripcion": descripcion,
        "es_de_dia": is_day,
    }


def calcular_riesgo_ambiental(meteo, topografia, combustible):
    """Calcula un puntaje de riesgo que combina clima, pendiente, humedad del combustible y tipo de combustible."""
    puntuacion = 0

    viento = float(meteo.get("viento") or 0)
    humedad = meteo.get("humedad")
    pendiente = float(topografia.get("maxima_pendiente_pct") or 0)
    tipo_combustible = combustible.get("tipo_combustible", "Desconocido")
    humedad_combustible = _resolver_humedad_combustible(meteo, combustible)

    if viento >= 40:
        puntuacion += 24
    elif viento >= 25:
        puntuacion += 16
    elif viento >= 10:
        puntuacion += 8

    if humedad is not None:
        if humedad < 20:
            puntuacion += 20
        elif humedad < 30:
            puntuacion += 14
        elif humedad < 50:
            puntuacion += 8
    else:
        puntuacion += 6

    if humedad_combustible is not None:
        if humedad_combustible < 12:
            puntuacion += 18
        elif humedad_combustible < 20:
            puntuacion += 12
        elif humedad_combustible < 30:
            puntuacion += 8

    if pendiente >= 25:
        puntuacion += 18
    elif pendiente >= 15:
        puntuacion += 12
    elif pendiente >= 8:
        puntuacion += 6

    if meteo.get("is_day") in (1, True, "1", "true", "True") and pendiente >= 15:
        puntuacion += 8
    elif meteo.get("is_day") not in (1, True, "1", "true", "True") and pendiente >= 20:
        puntuacion += 8

    if tipo_combustible in ("Bosque", "Matorral"):
        puntuacion += 18
    elif tipo_combustible in ("Pastizal", "Agrícola"):
        puntuacion += 12
    elif tipo_combustible == "Desconocido":
        puntuacion += 6

    if meteo.get("categoria_viento") in ("Alto", "Extremo"):
        puntuacion += 8

    puntuacion = max(0, min(100, puntuacion))

    if puntuacion >= 80:
        nivel = "Extremo"
        descripcion = "El entorno presenta condiciones muy favorables para la propagación del fuego y requiere respuesta inmediata."
    elif puntuacion >= 60:
        nivel = "Alto"
        descripcion = "El incendio puede escalar rápidamente si no se gestionan las condiciones de viento, combustible y pendiente."
    elif puntuacion >= 40:
        nivel = "Medio"
        descripcion = "Hay riesgo de expansión importante y es necesario reforzar vigilancia y controles de contención."
    else:
        nivel = "Bajo"
        descripcion = "El riesgo es moderado y puede mantenerse bajo con monitoreo y medidas preventivas."

    return {
        "puntuacion": puntuacion,
        "nivel": nivel,
        "descripcion": descripcion,
    }


def generar_recomendaciones(meteo, topografia, combustible, nivel_riesgo):
    recomendaciones = []

    viento = float(meteo.get("viento") or 0)
    humedad = meteo.get("humedad")
    pendiente = float(topografia.get("maxima_pendiente_pct") or 0)
    tipo_combustible = combustible.get("tipo_combustible", "Desconocido")
    humedad_combustible = _resolver_humedad_combustible(meteo, combustible)
    is_day = meteo.get("is_day") in (1, True, "1", "true", "True")

    if viento >= 25:
        recomendaciones.append("Priorizar medidas defensivas en la dirección del viento y evitar maniobras en zonas con ráfagas fuertes.")
    else:
        recomendaciones.append("Mantener vigilancia activa y reforzar controles de perímetro para evitar cambios bruscos del frente de fuego.")

    if humedad is not None:
        if humedad < 30:
            recomendaciones.append("La humedad es baja; reforzar cortes de combustible y reducir actividades con riesgo de ignición.")
        elif humedad < 50:
            recomendaciones.append("La humedad es moderada; monitorear puntos calientes y mantener la línea de contención preparada.")
        else:
            recomendaciones.append("La humedad ambiente ayuda a contener el avance, pero se debe seguir controlando el combustible cercano al perímetro.")

    if humedad_combustible is not None:
        if humedad_combustible < 20:
            recomendaciones.append("La humedad del combustible está muy baja y aumenta la probabilidad de ignición sostenida y propagación rápida.")
        elif humedad_combustible < 30:
            recomendaciones.append("La humedad del combustible es baja; revisar puntos calientes y reforzar vigilancia con mayor frecuencia.")

    if pendiente >= 15:
        recomendaciones.append("El terreno presenta pendientes relevantes; evitar el ingreso de personal a sectores con mayor inclinación y usar accesos inferiores.")

    if is_day and pendiente >= 15:
        recomendaciones.append("Es de día y el incendio puede ganar velocidad hacia la pendiente por los vientos térmicos ascendentes; priorizar una línea defensiva en la base de la ladera.")
    elif not is_day and pendiente >= 20:
        recomendaciones.append("Es de noche y los vientos fríos descendentes pueden empujar el frente rápido en dirección de bajada; reforzar la vigilancia en cotas inferiores.")

    if tipo_combustible in ("Bosque", "Matorral"):
        recomendaciones.append("La vegetación es densa; priorizar el trabajo en la periferia y mantener rutas de evacuación claramente señalizadas.")
    elif tipo_combustible in ("Pastizal", "Agrícola"):
        recomendaciones.append("El combustible es ligero y se propagará rápido; mantener limpieza y puntos de contención en el eje de avance principal.")

    if nivel_riesgo in ("Alto", "Extremo"):
        recomendaciones.append("Activar plan de respuesta preventiva inmediato con recursos de apoyo, vigilancia del perímetro y preparación de evacuaciones.")
    else:
        recomendaciones.append("Seguir realizando monitoreo regular para detectar cambios de comportamiento del fuego antes de que escalen.")

    return recomendaciones
