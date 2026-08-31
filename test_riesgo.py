from core.riesgo import (
    validar_coordenadas,
    calcular_riesgo_ambiental,
    generar_recomendaciones,
    analizar_ia_propagacion,
)


def test_validar_coordenadas_acepta_rangos_validos():
    valido, error = validar_coordenadas(-34.6037, -58.3816)
    assert valido is True
    assert error is None


def test_validar_coordenadas_rechaza_latitud_fuera_de_rango():
    valido, error = validar_coordenadas(91, 0)
    assert valido is False
    assert "latitud" in error.lower()


def test_calcular_riesgo_ambiental_devuelve_nivel_esperado():
    meteo = {"viento": 45, "humedad": 10, "categoria_viento": "Extremo"}
    topografia = {"maxima_pendiente_pct": 30}
    combustible = {"tipo_combustible": "Bosque"}

    riesgo = calcular_riesgo_ambiental(meteo, topografia, combustible)

    assert riesgo["puntuacion"] >= 60
    assert riesgo["nivel"] in {"Alto", "Extremo"}
    assert "descripcion" in riesgo


def test_generar_recomendaciones_incluye_acciones_operativas():
    meteo = {"viento": 35, "humedad": 18}
    topografia = {"maxima_pendiente_pct": 22}
    combustible = {"tipo_combustible": "Matorral"}

    recomendaciones = generar_recomendaciones(meteo, topografia, combustible, "Alto")

    assert len(recomendaciones) >= 3
    assert any("evacu" in recomendacion.lower() for recomendacion in recomendaciones)


def test_analizar_ia_propagacion_combina_viento_y_pendiente():
    meteo = {"viento": 28, "humedad": 18, "direccion": 0, "direccion_cardinal": "Norte"}
    topografia = {"maxima_pendiente_pct": 22, "pendiente_direccion": 90, "pendiente_direccion_cardinal": "Este"}
    combustible = {"tipo_combustible": "Bosque"}

    analisis = analizar_ia_propagacion(meteo, topografia, combustible)

    assert analisis["direccion_probable_cardinal"] in {"Sudeste", "Sureste", "Sur"}
    assert analisis["factor_aceeleracion"] >= 2.0
    assert "propagación" in analisis["descripcion"].lower()
