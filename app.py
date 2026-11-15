"""Servidor Flask de SIFO — Sistema Inteligente para Incendios Forestales."""
import glob
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
import unicodedata
from datetime import date, datetime, timedelta
from urllib.parse import urlencode, urlparse

from flask import (Flask, abort, g, redirect, render_template_string, request, send_from_directory,
                   session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix

from modulos import usuarios as U

from modulos.combustible import Combustible
from modulos.comportamiento import ComportamientoFuego, calcular_expansiones
from modulos.informe import generar_informe
from modulos.kml_gen import generar_kml
from modulos.kml_geojson import kml_a_geojson
from modulos.meteo import ErrorAPI, Meteorologia
from modulos.topografia import Topografia

BASE = os.path.dirname(os.path.abspath(__file__))
DIR_STATIC = os.path.join(BASE, "static")
DIR_SALIDA = os.environ.get("SIFO_DATA_DIR") or os.path.join(DIR_STATIC, "salida")
FUENTE = "Open-Meteo (meteorología) y OpenTopoData SRTM 90m (topografía)"

BASE_RE = re.compile(r"\d{8}_\d{6}_[A-Za-z0-9_]+")

# static_folder=None: nada se sirve sin pasar por el control de login.
app = Flask(__name__, static_folder=None)

# --- Configuración por variables de entorno -------------------------------
PRODUCCION = os.environ.get("SIFO_PRODUCCION", "0") == "1"
app.secret_key = os.environ.get("SIFO_SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=PRODUCCION,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    MAX_CONTENT_LENGTH=64 * 1024,
)
if PRODUCCION:
    # Detrás del proxy HTTPS del hosting (Render, Railway, Fly...).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Cuenta de administrador inicial (se crea/actualiza al arrancar). Los demás usuarios se registran
# desde /registro y quedan pendientes hasta que un admin los aprueba en /usuarios.
U.iniciar_db(os.environ.get("SIFO_ADMIN_USUARIO", ""), os.environ.get("SIFO_ADMIN_CLAVE", ""),
             os.environ.get("SIFO_ADMIN_CLAVE_HASH", ""))
REGISTRO_ABIERTO = os.environ.get("SIFO_REGISTRO", "1") == "1"

# Freno a fuerza bruta: 5 intentos fallidos por IP -> bloqueo de 15 minutos (login y registro).
MAX_INTENTOS, BLOQUEO_SEG = 5, 15 * 60
_intentos = {}
_intentos_lock = threading.Lock()
PUBLICAS = {"login", "registro", "healthz"}

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
                         for h, t in ITEMS_NAV) +
       '{% if usuario_actual and usuario_actual.rol == "admin" %}<a href="/usuarios"{% if activo == "/usuarios" %} class="activo"{% endif %}>Usuarios</a>{% endif %}'
       '<a href="/cuenta" style="margin-left:auto"{% if activo == "/cuenta" %} class="activo"{% endif %}>👤 {{ usuario_actual.usuario if usuario_actual }}</a>'
       '<form method="post" action="/logout"><button class="btn sec">Salir</button></form></nav>')
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

ESTILO_ACCESO = """body{font-family:sans-serif;background:linear-gradient(#3b1a0a,#b33a12);min-height:100vh;margin:0;
display:flex;align-items:center;justify-content:center}main{background:#fff;padding:2em;border-radius:12px;
max-width:400px;width:90%;box-shadow:0 6px 24px rgba(0,0,0,.4);margin:2em 0}h1{color:#8a2a0a;margin:.2em 0 0;font-size:1.6em}
p.sub{color:#6b4a3a;margin:.2em 0 1.2em}label{display:block;margin:.8em 0 .2em;font-weight:bold}
input{width:100%;padding:.6em;font-size:1em;box-sizing:border-box}button{margin-top:1.2em;width:100%;padding:.8em;
font-size:1.1em;font-weight:bold;background:#d9480f;color:#fff;border:0;border-radius:6px;cursor:pointer}
.err{padding:.8em;background:#fde8e8;border-radius:6px;margin-top:1em}.ok{padding:.8em;background:#e6f4e6;border-radius:6px;margin-top:1em}
.alt{text-align:center;margin-top:1.2em}a{color:#8a2a0a;font-weight:bold}small{color:#6b4a3a}"""

