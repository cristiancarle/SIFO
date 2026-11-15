"""Informe HTML de trabajo: 8 períodos con orden de trabajo y ventana de entrada/salida."""
import base64
import os
from html import escape

from .combustible import Combustible

RAFAGA_MAX_OPERABLE = 40.0
FM_MIN_OPERABLE = 10.0
VIENTO_MAX_QUEBRADA = 20.0
PUNTOS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
          "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]
_comb = Combustible()


def rumbo_texto(grados):
    return PUNTOS[int((grados % 360) / 22.5 + 0.5) % 16]


def _hora_operable(h):
    fm = _comb.humedad_muerta_1h(h["temp"] or 0, h["rh"] if h["rh"] is not None else 50)
    return (h["rafaga"] or 0) < RAFAGA_MAX_OPERABLE and fm >= FM_MIN_OPERABLE


def _sumar_hora(hhmm):
    return f"{(int(hhmm[:2]) + 1) % 24:02d}:00"


def ventana_operativa(meteo):
    """(entrada, salida, motivo) según las horas del período; entrada=None si no se puede operar."""
    horas = meteo["horario"]
    ok = [_hora_operable(h) for h in horas]
    if not any(ok):
        return None, None, "Ráfagas ≥ 40 km/h o combustible en condición extrema durante todo el período."
    i = ok.index(True)
    j = i
    while j + 1 < len(horas) and ok[j + 1]:
        j += 1
    entrada = horas[i]["hora_str"]
    cierra = j == len(horas) - 1
    salida = meteo["hora_fin_str"] if cierra else _sumar_hora(horas[j]["hora_str"])
    if cierra and i == 0:
        motivo = "Condiciones aptas durante todo el período; salir al cierre de la ventana."
    else:
        motivo = "Las condiciones se agravan fuera de este tramo; respetar la hora de salida."
    return entrada, salida, motivo


def _quebrada_segura(meteo, fm):
    return (meteo["viento_med_kmh"] < VIENTO_MAX_QUEBRADA
            and meteo["rafaga_max_kmh"] < RAFAGA_MAX_OPERABLE and fm >= FM_MIN_OPERABLE)


def _bloque(p):
    m, c = p["meteo"], p["comportamiento"]
    fm, riesgo = p["fm"], p["riesgo"]
    entrada, salida, motivo = ventana_operativa(m)
    if entrada:
        rec = (f"<p class='ok'><b>HORA DE ENTRADA: {entrada}</b> &nbsp; "
               f"<b>HORA DE SALIDA: {salida}</b></p><p>{escape(motivo)}</p>")
        if not _quebrada_segura(m, fm):
            rec += "<p class='mal'>Trabajar FUERA de las quebradas (viento fuerte o combustible extremo).</p>"
    else:
        rec = f"<p class='mal'><b>NO OPERAR EN ESTE PERÍODO.</b> {escape(motivo)}</p>"
    if 12 <= int(m["hora_inicio_str"][:2]) <= 16:
        rec += "<p>Período de pico típico de viento y calor (12-17 hs): extremar precauciones.</p>"
    if m["precip_mm"] > 0.2:
        rec += f"<p>Precipitación prevista: {m['precip_mm']:.1f} mm; terreno resbaladizo.</p>"

    prim = "".join(
        f"<li>{'Principal' if l['tipo'] == 'principal' else 'Flanco'}: hacia {l['rumbo']:.0f}° "
        f"({rumbo_texto(l['rumbo'])}), extensión {l['extension_m']:.0f} m</li>"
        for l in c["lineas_carrera_primaria"])
    ladera = "cuesta arriba" if c["fuego_sube_ladera"] else "con el viento / cuesta abajo"
    if c["lineas_carrera_secundaria"]:
        sec = "".join(
            f"<li>Quebrada a {s['distancia_foco_m']:.0f} m del foco: {s['velocidad_kmh']:.2f} km/h, "
            f"alcance {s['alcance_m']:.0f} m en el período</li>" for s in c["lineas_carrera_secundaria"])
        reglas = "".join(f"<li>{escape(r)}</li>" for r in c["reglas_quebrada"])
        sec = f"<ul>{sec}</ul><div class='adv'><b>⚠ ADVERTENCIA DE SEGURIDAD:</b><ul>{reglas}</ul></div>"
    else:
        sec = "<p>No se detectaron quebradas en el área analizada.</p>"

    return f"""
<section class="periodo">
<h2>PERÍODO {m['inicio_h']}-{m['fin_h']} hs (t0+{m['inicio_h']}) — ORDEN DE TRABAJO</h2>
<p class="ventana">VENTANA: {m['hora_inicio_str']} - {m['hora_fin_str']} ({m['fecha_inicio']})</p>
<h3>Meteorología</h3>
<p>Temperatura {m['temp_med']:.1f} °C · HR {m['rh_med']:.0f}% · Viento {m['viento_med_kmh']:.0f} km/h
desde {m['viento_dir_med_deg']:.0f}° ({rumbo_texto(m['viento_dir_med_deg'])}) ·
Ráfaga máx. {m['rafaga_max_kmh']:.0f} km/h · Precipitación {m['precip_mm']:.1f} mm · Nubes {m['nubes']:.0f}%</p>
<h3>Humedad del combustible</h3>
<p>FM 1h: <b>{fm:.1f}%</b> — {escape(riesgo)}</p>
<h3>Carreras primarias esperadas</h3>
<p>Dirección {c['direccion_carrera_primaria_deg']:.0f}° ({rumbo_texto(c['direccion_carrera_primaria_deg'])}),
corre {ladera}, velocidad estimada {c['velocidad_estimada_kmh']:.2f} km/h.</p><ul>{prim}</ul>
<h3>Carreras secundarias en quebradas</h3>{sec}
<h3>RECOMENDACIÓN OPERATIVA</h3>{rec}
</section>"""


