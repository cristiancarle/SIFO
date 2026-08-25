import math
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from config import (
    CARGA_COMBUSTIBLE,
    DIRECCION_PROPAGACION_GRADOS,
    ESCALAS_HEATMAP,
    ESCENARIOS_HORARIOS,
    FACTOR_PROPAGACION_VIENTO,
    FACTOR_VEGETACION,
    HUMEDAD_RELATIVA,
    KML_DIR,
    PASOS_SIMULACION_MINUTOS,
    PENDIENTE_MEDIA,
    RADIO_ANALISIS,
    TIPO_VEGETACION,
    VELOCIDAD_VIENTO_KMH
)

from modulos.database import obtener_incendio_por_id
from modulos.cartografia import (
    obtener_red_vial,
    clasificar_camino
)

from modulos.estilos import (
    estilo_carrera_primaria,
    estilo_carrera_secundaria,
    estilo_incendio,
    estilo_ruta,
    estilo_camino,
    estilo_sendero,
    estilo_simulacion,
    estilo_viento,
    estilos_heatmap
)

from modulos.utilidades import (
    crear_carpetas,
    escribir_log,
    sanitizar_nombre_archivo
)

NAMESPACE = "http://www.opengis.net/kml/2.2"


def _obtener_escenario_hora(indice):

    escenario = ESCENARIOS_HORARIOS[indice % len(ESCENARIOS_HORARIOS)]
    return {
        "viento_kmh": escenario["viento_kmh"],
        "direccion_grados": escenario["direccion_grados"],
        "humedad": escenario["humedad"],
        "pendiente": escenario["pendiente"],
        "vegetacion": escenario["vegetacion"],
    }


def _factor_ambiental(escenario=None):

    if escenario is None:
        escenario = _obtener_escenario_hora(0)

    viento = 1 + (escenario["viento_kmh"] / 28)
    humedad = max(0.25, 1.2 - (escenario["humedad"] / 100))
    pendiente = 1 + (escenario["pendiente"] / 90)
    vegetacion = FACTOR_VEGETACION.get(escenario["vegetacion"], 1.2)
    combustible = CARGA_COMBUSTIBLE.get(escenario["vegetacion"], 1.2)

    return 0.75 * viento * humedad * pendiente * vegetacion * combustible


def _calcular_propagacion_realista(radio_analisis, factor_ambiental, intensidad=1.0):

    base = max(0.25, min(3.0, factor_ambiental * intensidad))
    frente = radio_analisis * (0.10 + (base * 0.18))
    flanco = radio_analisis * (0.07 + (base * 0.11))
    return frente, flanco


def _descripcion_incendio(incendio):

    return (
        f"Nombre: {incendio[3]}\n"
        f"Fecha: {incendio[1]} {incendio[2]}\n"
        f"Ubicación: {incendio[4]} - {incendio[5]}\n"
        f"Estado: {incendio[9]}\n"
        f"Radio de análisis: {incendio[10]} m\n"
        f"Descripción: {incendio[8] or 'Sin descripción'}"
    )


def _crear_style_icono(documento, estilo):

    style = ET.SubElement(documento, "Style", id=estilo["id"])
    icon_style = ET.SubElement(style, "IconStyle")
    ET.SubElement(icon_style, "scale").text = estilo["icon_scale"]
    icon = ET.SubElement(icon_style, "Icon")
    ET.SubElement(icon, "href").text = estilo["icon_href"]


def _crear_style_linea(documento, estilo):

    style = ET.SubElement(documento, "Style", id=estilo["id"])
    line_style = ET.SubElement(style, "LineStyle")
    ET.SubElement(line_style, "color").text = estilo["line_color"]
    ET.SubElement(line_style, "width").text = estilo["line_width"]

    if "poly_color" in estilo:
        poly_style = ET.SubElement(style, "PolyStyle")
        ET.SubElement(poly_style, "color").text = estilo["poly_color"]


