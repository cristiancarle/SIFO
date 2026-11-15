"""Generación del KML: foco, viento (azul), carreras primarias (rojas) y secundarias (naranjas)."""
from xml.sax.saxutils import escape

from .comportamiento import destino

AZUL, ROJO, NARANJA = "ffff0000", "ff0000ff", "ff0080ff"  # formato KML aabbggrr
LARGO_VIENTO_M = 2000.0


def _coords(puntos):
    return " ".join(f"{lo:.6f},{la:.6f},0" for la, lo in puntos)


def _linea(nombre, descripcion, puntos, color, ancho, suelo=False):
    modo = "<tessellate>1</tessellate><altitudeMode>clampToGround</altitudeMode>" if suelo else ""
    return (f"<Placemark><name>{escape(nombre)}</name><description>{escape(descripcion)}</description>"
            f"<Style><LineStyle><color>{color}</color><width>{ancho}</width></LineStyle></Style>"
            f"<LineString>{modo}<coordinates>{_coords(puntos)}</coordinates></LineString></Placemark>")


ESTILOS_EXPANSION = {"inmediata": "ff0000ff", "9hs": "ff0080ff", "24hs": "ff00ffff"}  # aabbggrr


def _poligono(e):
    base = ESTILOS_EXPANSION[e["clave"]]
    relleno = "4d" + base[2:]  # alfa 0x4d ≈ 30% opaco = 70% transparente
    desc = (f"Extensión máx. {e['largo_m'] / 1000:.2f} km hacia {e['rumbo_deg']:.0f}°, "
            f"ancho máx. {e['ancho_max_m'] / 1000:.2f} km. Según combustible, meteorología y topografía.")
    return (f"<Placemark><name>{escape(e['nombre'])}</name><description>{escape(desc)}</description>"
            f"<Style><LineStyle><color>{base}</color><width>2</width></LineStyle>"
            f"<PolyStyle><color>{relleno}</color><fill>1</fill><outline>1</outline></PolyStyle></Style>"
            f"<Polygon><extrude>0</extrude><tessellate>1</tessellate><altitudeMode>clampToGround</altitudeMode>"
            f"<outerBoundaryIs><LinearRing><coordinates>{_coords(e['poligono'])}</coordinates>"
            f"</LinearRing></outerBoundaryIs></Polygon></Placemark>")


def generar_kml(lat, lon, resultados):
    """Devuelve el KML (string) con una carpeta por período."""
    nombre = (resultados.get("meta") or {}).get("nombre") or "Análisis de incendio forestal"
    partes = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
              f"<name>{escape(nombre)}</name>",
              '<Style id="fuego"><IconStyle><scale>1.4</scale><Icon><href>'
              "http://maps.google.com/mapfiles/kml/shapes/firedept.png</href></Icon></IconStyle></Style>",
              f"<Placemark><name>INICIO DEL FOCO</name><styleUrl>#fuego</styleUrl>"
              f"<Point><coordinates>{lon:.6f},{lat:.6f},0</coordinates></Point></Placemark>"]

    for p in resultados.get("periodos", []):
        m, c = p["meteo"], p["comportamiento"]
        etiqueta = f"+{m['inicio_h']}hs ({m['hora_inicio_str']}-{m['hora_fin_str']})"
        partes.append(f"<Folder><name>Período {escape(etiqueta)}</name>")

        hacia = c["direccion_viento_hacia_deg"]
        desc = (f"Viento {m['viento_med_kmh']:.0f} km/h desde {m['viento_dir_med_deg']:.0f}°, "
                f"hacia {hacia:.0f}°")
        partes.append(_linea(f"Viento {etiqueta}", desc,
                             [(lat, lon), destino(lat, lon, hacia, LARGO_VIENTO_M)], AZUL, 3))

        for l in c["lineas_carrera_primaria"]:
            rol = "Carrera primaria" if l["tipo"] == "principal" else "Flanco"
            d = (f"{rol} rumbo {l['rumbo']:.0f}°, {l['extension_m']:.0f} m, "
                 f"{c['velocidad_estimada_kmh']:.2f} km/h")
            partes.append(_linea(f"{rol} {etiqueta}", d, l["puntos"], ROJO, 4))

        for k, s in enumerate(c["lineas_carrera_secundaria"], 1):
            d = (f"Fuego en quebrada: corre aguas abajo, ~{s['velocidad_kmh']:.2f} km/h. "
                 "RIESGO EXTREMO para brigadas dentro de la quebrada.")
            partes.append(_linea(f"Carrera secundaria {k} {etiqueta}", d, s["puntos"], NARANJA, 3, True))
        partes.append("</Folder>")

    exp = resultados.get("expansiones", [])
    if exp:
        partes.append("<Folder><name>Posibles expansiones del incendio</name>")
        partes.extend(_poligono(e) for e in reversed(exp))
        partes.append("</Folder>")

    partes.append("</Document></kml>")
    return "\n".join(partes)