def _bloque_expansion(e, topo):
    if topo:
        if e["cauces_cruzan"]:
            q = (f"<b>Incluye quebradas:</b> {e['cauces_cruzan']} cauce(s) cruzan el polígono; "
                 "riesgo de carrera secundaria y focos por pavesas.")
        else:
            q = "No se detectaron quebradas dentro del polígono."
    else:
        q = "Quebradas: sin datos de topografía."
    ladera = "con tramos cuesta arriba" if e["sube_ladera"] else "sin empuje de ladera relevante"
    return (f"<div class='exp exp-{e['clave']}'><h3>{escape(e['nombre'])}</h3>"
            f"<p>Extensión máxima: <b>{e['largo_m'] / 1000:.2f} km</b> (ancho máx. {e['ancho_max_m'] / 1000:.2f} km), "
            f"dirección {e['rumbo_deg']:.0f}° ({rumbo_texto(e['rumbo_deg'])}); la punta queda a "
            f"{e['dist_foco_m'] / 1000:.2f} km del foco hacia el {rumbo_texto(e['rumbo_foco_deg'])}.</p>"
            f"<p>Zona abarcada: viento hasta {e['viento_max_kmh']:.0f} km/h, humedad del combustible mín. "
            f"{e['fm_min']:.1f}%, velocidad media {e['velocidad_media_kmh']:.2f} km/h, {ladera}.</p>"
            f"<p>{q}</p></div>")


NOMBRE_SIFO = "SIFO — Sistema Inteligente para Incendios Forestales"
PIE_AUTOR = "Cristian N. Carle M.P. 2484 - +5493564508868"


def _tabla_velocidades(resultados):
    """Tabla resumen de velocidades de propagación por período (cada período = 3 hs)."""
    p = resultados.get("periodos", [])
    if not p:
        return ""
    filas, vel = [], []
    for i, x in enumerate(p):
        m, c = x.get("meteo", {}), x.get("comportamiento", {})
        ventana = f"{m.get('hora_inicio_str','')} - {m.get('hora_fin_str','')}"
        v = float(c.get("velocidad_estimada_kmh", 0.0))
        dir_deg = c.get("direccion_carrera_primaria_deg")
        dir_txt = f"{dir_deg:.0f}° ({rumbo_texto(dir_deg)})" if dir_deg is not None else ""
        vel.append(v)
        if v < 0.6:
            obs = "Muy lenta — ideal para líneas de defensa y contrafuego"
        elif v < 0.9:
            obs = "Lenta/moderada — ventana útil de trabajo"
        elif v < 1.1:
            obs = "Moderada — trabajar solo con control"
        else:
            obs = "Rápida — NO OPERAR en frentes ni quebradas"
        filas.append(f"<tr><td>+{i*3}</td><td>{ventana}</td>"
                     f"<td>{v:.2f} km/h</td><td>{v*1000/60:.0f} m/min</td>"
                     f"<td>{dir_txt}</td><td>{obs}</td></tr>")
    vmax = max(vel) if vel else 0
    dist24 = sum(v * 3 for v in vel)
    nota = (f"<p><b>Máxima del día:</b> {vmax:.2f} km/h ({vmax*1000/60:.0f} m/min). "
            f"<b>Distancia total de carrera en 24 hs:</b> {dist24:.1f} km. "
            f"En quebradas con encauzamiento aplicar factor 1,3x.</p>")
    return ("<section class='periodo'><h2>VELOCIDADES DE PROPAGACIÓN APROXIMADAS</h2>"
            "<table class='tabla-vel'><thead><tr><th>Período</th><th>Ventana</th>"
            "<th>Velocidad</th><th>m/min</th><th>Dirección</th><th>Lectura operativa</th></tr></thead>"
            "<tbody>" + "".join(filas) + "</tbody></table>" + nota + "</section>")
