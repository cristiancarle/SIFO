"""Verificación: ejecuta todos los módulos con lat=-31.60 lon=-64.45."""
import json
import os
import sys
from datetime import date
from xml.dom import minidom

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app  # noqa: E402
from modulos.informe import ventana_operativa  # noqa: E402

print("import app OK")
r = app.analizar(-31.60, -64.45)
print("errores:", r["errores"])
t = r["topo"]
if t:
    print("topo: pend_max %.0f%% prom %.0f%% aspecto %.0f° cauces %d extensión %.0f m" % (
        t["pendiente_max"], t["pendiente_prom"], t["aspecto_grados"],
        len(t["red_de_cauces"]), t["extension_quebradas_m"]))
hoy = date.today().isoformat()
inf, kml, base = app.guardar_salidas(-31.60, -64.45, r, "Prueba Sierra", hoy, "Villa Carlos Paz")
print("base:", base)
minidom.parse(os.path.join(app.DIR_SALIDA, kml))
print("KML válido:", kml, "| informe:", inf)
for e in r["expansiones"]:
    print("%s: largo %.2f km ancho %.2f km rumbo %.0f° punta a %.2f km cauces %d vértices %d" % (
        e["nombre"], e["largo_m"] / 1000, e["ancho_max_m"] / 1000, e["rumbo_deg"],
        e["dist_foco_m"] / 1000, e["cauces_cruzan"], len(e["poligono"])))
doc = minidom.parse(os.path.join(app.DIR_SALIDA, kml))
nombres = [pm.getElementsByTagName("name")[0].firstChild.data
           for pm in doc.getElementsByTagName("Placemark") if pm.getElementsByTagName("Polygon")]
print("polígonos KML:", nombres)
assert len(nombres) == len(r["expansiones"]) == 3
for p in r["periodos"]:
    m, c = p["meteo"], p["comportamiento"]
    print("%s-%s T%.1f RH%.0f V%.0f dir%.0f ráf%.0f fm%.1f %s | carrera %.0f° %.2f km/h | sec %d | ventana %s" % (
        m["hora_inicio_str"], m["hora_fin_str"], m["temp_med"], m["rh_med"], m["viento_med_kmh"],
        m["viento_dir_med_deg"], m["rafaga_max_kmh"], p["fm"], p["riesgo"],
        c["direccion_carrera_primaria_deg"], c["velocidad_estimada_kmh"],
        len(c["lineas_carrera_secundaria"]), ventana_operativa(m)[:2]))

# Flujo completo: 2 incendios con metadatos distintos
r2 = app.analizar(-28.40, -65.80)
inf2, kml2, base2 = app.guardar_salidas(-28.40, -65.80, r2, "Prueba Ambato", "2026-10-20", "Catamarca")
assert base != base2
bases = {base, base2}
metas = {m["base"]: m for m in app.listar_metas()}
assert bases <= set(metas)
assert metas[base]["lugar"] == "Villa Carlos Paz" and metas[base2]["lugar"] == "Catamarca"
assert metas[base2]["fecha"] == "2026-10-20" and metas[base2]["lat"] == -28.40
gj = json.load(open(os.path.join(app.DIR_SALIDA, base + ".geojson"), encoding="utf-8"))
tipos = {f["geometry"]["type"] for f in gj["features"]}
print("GeoJSON válido: %d features, tipos %s" % (len(gj["features"]), sorted(tipos)))
assert {"Point", "LineString", "Polygon"} <= tipos

c = app.app.test_client()
NAVS = [b'href="/agregar"', b'href="/kml"', b'href="/informe"', b'href="/vistas"']
for ruta, esperado in [("/", b"Prueba Sierra"), ("/", b"Prueba Ambato"), ("/", b"Catamarca"), ("/", b"Ver KML"),
                       ("/agregar", b"Nombre del incendio"), ("/kml", b"Prueba Ambato"),
                       ("/informe", b"Prueba Sierra"), ("/vistas", b"Prueba Ambato"),
                       ("/incendios", None),
                       ("/ver/" + base, b"earth.google.com/web/"),
                       ("/salida/" + base + ".geojson", b"FeatureCollection"),
                       ("/salida/" + kml, b"<kml"), ("/salida/" + inf, b"Prueba Sierra")]:
    resp = c.get(ruta)
    if esperado is None:
        assert resp.status_code == 302, ruta
        continue
    assert resp.status_code == 200 and esperado in resp.data, ruta
    if ruta in ("/", "/kml", "/informe", "/vistas", "/ver/" + base):
        assert all(n in resp.data for n in NAVS), "nav " + ruta
    print("GET", ruta, "->", resp.status_code)
assert c.get("/ver/..%2Fapp").status_code == 404

# KML e informe por selección
resp = c.get("/kml?base=" + base2)
assert resp.status_code == 200 and b"Generar KML" in resp.data and b"/kml/" + base2.encode() in resp.data
p = os.path.join(app.DIR_SALIDA, kml2)
os.remove(p)
resp = c.post("/kml", data={"base": base2})
assert b"regenerado" in resp.data and os.path.isfile(p)
resp = c.get("/kml/%s/descargar" % base2)
assert resp.status_code == 200 and b"<kml" in resp.data and "attachment" in resp.headers["Content-Disposition"]
minidom.parseString(resp.data)
p = os.path.join(app.DIR_SALIDA, inf2)
os.remove(p)
resp = c.post("/informe", data={"base": base2})
assert b"regenerado" in resp.data and os.path.isfile(p) and b"Prueba Ambato" in open(p, encoding="utf-8").read().encode()
resp = c.get("/informe?base=" + base2)
assert b"Generar informe" in resp.data and b"Descargar informe" in resp.data
resp = c.get("/informe/%s/descargar" % base2)
assert resp.status_code == 200 and b"<html" in resp.data and "attachment" in resp.headers["Content-Disposition"]
html = open(os.path.join(app.DIR_SALIDA, inf), encoding="utf-8").read()
for txt in ["SIFO — Sistema Inteligente para Incendios Forestales", "Cristian N. Carle M.P. 2484 - +5493564508868",
            "position:fixed", "@media print", "Página 1 de 9", "marca-texto"]:
    assert txt in html, txt
assert html.count("class='pag-num'") == 9 and "Página 9 de 9" in html
home = c.get("/").get_data(as_text=True)
assert "🔥 SIFO" in home and "<title>Inicio · SIFO — Sistema Inteligente" in home
assert b"SIFO" in c.get("/agregar").data
print("Rebranding SIFO, encabezado y pie de informe OK")
assert c.post("/kml", data={"base": "../x"}).status_code == 404
print("KML e informe por selección OK")

# Eliminar uno
assert c.delete("/incendio/" + base2).get_json() == {"ok": True}
assert not [f for f in os.listdir(app.DIR_SALIDA) if base2 in f]
assert c.delete("/incendio/" + base2).status_code == 404
assert c.delete("/incendio/..%2Fapp").status_code == 404
resp = c.get("/")
assert b"Prueba Ambato" not in resp.data and b"Prueba Sierra" in resp.data
print("Eliminación OK; quedan:", [m["nombre"] for m in app.listar_metas() if m["base"] in bases])

# Estado vacío
import tempfile  # noqa: E402
orig = app.DIR_SALIDA
app.DIR_SALIDA = tempfile.mkdtemp()
for ruta in ("/", "/kml", "/informe", "/vistas"):
    assert "No hay incendios guardados. Agregá uno desde".encode() in c.get(ruta).data, ruta
app.DIR_SALIDA = orig
print("VERIFICACIÓN COMPLETA OK")
