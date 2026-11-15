"""Conversor simple KML -> GeoJSON (Point, LineString, Polygon) conservando estilos."""
import re
import xml.etree.ElementTree as ET

NS = "{http://www.opengis.net/kml/2.2}"


def _color(kml_color):
    """KML aabbggrr -> (#rrggbb, opacidad 0-1)."""
    c = (kml_color or "").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{8}", c):
        return "#3388ff", 1.0
    a, b, g, r = c[0:2], c[2:4], c[4:6], c[6:8]
    return f"#{r}{g}{b}", round(int(a, 16) / 255, 2)


def _coords(txt):
    out = []
    for tok in (txt or "").split():
        p = tok.split(",")
        if len(p) >= 2:
            out.append([float(p[0]), float(p[1])])
    return out


def _texto(el, tag):
    h = el.find(NS + tag)
    return (h.text or "").strip() if h is not None and h.text else ""


def kml_a_geojson(kml_texto):
    raiz = ET.fromstring(kml_texto.encode("utf-8") if isinstance(kml_texto, str) else kml_texto)
    feats = []
    for pm in raiz.iter(NS + "Placemark"):
        props = {"name": _texto(pm, "name"), "description": _texto(pm, "description")}
        estilo = pm.find(NS + "Style")
        if estilo is not None:
            ls, ps = estilo.find(NS + "LineStyle"), estilo.find(NS + "PolyStyle")
            if ls is not None:
                props["stroke"], props["stroke-opacity"] = _color(_texto(ls, "color"))
                try:
                    props["stroke-width"] = float(_texto(ls, "width") or 2)
                except ValueError:
                    props["stroke-width"] = 2
            if ps is not None:
                props["fill"], props["fill-opacity"] = _color(_texto(ps, "color"))
        geom = None
        pt = pm.find(NS + "Point")
        ln = pm.find(NS + "LineString")
        pg = pm.find(NS + "Polygon")
        if pt is not None:
            c = _coords(_texto(pt, "coordinates"))
            if c:
                geom = {"type": "Point", "coordinates": c[0]}
        elif ln is not None:
            geom = {"type": "LineString", "coordinates": _coords(_texto(ln, "coordinates"))}
        elif pg is not None:
            anillos = [_coords(_texto(lr, "coordinates")) for lr in pg.iter(NS + "LinearRing")]
            geom = {"type": "Polygon", "coordinates": anillos}
        if geom:
            feats.append({"type": "Feature", "properties": props, "geometry": geom})
    return {"type": "FeatureCollection", "features": feats}
