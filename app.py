"""Servidor Flask de SIFO — Sistema Inteligente para Incendios Forestales."""
import glob
import json
import os
import re
import shutil
import subprocess
import unicodedata
from datetime import date, datetime
from urllib.parse import urlencode

from flask import Flask, abort, redirect, render_template_string, request, send_from_directory

from modulos.combustible import Combustible
from modulos.comportamiento import ComportamientoFuego, calcular_expansiones
from modulos.informe import generar_informe
from modulos.kml_gen import generar_kml
from modulos.kml_geojson import kml_a_geojson
from modulos.meteo import ErrorAPI, Meteorologia
from modulos.topografia import Topografia

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_STATIC = os.path.join(BASE, "static")
DIR_SALIDA = os.path.join(DIR_STATIC, "salida")
FUENTE = "Open-Meteo (meteorología) y OpenTopoData SRTM 90m (topografía)"

BASE_RE = re.compile(r"\d{8}_\d{6}_[A-Za-z0-9_]+")

app = Flask(__name__, static_folder=DIR_STATIC)

CSS = """
body{font-family:sans-serif;margin:0;padding-top:56px;background:#f4efe9;color:#222}
nav{position:fixed;top:0;left:0;right:0;z-index:2000;height:56px;box-sizing:border-box;background:#3b1a0a;padding:0 1em;
display:flex;align-items:center;gap:.3em;overflow-x:auto;box-shadow:0 2px 8px rgba(0,0,0,.4)}
nav a{color:#fff;padding:.5em .9em;font-weight:bold;text-decoration:none;border-radius:6px;white-space:nowrap}
nav .marca{color:#ffb27a;font-weight:bold;font-size:1.1em;margin-right:.8em;white-space:nowrap}
nav a:hover{background:#6b2a10}nav a.activo{background:#d9480f}
.wrap{max-width:1100px;margin:1em auto;padding:0 1em}
h1{color:#8a2a0a}table{border-collapse:collapse;width:100%;background:#fff}
th,td{border:1px solid #ddd;padding:.5em;text-align:left}th{background:#b33;color:#fff}
.btn{display:inline-block;padding:.5em .9em;background:#d9480f;color:#fff;border:0;border-radius:6px;text-decoration:none;
font-weight:bold;margin:.2em .3em .2em 0;font-size:1em;cursor:pointer}
.btn.peligro{background:#a61e1e}.btn.sec{background:#6b4a3a}
.aviso{padding:1em;background:#fff3cd;border-radius:6px}.ok{padding:1em;background:#e6f4e6;border-radius:6px}
.err{padding:1em;background:#fde8e8;border-radius:6px}
select{padding:.6em;font-size:1em;min-width:300px;max-width:100%}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1em}
.card{background:#fff;border-radius:10px;padding:1em;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.card h3{margin:.2em 0;color:#8a2a0a}.card iframe{height:220px;pointer-events:none}
#map{height:500px;border:1px solid #999;border-radius:6px;margin:1em 0}
iframe{width:100%;height:700px;border:1px solid #999;background:#fff}
"""
ITEMS_NAV = [("/", "Inicio"), ("/agregar", "Agregar"), ("/kml", "KML"), ("/informe", "Informe"), ("/vistas", "Vistas")]
NAV = ('<nav><span class="marca" title="SIFO — Sistema Inteligente para Incendios Forestales">🔥 SIFO</span>' + "".join(f'<a href="{h}"{{% if activo == "{h}" %}} class="activo"{{% endif %}}>{t}</a>'
                         for h, t in ITEMS_NAV) + '</nav>')