RUTA_LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "static", "img", "logo.png")
LLAMA_SVG = ('<svg class="llama" viewBox="0 0 24 32" width="34" height="44" aria-hidden="true">'
             '<path d="M12 1c1 6-6 9-6 18a8 8 0 0 0 16 0c0-5-3-7-4-11-1 3-3 4-3 4 1-4 0-8-3-11z" fill="#d9480f"/>'
             '<path d="M12 15c1 3-3 4-3 8a3 3 0 0 0 6 0c0-3-2-4-3-8z" fill="#ffd43b"/></svg>')


def _cabecera_sifo():
    """Logo embebido (data URI) si static/img/logo.png existe; si no, texto SIFO con llama SVG."""
    try:
        with open(RUTA_LOGO, "rb") as f:
            uri = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
        marca = f'<img class="logo" src="{uri}" alt="SIFO">'
    except OSError:
        marca = f'<div class="marca-texto">{LLAMA_SVG}<span>SIFO</span></div>'
    return f'<header class="cab-sifo">{marca}<div class="cab-titulo">{NOMBRE_SIFO}</div></header>'


def _paginar(bloques):
    """Cada <section class='periodo'> es una página impresa; al final de cada bloque va
    el pie completo: autor a la izquierda y 'Página N de M' a la derecha (siempre visibles)."""
    partes = bloques.split("</section>")
    total = len(partes) - 1
    if total < 1:
        return bloques, 1
    pie = (f"<div class='pie-periodo'>"
           f"<span class='pie-autor'>{PIE_AUTOR}</span>"
           f"<span class='pie-pagina'>Página {{}} de {total}</span></div>")
    sal = "".join(f"{p}{pie.format(i)}</section>"
                  for i, p in enumerate(partes[:-1], 1))
    return sal + partes[-1], total