PLANTILLA_LOGIN = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Ingresar · SIFO</title>
<style>{{ estilo }}</style></head><body><main>
<h1>🔥 SIFO</h1><p class="sub">Sistema Inteligente para Incendios Forestales</p>
{% if msg %}<p class="ok">{{ msg }}</p>{% endif %}
<form method="post"><input type="hidden" name="siguiente" value="{{ siguiente }}">
<label for="u">Usuario</label><input id="u" name="usuario" autocomplete="username" required autofocus>
<label for="c">Contraseña</label><input id="c" name="clave" type="password" autocomplete="current-password" required>
<button>Ingresar</button></form>{% if error %}<p class="err">{{ error }}</p>{% endif %}
{% if registro %}<p class="alt">¿No tenés cuenta? <a href="/registro">Registrate</a></p>{% endif %}</main></body></html>"""

PLANTILLA_REGISTRO = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Registro · SIFO</title>
<style>{{ estilo }}</style></head><body><main>
<h1>🔥 SIFO</h1><p class="sub">Solicitud de cuenta</p>
{% if errores %}<div class="err">{% for e in errores %}<div>{{ e }}</div>{% endfor %}</div>{% endif %}
<form method="post">
<label for="n">Nombre y apellido</label><input id="n" name="nombre" value="{{ f.nombre }}" maxlength="100" required autofocus>
<label for="e">Email</label><input id="e" name="email" type="email" value="{{ f.email }}" maxlength="150" required>
<label for="u">Usuario</label><input id="u" name="usuario" value="{{ f.usuario }}" autocomplete="username"
 pattern="[A-Za-z0-9_.\\-]{3,30}" required>
<label for="c">Contraseña <small>(mínimo {{ minimo }} caracteres)</small></label>
<input id="c" name="clave" type="password" minlength="{{ minimo }}" autocomplete="new-password" required>
<label for="c2">Repetir contraseña</label>
<input id="c2" name="clave2" type="password" minlength="{{ minimo }}" autocomplete="new-password" required>
<button>Solicitar cuenta</button></form>
<p class="alt"><small>Tu cuenta quedará pendiente hasta que un administrador la apruebe.</small><br><br>
¿Ya tenés cuenta? <a href="/login">Ingresá</a></p></main></body></html>"""


def _ip():
    return request.remote_addr or "?"


def _bloqueado(clave):
    with _intentos_lock:
        n, desde = _intentos.get(clave, (0, 0))
        if n >= MAX_INTENTOS and time.time() - desde < BLOQUEO_SEG:
            return True
        if n >= MAX_INTENTOS:
            _intentos.pop(clave, None)
        return False


def _sumar_intento(clave):
    with _intentos_lock:
        n, desde = _intentos.get(clave, (0, time.time()))
        _intentos[clave] = (n + 1, time.time() if n + 1 >= MAX_INTENTOS else desde)


def _siguiente_seguro(url):
    """Solo rutas internas (evita open redirect)."""
    p = urlparse(url or "")
    return url if url and not p.scheme and not p.netloc and url.startswith("/") and not url.startswith("//") else "/"


def _mismo_origen():
    """Defensa CSRF extra (además de SameSite=Lax): los POST/DELETE deben venir de este mismo sitio."""
    origen = request.headers.get("Origin")
    if origen and urlparse(origen).netloc != request.host:
        abort(403)


@app.before_request
def control_acceso():
    g.usuario = None
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        _mismo_origen()
    uid = session.get("uid")
    if uid:
        u = U.obtener(uid)
        if u is not None and u["estado"] == "activo":
            g.usuario = u
        else:
            session.clear()  # desactivado o eliminado: se cierra su sesión
    if request.endpoint in PUBLICAS or g.usuario is not None:
        return None
    if request.method == "GET":
        return redirect(url_for("login", siguiente=request.full_path.rstrip("?")))
    abort(401)