VACIO = '<p class="aviso">No hay incendios guardados. Agregá uno desde <a href="/agregar">AGREGAR</a>.</p>'
CABECERA = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{{ titulo }} · SIFO — Sistema Inteligente para Incendios Forestales</title>
<style>{{ css }}</style></head><body>""" + NAV + '<div class="wrap">'
PIE = "</div></body></html>"

SELECTOR = """<form method="get"><label for="base"><b>Incendio:</b></label>
<select id="base" name="base" onchange="this.form.submit()">
<option value="">— Elegí un incendio —</option>
{% for x in metas %}<option value="{{ x.base }}"{% if m and m.base == x.base %} selected{% endif %}>{{ x.nombre }} · {{ x.fecha }} · {{ x.lugar }}</option>
{% endfor %}</select> <noscript><button class="btn">Ver</button></noscript></form>"""

PLANTILLA_INICIO = CABECERA + """<h1>Incendios guardados</h1>
{% if msg %}<p class="ok">{{ msg }}</p>{% endif %}
{% if metas %}<table><tr><th>Nombre</th><th>Fecha del incidente</th><th>Lugar</th><th>Coordenadas</th><th>Hora de análisis</th><th>Acciones</th></tr>
{% for m in metas %}<tr><td>{{ m.nombre }}</td><td>{{ m.fecha }}</td><td>{{ m.lugar }}</td>
<td>{{ "%.5f"|format(m.lat) }}, {{ "%.5f"|format(m.lon) }}</td><td>{{ m.generado }}</td>
<td><a class="btn" href="/ver/{{ m.base }}">Ver KML</a>
<a class="btn sec" href="/salida/{{ m.informe }}" target="_blank">Ver informe</a>
<button class="btn peligro" data-base="{{ m.base }}" data-nombre="{{ m.nombre }}">Eliminar</button></td></tr>
{% endfor %}</table>""" + """{% else %}""" + VACIO + """{% endif %}
<script>
document.querySelectorAll("button[data-base]").forEach(b => b.addEventListener("click", async () => {
  if (!confirm("¿Eliminar el incendio '" + b.dataset.nombre + "' y todos sus archivos?")) return;
  const r = await fetch("/incendio/" + b.dataset.base, {method: "DELETE"});
  if (r.ok) location.href = "/?msg=" + encodeURIComponent("Incendio eliminado."); else alert("No se pudo eliminar.");
}));
</script>""" + PIE

PLANTILLA_KML = CABECERA + """<h1>KML</h1>""" + SELECTOR + """
{% if not metas %}""" + VACIO + """{% endif %}
{% if msg %}<p class="ok">{{ msg }}</p>{% endif %}{% if error %}<p class="err">{{ error }}</p>{% endif %}
{% if m %}<h2>{{ m.nombre }}</h2><p>{{ m.fecha }} · {{ m.lugar }}</p>
<p>{% if existe %}<a class="btn" href="/kml/{{ m.base }}/descargar">Descargar KML</a>
{% else %}<span class="aviso">El archivo KML no existe; generalo.</span>{% endif %}
<form method="post" action="/kml" style="display:inline"><input type="hidden" name="base" value="{{ m.base }}">
<button class="btn sec">Generar KML</button></form>
<a class="btn sec" href="/ver/{{ m.base }}">Ver en mapa</a></p>{% endif %}""" + PIE

PLANTILLA_INFORME = CABECERA + """<h1>Informe</h1>""" + SELECTOR + """
{% if not metas %}""" + VACIO + """{% endif %}
{% if msg %}<p class="ok">{{ msg }}</p>{% endif %}{% if error %}<p class="err">{{ error }}</p>{% endif %}
{% if m %}<h2>{{ m.nombre }}</h2><p>{{ m.fecha }} · {{ m.lugar }}</p>
<p>{% if existe %}<a class="btn" href="/informe/{{ m.base }}/pdf">Descargar informe (PDF)</a> <a class="btn" href="/informe/{{ m.base }}/descargar">Descargar HTML</a>{% else %}
<span class="aviso">El informe no existe; generalo.</span>{% endif %}
<form method="post" action="/informe" style="display:inline"><input type="hidden" name="base" value="{{ m.base }}">
<button class="btn sec">Generar informe</button></form></p>
{% if existe %}<iframe src="/salida/{{ m.informe }}" title="Informe"></iframe>{% endif %}{% endif %}""" + PIE

PLANTILLA_VISTAS = CABECERA + """<h1>Vistas de informes</h1>
{% if metas %}<div class="cards">{% for m in metas %}<div class="card"><h3>{{ m.nombre }}</h3>
<p>{{ m.fecha }} · {{ m.lugar }}</p><iframe src="/salida/{{ m.informe }}" title="Vista previa" loading="lazy"></iframe>
<p><a class="btn" href="/salida/{{ m.informe }}" target="_blank">Informe completo</a>
<a class="btn sec" href="/ver/{{ m.base }}">Mapa</a>
<a class="btn sec" href="/salida/{{ m.kml }}" download>KML</a></p></div>{% endfor %}</div>
{% else %}""" + VACIO + """{% endif %}""" + PIE

PLANTILLA_VER = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{{ m.nombre }} · SIFO — Sistema Inteligente para Incendios Forestales</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>{{ css }}</style></head><body>""" + NAV + """<div class="wrap">
<h1>{{ m.nombre }}</h1>
<p><b>Fecha del incidente:</b> {{ m.fecha }} &nbsp; <b>Lugar:</b> {{ m.lugar }} &nbsp;
<b>Coordenadas:</b> {{ "%.5f"|format(m.lat) }}, {{ "%.5f"|format(m.lon) }} &nbsp; <b>Generado:</b> {{ m.generado }}</p>
<p><a class="btn" href="/salida/{{ m.kml }}" download>Descargar KML</a>
<a class="btn" href="https://earth.google.com/web/" target="_blank" rel="noopener">Abrir en Google Earth</a>
<a class="btn" href="/salida/{{ m.informe }}" target="_blank">Informe en pestaña nueva</a></p>
<p><small>Google Earth: descargá el KML y, en Google Earth web, usá Proyectos &rarr; Importar archivo KML.</small></p>
<div id="map"></div>
<h2>Informe</h2><iframe src="/salida/{{ m.informe }}" title="Informe"></iframe></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map = L.map("map").setView([{{ m.lat }}, {{ m.lon }}], 13);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 19, attribution: "&copy; OpenStreetMap"}).addTo(map);
fetch("/salida/{{ m.geojson }}").then(r => r.json()).then(gj => {
  const capa = L.geoJSON(gj, {
    style: f => ({color: f.properties.stroke || "#3388ff", weight: f.properties["stroke-width"] || 2,
                  opacity: f.properties["stroke-opacity"] ?? 1, fillColor: f.properties.fill,
                  fillOpacity: f.properties["fill-opacity"] ?? 0.3}),
    onEachFeature: (f, l) => { const d = document.createElement("div");
      const b = document.createElement("b"); b.textContent = f.properties.name || "";
      d.append(b, document.createElement("br"), document.createTextNode(f.properties.description || ""));
      l.bindPopup(d); }
  }).addTo(map);
  if (capa.getBounds().isValid()) map.fitBounds(capa.getBounds());
});
</script></body></html>"""