def _crear_estructura_base(nombre):

    ET.register_namespace("", NAMESPACE)

    kml = ET.Element(f"{{{NAMESPACE}}}kml")
    documento = ET.SubElement(kml, "Document")
    ET.SubElement(documento, "name").text = _texto_seguro(nombre)

    _crear_style_icono(documento, estilo_incendio())
    _crear_style_linea(documento, estilo_ruta())
    _crear_style_linea(documento, estilo_camino())
    _crear_style_linea(documento, estilo_sendero())
    _crear_style_linea(documento, estilo_simulacion())
    _crear_style_linea(documento, estilo_viento())
    _crear_style_linea(documento, estilo_carrera_primaria())
    _crear_style_linea(documento, estilo_carrera_secundaria())

    for estilo in estilos_heatmap():
        _crear_style_linea(documento, estilo)

    return kml, documento


def _agregar_folder(documento, nombre):

    folder = ET.SubElement(documento, "Folder")
    ET.SubElement(folder, "name").text = _texto_seguro(nombre)
    return folder


def _texto_seguro(valor):

    if valor is None:
        return ""

    if isinstance(valor, (list, tuple, set)):
        valor = " ".join(str(item) for item in valor if item is not None)

    if isinstance(valor, float) and not math.isfinite(valor):
        return ""

    return str(valor)


def _agregar_descripcion(placemark, descripcion):

    descripcion_texto = _texto_seguro(descripcion)
    if descripcion_texto:
        ET.SubElement(placemark, "description").text = descripcion_texto


def _agregar_timespan(placemark, inicio, fin):

    if inicio is None or fin is None:
        return

    timespan = ET.SubElement(placemark, "TimeSpan")
    ET.SubElement(timespan, "begin").text = inicio.isoformat()
    ET.SubElement(timespan, "end").text = fin.isoformat()


def _coordenadas_validas(coordenadas):

    coordenadas_limpias = []

    for lon, lat in coordenadas:
        try:
            lon_valor = float(lon)
            lat_valor = float(lat)
        except (TypeError, ValueError):
            continue

        if not math.isfinite(lon_valor) or not math.isfinite(lat_valor):
            continue

        coordenadas_limpias.append((lon_valor, lat_valor))

    return coordenadas_limpias


def _formatear_coordenadas(coordenadas):

    coordenadas_limpias = _coordenadas_validas(coordenadas)

    if not coordenadas_limpias:
        return "0,0,0"

    return " ".join(f"{lon},{lat},0" for lon, lat in coordenadas_limpias)


def _agregar_punto(folder, nombre, longitud, latitud, descripcion):

    try:
        lon_valor = float(longitud)
        lat_valor = float(latitud)
    except (TypeError, ValueError):
        return

    if not math.isfinite(lon_valor) or not math.isfinite(lat_valor):
        return

    placemark = ET.SubElement(folder, "Placemark")
    ET.SubElement(placemark, "name").text = _texto_seguro(nombre)
    ET.SubElement(placemark, "styleUrl").text = "#incendio"
    _agregar_descripcion(placemark, descripcion)

    point = ET.SubElement(placemark, "Point")
    ET.SubElement(point, "coordinates").text = f"{lon_valor},{lat_valor},0"


def _agregar_linea(folder, nombre, coordenadas, style_id):

    placemark = ET.SubElement(folder, "Placemark")
    ET.SubElement(placemark, "name").text = _texto_seguro(nombre)
    ET.SubElement(placemark, "styleUrl").text = _texto_seguro(f"#{style_id}")

    linestring = ET.SubElement(placemark, "LineString")
    ET.SubElement(linestring, "tessellate").text = "1"
    ET.SubElement(linestring, "coordinates").text = _formatear_coordenadas(
        coordenadas
    )


def _agregar_flecha_viento(folder, latitud, longitud, distancia_m, angulo_grados):

    angulo_radianes = math.radians(angulo_grados)
    lat_fin, lon_fin = _desplazar_punto(
        latitud,
        longitud,
        math.sin(angulo_radianes) * distancia_m,
        math.cos(angulo_radianes) * distancia_m,
    )

    punta_mas_lejana = 220
    angulo_izq = angulo_radianes + math.radians(22)
    angulo_der = angulo_radianes - math.radians(22)
    lat_punta_izq, lon_punta_izq = _desplazar_punto(
        lat_fin,
        lon_fin,
        math.sin(angulo_izq) * punta_mas_lejana,
        math.cos(angulo_izq) * punta_mas_lejana,
    )
    lat_punta_der, lon_punta_der = _desplazar_punto(
        lat_fin,
        lon_fin,
        math.sin(angulo_der) * punta_mas_lejana,
        math.cos(angulo_der) * punta_mas_lejana,
    )

    coordenadas = [
        (longitud, latitud),
        (lon_fin, lat_fin),
        (lon_punta_izq, lat_punta_izq),
        (lon_fin, lat_fin),
        (lon_punta_der, lat_punta_der),
    ]

    _agregar_linea(folder, 'Dirección del viento', coordenadas, 'viento')