def generar_informe(resultados):
    errores = "".join(f"<li>{escape(e)}</li>" for e in resultados.get("errores", []))
    cab_err = f"<div class='mal'><h3>Avisos y errores</h3><ul>{errores}</ul></div>" if errores else ""
    topo = resultados.get("topo")
    if topo:
        txt_topo = (f"Pendiente máx. {topo['pendiente_max']:.0f}% · prom. {topo['pendiente_prom']:.0f}% · "
                    f"orientación dominante {topo['aspecto_grados']:.0f}° ({rumbo_texto(topo['aspecto_grados'])}) · "
                    f"quebradas: {topo['extension_quebradas_m']:.0f} m en {len(topo['red_de_cauces'])} cauces")
    else:
        txt_topo = "Topografía no disponible (ver avisos)."
    bloques = "".join(_bloque(p) for p in resultados.get("periodos", []))
    bloques += _tabla_velocidades(resultados)
    if bloques and resultados.get("expansiones"):
        bloques += ("<section class='periodo'><h2>POSIBLES EXPANSIONES DEL INCENDIO</h2>"
                    + "".join(_bloque_expansion(e, topo) for e in resultados["expansiones"])
                    + "</section>")
    if not bloques:
        bloques = "<p class='mal'>No se pudo generar el informe por períodos: faltan datos meteorológicos.</p>"
    bloques, total_pag = _paginar(bloques)
    meta = resultados.get("meta") or {}
    ident = ""
    if meta.get("nombre"):
        ident = (f"<p><b>Incendio:</b> {escape(meta['nombre'])}<br>"
                 f"<b>Fecha del incidente:</b> {escape(meta.get('fecha', ''))}<br>"
                 f"<b>Lugar:</b> {escape(meta.get('lugar', ''))}</p>")
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Informe de trabajo — {NOMBRE_SIFO}</title>
<style>
body{{font-family:sans-serif;max-width:900px;margin:1em auto;padding:0 1em;color:#222}}
.periodo{{border:2px solid #b33;border-radius:8px;padding:0 1em 1em;margin:1em 0}}
h2{{background:#b33;color:#fff;margin:0 -1em;padding:.4em 1em;border-radius:6px 6px 0 0}}
.ventana{{font-size:1.2em;font-weight:bold}}
.ok{{background:#e6f4e6;padding:.5em}} .mal{{background:#fde8e8;padding:.5em}}
.exp{{border-left:8px solid;padding:0 .8em;margin:.6em 0}}
.exp-inmediata{{border-color:#f00}} .exp-9hs{{border-color:#f80}} .exp-24hs{{border-color:#fc0}}
.adv{{background:#fff3cd;padding:.5em;border-left:4px solid #f90}}
.cab-sifo{{display:flex;flex-direction:column;align-items:center;text-align:center;border-bottom:3px solid #d9480f;padding-bottom:.5em;margin-bottom:.5em}}
.cab-sifo .logo{{max-height:90px;max-width:100%}}
.marca-texto{{display:flex;align-items:center;gap:.4em;font-size:2.2em;font-weight:900;letter-spacing:.15em;color:#8a2a0a}}
.cab-titulo{{font-size:1.15em;font-weight:bold;color:#3b1a0a}}
.pag-num{{text-align:right;font-size:.85em;color:#555;margin-top:.8em}}
.pie-periodo{{display:flex;justify-content:space-between;align-items:flex-end;border-top:2px solid #d9480f;margin-top:1em;padding-top:.4em;font-size:.85em;color:#222;gap:1em}}
.pie-periodo .pie-autor{{font-weight:bold}}
.pie-periodo .pie-pagina{{white-space:nowrap}}
.pie-sifo{{display:flex;justify-content:space-between;border-top:1px solid #999;margin-top:1em;padding-top:.4em;font-size:.85em;color:#444}}
@media print{{
@page{{size:A4;margin:1.2cm 1.2cm 1.5cm}}
.nav-inf{{display:none}}
body{{margin:0;max-width:none;font-size:0.92em}}
.periodo{{page-break-after:always;break-after:page;page-break-inside:avoid;break-inside:avoid;margin-top:0}}
.periodo:last-of-type{{page-break-after:auto;break-after:auto}}
.pie-sifo{{display:none}}
.periodo{{display:flex;flex-direction:column;min-height:24.6cm;padding:0 .2em;break-after:page}}
.periodo p{{margin:.16em 0;line-height:1.28}}
.periodo h3,.periodo h4{{margin:.35em 0 .2em}}
.periodo h2{{margin:.15em 0 .25em;font-size:1.12em}}
.periodo h3{{margin:.3em 0 .2em;font-size:1em}}
.periodo table,.tabla-vel{{font-size:.85em;line-height:1.2}}
.periodo table td,.periodo table th,.tabla-vel td,.tabla-vel th{{padding:.18em .4em}}
.periodo ul,.periodo li{{margin:.08em 0}}
.pie-periodo{{display:flex;justify-content:space-between;align-items:flex-end;gap:1em;margin-top:auto;padding-top:.35em}}
.pag-num{{margin-top:auto;font-weight:bold}}
}}
</style></head><body>
<p class="nav-inf"><a href="/" target="_top">Inicio</a> | <a href="/incendios" target="_top">Historial de incendios</a></p>
{_cabecera_sifo()}
<h1>INFORME DE TRABAJO — PRÓXIMAS 24 HS</h1>
{ident}<p><b>Coordenadas:</b> {resultados['lat']:.5f}, {resultados['lon']:.5f}<br>
<b>Generado (t0):</b> {escape(resultados['generado'])}<br>
<b>Fuente de datos:</b> {escape(resultados['fuente'])}<br>
<b>Topografía:</b> {txt_topo}</p>
{cab_err}{bloques}
<p><small>Estimaciones simplificadas (tipo BEHAVE); no reemplazan el criterio del jefe de operaciones.</small></p>
<footer class="pie-sifo"><span>{PIE_AUTOR}</span><span class="pie-der">{total_pag} página(s) — cada período = una página impresa</span></footer>
<script>
/* Ajustador: si un bloque excede la altura útil de la hoja, lo escala para que
   el pie SIEMPRE quede adentro, sin importar la cantidad de contenido. */
(function () {{
  var ALTO_UTIL = 1000; // px ~= area util A4 (26 cm)
  function ajustar() {{
    var bs = document.querySelectorAll(".periodo");
    for (var i = 0; i < bs.length; i++) {{
      var b = bs[i];
      b.style.zoom = "1";
      var h = b.scrollHeight, intentos = 0, z = 1;
      while (h > ALTO_UTIL && intentos < 25 && z > 0.56) {{
        z = Math.max(0.55, ALTO_UTIL / h);
        b.style.zoom = z;
        h = b.scrollHeight;
        intentos++;
      }}
    }}
  }}
  if (document.readyState === "complete") ajustar();
  else window.addEventListener("load", ajustar);
}})();
</script>
</body></html>"""