def analizar(lat, lon):
    """Corre todos los módulos y devuelve el diccionario de resultados."""
    errores = []
    meteo = Meteorologia()
    comb = Combustible()
    comp = ComportamientoFuego()
    resultados = {"lat": lat, "lon": lon, "fuente": FUENTE, "errores": errores,
                  "periodos": [], "topo": None, "generado": ""}

    topo, barrancos = None, []
    try:
        t = Topografia()
        t.get_dem(lat, lon)
        topo = t.calcular()
        barrancos = t.identificar_barrancos()
    except ErrorAPI as e:
        errores.append(f"{e} Se continúa sin análisis topográfico.")
    resultados["topo"] = topo

    try:
        meteo.get_forecast(lat, lon)
        t0 = meteo.hora_local_actual()
        periodos = meteo.periodos(t0)
        resultados["generado"] = t0.strftime("%d/%m/%Y %H:%M (hora local)")
    except ErrorAPI as e:
        errores.append(str(e))
        resultados["generado"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        return resultados

    for m in periodos:
        fm = comb.humedad_muerta_1h(m["temp_med"], m["rh_med"])
        resultados["periodos"].append({
            "meteo": m, "fm": fm, "riesgo": comb.clasificar_riesgo(fm),
            "comportamiento": comp.analizar_periodo(lat, lon, m, topo, barrancos),
        })
    resultados["expansiones"] = calcular_expansiones(
        lat, lon, resultados["periodos"], topo["red_de_cauces"] if topo else None)
    return resultados


def slug(texto):
    """Nombre seguro para archivos: sin acentos, espacios ni caracteres raros."""
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")
    return t[:40] or "sin_nombre"


def guardar_salidas(lat, lon, resultados, nombre="", fecha="", lugar=""):
    """Escribe informe, KML, GeoJSON y metadatos en static/salida/; devuelve (informe, kml, base)."""
    os.makedirs(DIR_SALIDA, exist_ok=True)
    ahora = datetime.now()
    base = f"{ahora.strftime('%Y%m%d_%H%M%S')}_{slug(nombre)}"
    meta = {"nombre": nombre or "Sin nombre", "fecha": fecha, "lugar": lugar, "lat": lat, "lon": lon,
            "generado": ahora.strftime("%d/%m/%Y %H:%M:%S"), "base": base}
    informe, kml = f"informe_{base}.html", f"foco_{base}.kml"
    meta.update({"informe": informe, "kml": kml, "geojson": f"{base}.geojson", "datos": f"{base}_datos.json"})
    resultados["meta"] = meta
    with open(os.path.join(DIR_SALIDA, meta["datos"]), "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False)
    with open(os.path.join(DIR_SALIDA, f"{base}_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    regenerar(meta, "kml")
    regenerar(meta, "informe")
    return informe, kml, base


def _escribir(nombre, texto):
    with open(os.path.join(DIR_SALIDA, nombre), "w", encoding="utf-8") as f:
        f.write(texto)


def regenerar(meta, que):
    """Regenera 'kml' (más geojson) o 'informe' desde los datos guardados. False si faltan los datos."""
    ruta = os.path.join(DIR_SALIDA, meta.get("datos") or f"{meta['base']}_datos.json")
    if not os.path.isfile(ruta):
        return False
    with open(ruta, encoding="utf-8") as f:
        resultados = json.load(f)
    resultados["meta"] = meta
    if que == "kml":
        kml_txt = generar_kml(meta["lat"], meta["lon"], resultados)
        _escribir(meta["kml"], kml_txt)
        _escribir(meta["geojson"], json.dumps(kml_a_geojson(kml_txt), ensure_ascii=False))
    else:
        _escribir(meta["informe"], generar_informe(resultados))
    return True


def borrar_incendio(base):
    meta = leer_meta(base)
    if meta is None:
        return False
    nombres = {f"{base}_meta.json", f"{base}_datos.json", f"{base}.geojson"}
    nombres |= {meta.get(k) for k in ("informe", "kml", "geojson", "datos")} - {None}
    for n in nombres:
        ruta = os.path.join(DIR_SALIDA, os.path.basename(n))
        if os.path.isfile(ruta):
            os.remove(ruta)
    return True


def leer_meta(base):
    if not BASE_RE.fullmatch(base):
        return None
    ruta = os.path.join(DIR_SALIDA, f"{base}_meta.json")
    if not os.path.isfile(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def listar_metas():
    metas = []
    for ruta in glob.glob(os.path.join(DIR_SALIDA, "*_meta.json")):
        try:
            with open(ruta, encoding="utf-8") as f:
                metas.append(json.load(f))
        except (OSError, ValueError):
            continue
    return sorted(metas, key=lambda m: m.get("base", ""), reverse=True)


def pagina(plantilla, titulo, activo, **ctx):
    return render_template_string(plantilla, css=CSS, titulo=titulo, activo=activo, **ctx)


@app.route("/")
def index():
    return pagina(PLANTILLA_INICIO, "Inicio", "/", metas=listar_metas(), msg=request.args.get("msg", "")[:200])


@app.route("/agregar")
def agregar():
    return send_from_directory(DIR_STATIC, "index.html")


@app.route("/agregar", methods=["POST"])
@app.route("/analizar", methods=["POST"])
def ruta_analizar():
    try:
        lat = float(request.form["lat"].replace(",", "."))
        lon = float(request.form["lon"].replace(",", "."))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError
    except (KeyError, ValueError):
        msg = "Coordenadas inválidas: lat entre -90 y 90, lon entre -180 y 180."
        return redirect("/agregar?" + urlencode({"error": msg}))
    nombre = request.form.get("nombre", "").strip()[:100]
    fecha = request.form.get("fecha", "").strip()[:10] or date.today().isoformat()
    lugar = request.form.get("lugar", "").strip()[:150]
    resultados = analizar(lat, lon)
    _, _, base = guardar_salidas(lat, lon, resultados, nombre, fecha, lugar)
    return redirect("/?" + urlencode({"msg": f"Incendio '{nombre or 'Sin nombre'}' guardado correctamente."}))


@app.route("/incendios")
def historial():
    return redirect("/")


def _seleccion(plantilla, titulo, activo, clave, regen=None):
    """Página con selector de incendio; en POST regenera el archivo elegido."""
    base = request.values.get("base", "")
    m = leer_meta(base) if base else None
    msg = error = ""
    if request.method == "POST":
        if m is None:
            abort(404)
        if regenerar(m, regen):
            msg = "Archivo regenerado correctamente."
        else:
            error = "No hay datos guardados para regenerar este incendio."
    existe = bool(m) and os.path.isfile(os.path.join(DIR_SALIDA, m[clave]))
    return pagina(plantilla, titulo, activo, metas=listar_metas(), m=m, existe=existe, msg=msg, error=error)


@app.route("/kml", methods=["GET", "POST"])
def ruta_kml():
    return _seleccion(PLANTILLA_KML, "KML", "/kml", "kml", "kml")


@app.route("/informe", methods=["GET", "POST"])
def ruta_informe():
    return _seleccion(PLANTILLA_INFORME, "Informe", "/informe", "informe", "informe")


def _descarga(base, clave):
    meta = leer_meta(base)
    if meta is None or not os.path.isfile(os.path.join(DIR_SALIDA, meta[clave])):
        abort(404)
    return send_from_directory(DIR_SALIDA, meta[clave], as_attachment=True)


@app.route("/kml/<base>/descargar")
def descargar_kml(base):
    return _descarga(base, "kml")


@app.route("/informe/<base>/descargar")
def descargar_informe(base):
    return _descarga(base, "informe")


def _generar_pdf(base, meta):
    """Convierte el informe HTML a PDF con el motor de impresión de Chromium
    (respeta el salto de página por período, logo y pies). Cachear el resultado."""
    informe = meta.get("informe", "")
    html_path = os.path.join(DIR_SALIDA, informe)
    pdf_name = informe.rsplit(".", 1)[0] + ".pdf"
    pdf_path = os.path.join(DIR_SALIDA, pdf_name)
    if not os.path.isfile(pdf_path):
        chrome = shutil.which("chromium") or shutil.which("chromium-browser") \
                 or shutil.which("google-chrome")
        if not chrome:
            abort(500, "Chromium no está instalado en el servidor; no se puede generar PDF.")
        cmd = [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
               "--run-all-compositor-stages-before-draw",
               "--virtual-time-budget=15000",
               "--print-to-pdf=" + pdf_path, "--no-pdf-header-footer",
               "file://" + html_path]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        if r.returncode != 0 or not os.path.isfile(pdf_path):
            abort(500, "No se pudo generar el PDF.")
    return pdf_name


@app.route("/informe/<base>/pdf")
def descargar_informe_pdf(base):
    meta = leer_meta(base)
    if meta is None:
        abort(404)
    pdf_name = _generar_pdf(base, meta)
    return send_from_directory(DIR_SALIDA, pdf_name, as_attachment=True)


@app.route("/vistas")
def vistas():
    return pagina(PLANTILLA_VISTAS, "Vistas", "/vistas", metas=listar_metas())


@app.route("/incendio/<base>", methods=["DELETE"])
def eliminar(base):
    if not borrar_incendio(base):
        abort(404)
    return {"ok": True}


@app.route("/ver/<base>")
def ver(base):
    meta = leer_meta(base)
    if meta is None:
        abort(404)
    return render_template_string(PLANTILLA_VER, m=meta, css=CSS, activo="/")


@app.route("/salida/<path:archivo>")
def salida(archivo):
    if not os.path.isfile(os.path.join(DIR_SALIDA, archivo)):
        abort(404)
    return send_from_directory(DIR_SALIDA, archivo)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