def _agregar_carrera_propagacion(folder, latitud, longitud, distancia_m, angulo_grados, style_id, nombre, desplazamiento_m=0):

    angulo_radianes = math.radians(angulo_grados)
    lat_fin, lon_fin = _desplazar_punto(
        latitud,
        longitud,
        math.sin(angulo_radianes) * distancia_m,
        math.cos(angulo_radianes) * distancia_m,
    )

    if desplazamiento_m:
        angulo_lateral = angulo_radianes + math.radians(90)
        lat_fin, lon_fin = _desplazar_punto(
            lat_fin,
            lon_fin,
            math.sin(angulo_lateral) * desplazamiento_m,
            math.cos(angulo_lateral) * desplazamiento_m,
        )

    coordenadas = [
        (longitud, latitud),
        (lon_fin, lat_fin),
    ]
    _agregar_linea(folder, nombre, coordenadas, style_id)


def _agregar_poligono(
        folder,
        nombre,
        coordenadas,
        style_id,
        descripcion=None,
        inicio=None,
        fin=None):

    placemark = ET.SubElement(folder, "Placemark")
    ET.SubElement(placemark, "name").text = _texto_seguro(nombre)
    ET.SubElement(placemark, "styleUrl").text = _texto_seguro(f"#{style_id}")
    _agregar_descripcion(placemark, descripcion)
    _agregar_timespan(placemark, inicio, fin)

    polygon = ET.SubElement(placemark, "Polygon")
    ET.SubElement(polygon, "tessellate").text = "1"
    outer_boundary = ET.SubElement(polygon, "outerBoundaryIs")
    linear_ring = ET.SubElement(outer_boundary, "LinearRing")

    anillo = list(coordenadas)

    if anillo[0] != anillo[-1]:
        anillo.append(anillo[0])

    ET.SubElement(linear_ring, "coordinates").text = _formatear_coordenadas(
        anillo
    )


def _desplazar_punto(latitud, longitud, norte_m, este_m):

    try:
        latitud = float(latitud)
        longitud = float(longitud)
        norte_m = float(norte_m)
        este_m = float(este_m)
    except (TypeError, ValueError):
        return 0.0, 0.0

    radio_tierra = 6378137
    delta_lat = (norte_m / radio_tierra) * (180 / math.pi)
    cos_latitud = math.cos(math.radians(latitud))
    if abs(cos_latitud) < 1e-12:
        cos_latitud = 1e-12
    delta_lon = ((este_m / radio_tierra) * (180 / math.pi)) / cos_latitud

    lat_salida = latitud + delta_lat
    lon_salida = longitud + delta_lon

    if not math.isfinite(lat_salida) or not math.isfinite(lon_salida):
        return 0.0, 0.0

    return lat_salida, lon_salida


def _generar_elipse(
        latitud,
        longitud,
        semieje_mayor_m,
        semieje_menor_m,
        rotacion_grados,
        desplazamiento_m=0,
        puntos=72):

    angulo_rotacion = math.radians(rotacion_grados)
    norte = math.cos(angulo_rotacion) * desplazamiento_m
    este = math.sin(angulo_rotacion) * desplazamiento_m
    centro_lat, centro_lon = _desplazar_punto(latitud, longitud, norte, este)
    coordenadas = []

    for indice in range(puntos):
        angulo = 2 * math.pi * indice / puntos
        x = semieje_mayor_m * math.cos(angulo)
        y = semieje_menor_m * math.sin(angulo)

        este_rotado = (
            x * math.sin(angulo_rotacion) +
            y * math.cos(angulo_rotacion)
        )
        norte_rotado = (
            x * math.cos(angulo_rotacion) -
            y * math.sin(angulo_rotacion)
        )

        punto_lat, punto_lon = _desplazar_punto(
            centro_lat,
            centro_lon,
            norte_rotado,
            este_rotado
        )

        coordenadas.append((punto_lon, punto_lat))

    return coordenadas