def solo_admin():
    if g.usuario is None or g.usuario["rol"] != "admin":
        abort(403)


@app.context_processor
def contexto_usuario():
    return {"usuario_actual": g.get("usuario")}


@app.after_request
def cabeceras_seguridad(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    # OSM exige Referer con el origen para servir los mosaicos del mapa.
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if PRODUCCION:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return resp


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario is not None:
        return redirect("/")
    siguiente = _siguiente_seguro(request.values.get("siguiente", "/"))
    error, codigo = "", 200
    if request.method == "POST":
        ip = "login:" + _ip()
        if _bloqueado(ip):
            error, codigo = "Demasiados intentos fallidos. Probá de nuevo en 15 minutos.", 429
        else:
            u, motivo = U.autenticar(request.form.get("usuario", "").strip(), request.form.get("clave", ""))
            if u is not None:
                with _intentos_lock:
                    _intentos.pop(ip, None)
                session.clear()
                session.permanent = True
                session["uid"] = u["id"]
                return redirect(siguiente)
            codigo = 401
            if motivo == "pendiente":
                error = "Tu cuenta todavía no fue aprobada por un administrador."
            elif motivo == "inactivo":
                error = "Tu cuenta está desactivada. Contactá a un administrador."
            else:
                _sumar_intento(ip)
                app.logger.warning("SIFO: login fallido desde %s", _ip())
                error = "Usuario o contraseña incorrectos."
    return render_template_string(PLANTILLA_LOGIN, estilo=ESTILO_ACCESO, siguiente=siguiente, error=error,
                                  msg=request.args.get("msg", "")[:200], registro=REGISTRO_ABIERTO), codigo


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if not REGISTRO_ABIERTO:
        abort(404)
    f = {k: request.form.get(k, "").strip() for k in ("usuario", "nombre", "email")}
    errores = []
    if request.method == "POST":
        ip = "registro:" + _ip()
        if _bloqueado(ip):
            errores = ["Demasiadas solicitudes desde tu conexión. Probá de nuevo más tarde."]
        else:
            errores = U.validar_registro(f["usuario"], f["nombre"], f["email"],
                                         request.form.get("clave", ""), request.form.get("clave2", ""))
            if not errores:
                _sumar_intento(ip)  # máx. 5 registros por IP cada 15 min
                if U.registrar(f["usuario"], f["nombre"], f["email"], request.form["clave"]):
                    app.logger.info("SIFO: nuevo registro pendiente: %s", f["usuario"])
                    return redirect(url_for("login", msg="Solicitud enviada. Vas a poder ingresar cuando un "
                                                          "administrador apruebe tu cuenta."))
                errores = ["Ese nombre de usuario ya está en uso."]
    return render_template_string(PLANTILLA_REGISTRO, estilo=ESTILO_ACCESO, errores=errores, f=f,
                                  minimo=U.CLAVE_MIN), (400 if errores else 200)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/healthz")
def healthz():
    return {"ok": True}


PLANTILLA_USUARIOS = CABECERA + """<h1>Usuarios</h1>
{% if msg %}<p class="ok">{{ msg }}</p>{% endif %}{% if error %}<p class="err">{{ error }}</p>{% endif %}
<table><tr><th>Usuario</th><th>Nombre</th><th>Email</th><th>Rol</th><th>Estado</th><th>Registro</th><th>Último ingreso</th><th>Acciones</th></tr>
{% for u in lista %}<tr><td>{{ u.usuario }}</td><td>{{ u.nombre }}</td><td>{{ u.email }}</td><td>{{ u.rol }}</td>
<td>{% if u.estado == "pendiente" %}<b style="color:#a61e1e">pendiente</b>{% else %}{{ u.estado }}{% endif %}</td>
<td>{{ u.creado }}</td><td>{{ u.ultimo_login or "—" }}</td><td>
{% if u.id != usuario_actual.id %}<form method="post" style="display:inline"><input type="hidden" name="uid" value="{{ u.id }}">
{% if u.estado != "activo" %}<button class="btn" name="accion" value="aprobar">{{ "Aprobar" if u.estado == "pendiente" else "Activar" }}</button>
{% else %}<button class="btn sec" name="accion" value="desactivar">Desactivar</button>{% endif %}
{% if u.rol == "admin" %}<button class="btn sec" name="accion" value="quitar_admin">Quitar admin</button>
{% else %}<button class="btn sec" name="accion" value="hacer_admin">Hacer admin</button>{% endif %}
<button class="btn peligro" name="accion" value="eliminar" onclick="return confirm('¿Eliminar al usuario {{ u.usuario }}?')">Eliminar</button>
</form>{% else %}<small>(vos)</small>{% endif %}</td></tr>{% endfor %}</table>""" + PIE

PLANTILLA_CUENTA = CABECERA + """<h1>Mi cuenta</h1>
<p><b>Usuario:</b> {{ usuario_actual.usuario }} &nbsp; <b>Nombre:</b> {{ usuario_actual.nombre }} &nbsp;
<b>Email:</b> {{ usuario_actual.email or "—" }} &nbsp; <b>Rol:</b> {{ usuario_actual.rol }}</p>
<h2>Cambiar contraseña</h2>
{% if msg %}<p class="ok">{{ msg }}</p>{% endif %}{% if error %}<p class="err">{{ error }}</p>{% endif %}
<form method="post" style="max-width:400px">
<p><label>Contraseña actual<br><input name="actual" type="password" autocomplete="current-password" required style="width:100%;padding:.5em"></label></p>
<p><label>Contraseña nueva (mín. {{ minimo }})<br><input name="nueva" type="password" minlength="{{ minimo }}" autocomplete="new-password" required style="width:100%;padding:.5em"></label></p>
<button class="btn">Guardar</button></form>""" + PIE


@app.route("/usuarios", methods=["GET", "POST"])
def admin_usuarios():
    solo_admin()
    msg = error = ""
    if request.method == "POST":
        try:
            uid = int(request.form.get("uid", ""))
        except ValueError:
            abort(400)
        u, accion = U.obtener(uid), request.form.get("accion", "")
        if u is None:
            abort(404)
        if uid == g.usuario["id"]:
            error = "No podés modificar tu propia cuenta desde acá."
        elif (accion in ("desactivar", "quitar_admin", "eliminar") and u["rol"] == "admin"
              and u["estado"] == "activo" and U.cantidad_admins_activos() <= 1):
            error = "Debe quedar al menos un administrador activo."
        elif accion == "aprobar":
            U.cambiar_estado(uid, "activo"); msg = f"Usuario {u['usuario']} activado."
        elif accion == "desactivar":
            U.cambiar_estado(uid, "inactivo"); msg = f"Usuario {u['usuario']} desactivado."
        elif accion == "hacer_admin":
            U.cambiar_rol(uid, "admin"); msg = f"{u['usuario']} ahora es administrador."
        elif accion == "quitar_admin":
            U.cambiar_rol(uid, "usuario"); msg = f"{u['usuario']} ya no es administrador."
        elif accion == "eliminar":
            U.eliminar(uid); msg = f"Usuario {u['usuario']} eliminado."
        else:
            abort(400)
    return pagina(PLANTILLA_USUARIOS, "Usuarios", "/usuarios", lista=U.listar(), msg=msg, error=error)


@app.route("/cuenta", methods=["GET", "POST"])
def cuenta():
    msg = error = ""
    if request.method == "POST":
        error = U.cambiar_clave(g.usuario["id"], request.form.get("actual", ""), request.form.get("nueva", ""))
        msg = "" if error else "Contraseña actualizada."
    return pagina(PLANTILLA_CUENTA, "Mi cuenta", "/cuenta", msg=msg, error=error, minimo=U.CLAVE_MIN)


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
        if meteo.aviso():
            errores.append(meteo.aviso())
        if meteo.fuente() != "Open-Meteo":
            resultados["fuente"] = FUENTE.replace("Open-Meteo", meteo.fuente())
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
    # Solo para desarrollo local; en producción se usa gunicorn (ver Dockerfile).
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")))