def _obtener_fecha_base(incendio):

    try:
        return datetime.strptime(
            f"{incendio[1]} {incendio[2]}",
            "%d/%m/%Y %H:%M"
        )
    except ValueError:
        return None


def _descripcion_simulacion(minutos, semieje_mayor, semieje_menor):

    return (
        f"Proyección a {minutos} minutos.\n"
        f"Frente estimado: {int(semieje_mayor)} m.\n"
        f"Flancos estimados: {int(semieje_menor)} m.\n"
        "Modelo simplificado con propagación elíptica."
    )


def generar_kml(id_incendio):

    incendio = obtener_incendio_por_id(id_incendio)

    if incendio is None:

        print("Incendio inexistente.")
        return

    # -----------------------------
    # Datos
    # -----------------------------

    latitud = incendio[6]
    longitud = incendio[7]
    nombre = incendio[3] or f"Incendio {incendio[0]}"
    radio_analisis = incendio[10] or RADIO_ANALISIS

    escribir_log(f"Generando mapa de {nombre}")
    crear_carpetas()

    # -----------------------------
    # Crear KML
    # -----------------------------

    kml, documento = _crear_estructura_base(nombre)

    carpeta_incendio = _agregar_folder(documento, "Incendio")
    carpeta_heatmap = _agregar_folder(documento, "Mapa de calor")
    carpeta_simulacion = _agregar_folder(documento, "Simulación de avance")
    carpeta_viento = _agregar_folder(documento, "Dirección del viento")
    carpeta_primarias = _agregar_folder(documento, "Carrera primaria del incendio")
    carpeta_secundarias = _agregar_folder(documento, "Carrera secundaria del incendio")
    carpeta_senderos = _agregar_folder(documento, "Senderos")

    # -----------------------------
    # Punto incendio
    # -----------------------------

    _agregar_punto(
        carpeta_incendio,
        nombre,
        longitud,
        latitud,
        _descripcion_incendio(incendio)
    )

    _agregar_flecha_viento(
        carpeta_viento,
        latitud,
        longitud,
        5000,
        DIRECCION_PROPAGACION_GRADOS,
    )

    direccion_viento = DIRECCION_PROPAGACION_GRADOS
    for indice, angulo in enumerate([
        direccion_viento,
        (direccion_viento + 15) % 360,
        (direccion_viento - 15) % 360,
    ]):
        _agregar_carrera_propagacion(
            carpeta_primarias,
            latitud,
            longitud,
            max(800, radio_analisis * 0.55),
            angulo,
            "carrera_primaria",
            f"Carrera primaria {indice + 1}",
        )

    for indice, angulo in enumerate([
        (direccion_viento + 45) % 360,
        (direccion_viento - 45) % 360,
        (direccion_viento + 90) % 360,
        (direccion_viento - 90) % 360,
    ]):
        _agregar_carrera_propagacion(
            carpeta_secundarias,
            latitud,
            longitud,
            max(500, radio_analisis * 0.35),
            angulo,
            "carrera_secundaria",
            f"Carrera secundaria {indice + 1}",
        )

    # -----------------------------
    # Simulación
    # -----------------------------

    fecha_base = _obtener_fecha_base(incendio)
    escenario_base = _obtener_escenario_hora(0)
    factor_ambiental = _factor_ambiental(escenario_base)
    maximo_frente, maximo_flanco = _calcular_propagacion_realista(
        radio_analisis,
        factor_ambiental,
        intensidad=1.1
    )

    folder_condiciones = _agregar_folder(documento, "Condiciones ambientales")
    descripcion_condiciones = (
        f"Viento: {escenario_base['viento_kmh']} km/h\n"
        f"Dirección principal: {escenario_base['direccion_grados']}°\n"
        f"Humedad relativa: {escenario_base['humedad']}%\n"
        f"Pendiente media: {escenario_base['pendiente']}%\n"
        f"Vegetación dominante: {escenario_base['vegetacion']}\n"
        f"Factor ambiental estimado: {factor_ambiental:.2f}\n"
        f"Riesgo de propagación: {min(10, max(1, round(factor_ambiental * 3, 1)))} / 10"
    )
    placemark_condiciones = ET.SubElement(folder_condiciones, "Placemark")
    ET.SubElement(placemark_condiciones, "name").text = "Condiciones ambientales"
    ET.SubElement(placemark_condiciones, "description").text = descripcion_condiciones
    point_condiciones = ET.SubElement(placemark_condiciones, "Point")
    ET.SubElement(point_condiciones, "coordinates").text = f"{longitud},{latitud},0"

    heatmap_styles = {
        nombre_estilo: f"heatmap_{nombre_estilo}"
        for nombre_estilo, _ in ESCALAS_HEATMAP
    }

    for nombre_estilo, escala in reversed(ESCALAS_HEATMAP):
        semieje_mayor = maximo_frente * escala
        semieje_menor = maximo_flanco * escala
        poligono_heatmap = _generar_elipse(
            latitud,
            longitud,
            semieje_mayor,
            semieje_menor,
            escenario_base["direccion_grados"],
            desplazamiento_m=semieje_mayor * 0.18
        )
        _agregar_poligono(
            carpeta_heatmap,
            f"Intensidad {nombre_estilo}",
            poligono_heatmap,
            heatmap_styles[nombre_estilo],
            (
                f"Zona de intensidad {nombre_estilo}.\n"
                f"Extensión estimada: {int(semieje_mayor)} m."
            )
        )

    paso_maximo = PASOS_SIMULACION_MINUTOS[-1]

    for indice, minutos in enumerate(PASOS_SIMULACION_MINUTOS):
        escenario = _obtener_escenario_hora(indice)
        factor_escenario = _factor_ambiental(escenario)
        frente_actual, flanco_actual = _calcular_propagacion_realista(
            radio_analisis,
            factor_escenario,
            intensidad=(1.0 + (indice / len(PASOS_SIMULACION_MINUTOS)))
        )
        proporcion = minutos / paso_maximo
        semieje_mayor = frente_actual * proporcion
        semieje_menor = flanco_actual * proporcion
        semieje_mayor = max(semieje_mayor, 150)
        semieje_menor = max(semieje_menor, 120)
        poligono = _generar_elipse(
            latitud,
            longitud,
            semieje_mayor,
            semieje_menor,
            escenario["direccion_grados"],
            desplazamiento_m=semieje_mayor * 0.18
        )
        inicio = fecha_base
        fin = None

        if fecha_base is not None:
            fin = fecha_base + timedelta(minutes=minutos)

        _agregar_poligono(
            carpeta_simulacion,
            f"Avance estimado {minutos} min ({escenario['vegetacion']}, {escenario['viento_kmh']} km/h)",
            poligono,
            "simulacion",
            _descripcion_simulacion(
                minutos,
                semieje_mayor,
                semieje_menor
            )
            + f"\nVegetación: {escenario['vegetacion']}\nViento: {escenario['viento_kmh']} km/h",
            inicio=inicio,
            fin=fin
        )

    # -----------------------------
    # Descargar red vial
    # -----------------------------

    print("Descargando OpenStreetMap...")

    caminos = obtener_red_vial(
        latitud,
        longitud,
        radio_analisis
    )

    print(f"{len(caminos)} caminos encontrados")

    # -----------------------------
    # Dibujar
    # -----------------------------

    for camino in caminos:

        categoria = clasificar_camino(
            camino["tipo"]
        )

        if categoria == "ruta":

            _agregar_linea(
                carpeta_primarias,
                camino["nombre"],
                camino["coordenadas"],
                "ruta"
            )

        elif categoria == "camino":

            _agregar_linea(
                carpeta_secundarias,
                camino["nombre"],
                camino["coordenadas"],
                "camino"
            )

        elif categoria == "sendero":

            _agregar_linea(
                carpeta_senderos,
                camino["nombre"],
                camino["coordenadas"],
                "sendero"
            )

    # -----------------------------
    # Guardar
    # -----------------------------

    os.makedirs(KML_DIR, exist_ok=True)

    archivo = os.path.join(
        KML_DIR,
        sanitizar_nombre_archivo(nombre, ".kml")
    )

    arbol = ET.ElementTree(kml)
    ET.indent(arbol, space="    ")
    arbol.write(archivo, encoding="utf-8", xml_declaration=True)

    escribir_log("Mapa generado correctamente.")

    print()

    print("===================================")
    print("Mapa generado correctamente")
    print(archivo)
    print("===================================")