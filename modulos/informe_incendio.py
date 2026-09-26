import html as html_lib
import json
import math
import os
from datetime import datetime, timedelta

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import INFORMES_DIR
from modulos.database import obtener_incendio_por_id
from modulos.utilidades import crear_carpetas


MAPA_COMBUSTIBLE = {
    'matorral': 1.25,
    'bosque': 1.4,
    'pastizal': 1.1,
    'pinar': 1.55,
    'maleza': 1.2,
    'humedal': 0.9,
    'roca': 0.7,
}


def _sanear_nombre(nombre):
    nombre_limpio = ''.join(ch if ch.isalnum() or ch in ('-', '_', ' ') else '_' for ch in nombre).strip()
    return nombre_limpio or 'incendio'


def _riesgo_incendio(incendio):
    viento = 18
    humedad = 35
    pendiente = 12
    vegetacion = 'matorral'

    if incendio is not None:
        viento = max(5, min(60, 18 + (incendio[7] * -0.02)))
        humedad = max(8, min(85, 35 + (1 if incendio[0] % 2 else -1) * 7))
        pendiente = max(3, min(45, 12 + abs(incendio[6]) * 0.7))
        vegetacion = 'matorral'

    riesgo = 0.35 + (viento / 60) + ((100 - humedad) / 100) + (pendiente / 60)

    if vegetacion in {'pinar', 'bosque'}:
        riesgo += 0.3
    elif vegetacion in {'matorral', 'maleza'}:
        riesgo += 0.2
    elif vegetacion == 'humedal':
        riesgo -= 0.1

    riesgo = max(0.25, min(9.9, riesgo))

    if riesgo >= 7.5:
        nivel = 'Crítico'
    elif riesgo >= 5.5:
        nivel = 'Alto'
    elif riesgo >= 3.5:
        nivel = 'Medio'
    elif riesgo >= 2.0:
        nivel = 'Bajo'
    else:
        nivel = 'Muy bajo'

    return round(riesgo, 2), nivel, {
        'viento': round(viento, 1),
        'humedad': round(humedad, 1),
        'pendiente': round(pendiente, 1),
        'vegetacion': vegetacion,
    }


def _obtener_hora_inicio_pronostico(incendio):
    inicio = datetime.strptime(f"{incendio[1]} {incendio[2]}", "%d/%m/%Y %H:%M")

    if inicio.hour >= 18:
        inicio_base = datetime(inicio.year, inicio.month, inicio.day) + timedelta(days=1)
        return inicio_base.replace(hour=0, minute=0)

    return datetime(inicio.year, inicio.month, inicio.day, 12, 0)


def _pronostico_24hs(incendio):
    inicio = _obtener_hora_inicio_pronostico(incendio)
    vegetacion = 'matorral'
    pendiente = 12
    base_temp = 28

    forecast = []
    for paso in range(0, 25, 3):
        hora = inicio + timedelta(hours=paso)
        ciclo = math.sin((hora.hour / 24) * 2 * math.pi)
        viento_kmh = round(10 + (pendiente * 0.8) + (MAPA_COMBUSTIBLE[vegetacion] * 8) + (ciclo * 10) + (paso / 7), 1)
        humedad = round(max(8, min(90, 62 - (hora.hour * 1.7) + (pendiente * 0.5) - MAPA_COMBUSTIBLE[vegetacion] * 7)), 1)
        temperatura = round(max(18, min(46, base_temp + (hora.hour * 0.7) + (pendiente / 4) + MAPA_COMBUSTIBLE[vegetacion] * 5)), 1)
        rachas = round(viento_kmh + 6 + abs(ciclo) * 10, 1)
        direccion = 135 - (paso * 2.0)
        if direccion < 0:
            direccion = 360 + direccion
        direccion = round(direccion, 0)
        indice_riesgo = round(max(0.5, min(9.9, 1.1 + (viento_kmh / 14) + ((100 - humedad) / 50) + (pendiente / 25) + MAPA_COMBUSTIBLE[vegetacion] * 0.8)), 2)
        severidad = 'Crítico' if indice_riesgo >= 7.5 else 'Alto' if indice_riesgo >= 5.5 else 'Medio' if indice_riesgo >= 3.5 else 'Bajo' if indice_riesgo >= 2 else 'Muy bajo'
        propagacion = round(max(40, min(2400, 120 + indice_riesgo * 110 + (pendiente * 18))), 0)
        estrategia = (
            'Mantener ataque directo en el flanco de viento y reforzar línea de seguridad.' if indice_riesgo >= 6 else
            'Flanqueo progresivo con refuerzo de agua y control del perímetro.' if indice_riesgo >= 4 else
            'Inspección de perímetro y consolidación con vigilancia activa.'
        )
        forecast.append({
            'hora': hora.strftime('%d/%m %H:%M'),
            'viento_kmh': viento_kmh,
            'humedad': humedad,
            'temperatura': temperatura,
            'rafagas': rachas,
            'direccion': direccion,
            'indice': indice_riesgo,
            'severidad': severidad,
            'propagacion_m': propagacion,
            'estrategia': estrategia,
        })

    return forecast


def _topografia_descripcion(pendiente):
    angulo = math.degrees(math.atan(pendiente / 100))
    if angulo > 20:
        return 'Ladera activa con pendiente superior a 20° y prioridad de control del flanco de viento.'
    if angulo > 10:
        return 'Pendiente moderada, con riesgo de aceleración del fuego en sectores de evacuación.'
    return 'Terreno predominantemente llano con propagación más controlada, pero requiere vigilancia del perímetro.'


def _analisis_horario(incendio):
    inicio = datetime.strptime(f"{incendio[1]} {incendio[2]}", "%d/%m/%Y %H:%M")
    hora = inicio.hour

    if 10 <= hora <= 16:
        return {
            'etapa': 'Horario diurno',
            'descripcion': (
                'En horario diurno, el viento suele reforzarse con el calentamiento y la pendiente favorece la propagación '
                'si el viento y la ladera están alineados. Es el período con mayor intensidad cuando el fuego avanza en la ' 
                'misma dirección del viento y la pendiente.'
            ),
            'prioridad': 'máxima'
        }

    if 18 <= hora <= 23 or 0 <= hora <= 5:
        return {
            'etapa': 'Horario nocturno',
            'descripcion': (
                'En la noche, el viento suele debilitarse por el enfriamiento; sin embargo, cuando el fuego desciende por la pendiente '
                'la violencia puede aumentar porque la combustión se intensifica en el flanco bajo y el avance es menos predecible.'
            ),
            'prioridad': 'alta'
        }

    return {
        'etapa': 'Horario de transición',
        'descripcion': (
            'En la transición térmica, la intensidad del fuego depende de la combinación exacta entre viento, pendiente y humedad; '
            'se debe vigilar el cambio de dirección del viento y cualquier aumento de velocidad en laderas.'
        ),
        'prioridad': 'media'
    }


def _estrategias_tacticas(forecast, condiciones):
    max_risk = max(forecast, key=lambda item: item['indice'])
    peak_hour = max_risk['hora']
    peak_index = max_risk['indice']

    estrategias = [
        'Priorizar cortafuegos y limpieza de combustible en el sector de avance del viento.',
        'Mantener dos líneas de defensa: una de ataque directo y una de contención en el flanco opuesto.',
        'Reforzar vigilancia y rutas de escape para personal bajo ráfagas superiores a 30 km/h.',
        'Definir puntos de agua y abastecimiento previo a la hora pico de riesgo.',
        'Ajustar el despliegue del helicóptero y medios aéreos en la hora de mayor intensidad.'
    ]

    if peak_index >= 6:
        estrategias.insert(0, 'Desactivar la operación de ataque frontal durante la ventana más crítica y reforzar el flanco bajo el viento.')
        estrategias.append('Asegurar la evacuación preventiva de personal en zonas de pendiente y combustibles secos.')
    elif peak_index >= 4:
        estrategias.insert(0, 'Realizar el avance de forma escalonada y con línea de protección en la cara de mayor pendiente.')
    else:
        estrategias.insert(0, 'Mantener vigilancia y control del perímetro con patrullaje constante.')

    return {
        'hora_pico': peak_hour,
        'riesgo_pico': peak_index,
        'recomendacion_general': 'Aplicar un esquema de ataque indirecto en el flanco de mayor intensidad, con despegue y control del perímetro en la franja de máxima pendiente y menor humedad.',
        'acciones': estrategias,
        'linea_defensa': 'Consolidar la zona de transición entre combustible denso y área de intervención, evitando avances en paralelo al viento.',
        'observaciones': (
            f'Con vegetación {condiciones["vegetacion"]}, pendiente {condiciones["pendiente"]}% y humedad {condiciones["humedad"]}%, '
            f'la mayor propagación se concentra en la ventana {peak_hour}.'
        )
    }


def _generar_html_dashboard(incendio, riesgo, nivel, condiciones, pronostico, estrategia, analisis_horario=None):
    nombre = incendio[3] or f'Incendio {incendio[0]}'
    provincia = incendio[4] or 'No informado'
    localidad = incendio[5] or 'No informado'
    descripcion = (incendio[8] or 'Sin descripción').replace('\n', '<br>')

    filas_pronostico = ''.join(
        f"<tr><td>{item['hora']}</td><td>{item['viento_kmh']} km/h</td><td>{item['rafagas']} km/h</td><td>{item['direccion']}°</td><td>{item['humedad']}%</td><td>{item['temperatura']}°C</td><td>{item['severidad']}</td></tr>"
        for item in pronostico
    )

    filas_acciones = ''.join(f'<li>{html_lib.escape(item)}</li>' for item in estrategia['acciones'])

    topografia_texto = _topografia_descripcion(condiciones['pendiente'])
    analisis_horario = analisis_horario or _analisis_horario(incendio)
    html_text = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8" />
      <title>Informe SIFO - {html_lib.escape(nombre)}</title>
      <style>
        body {{ font-family: Arial, sans-serif; background: #f4f6fb; margin: 0; padding: 32px; color: #16314d; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #0e4785, #d84545); color: white; padding: 28px 30px; border-radius: 18px; box-shadow: 0 10px 30px rgba(12,34,61,0.15); }}
        .header h1 {{ margin: 0; font-size: 32px; }}
        .header p {{ margin: 8px 0 0; opacity: 0.9; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 18px; margin-top: 24px; }}
        .card {{ background: white; border-radius: 16px; padding: 18px 20px; box-shadow: 0 8px 20px rgba(15,35,64,0.08); border-left: 7px solid #0e4785; }}
        .label {{ font-size: 11px; letter-spacing: 1px; text-transform: uppercase; color: #64748b; }}
        .value {{ font-size: 22px; font-weight: 700; margin-top: 8px; }}
        .risk {{ border-left-color: #d84545; }}
        .risk .value {{ color: #d84545; }}
        .section {{ background: white; border-radius: 16px; padding: 24px; margin-top: 24px; box-shadow: 0 8px 20px rgba(15,35,64,0.08); }}
        .section h2 {{ margin-top: 0; font-size: 22px; }}
        .table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        .table th, .table td {{ border-bottom: 1px solid #e8edf5; padding: 10px 12px; text-align: left; }}
        .table th {{ background: #edf4ff; color: #15304a; }}
        .badge {{ display: inline-block; padding: 8px 14px; border-radius: 999px; font-weight: 700; background: #ffe7e7; color: #a42525; }}
        .small {{ color: #5a6e86; font-size: 14px; }}
        ul {{ padding-left: 20px; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>SIFO - Informe operativo de incendio</h1>
          <p>{html_lib.escape(nombre)} · {html_lib.escape(provincia)} · {html_lib.escape(localidad)}</p>
        </div>

        <div class="grid">
          <div class="card"><div class="label">Fecha</div><div class="value">{html_lib.escape(incendio[1])}</div></div>
          <div class="card"><div class="label">Hora</div><div class="value">{html_lib.escape(incendio[2])}</div></div>
          <div class="card"><div class="label">Coordenadas</div><div class="value">{incendio[6]:.5f}, {incendio[7]:.5f}</div></div>
          <div class="card risk"><div class="label">Riesgo estimado</div><div class="value">{riesgo} / 10</div></div>
        </div>

        <div class="section">
          <h2>Resumen operativo</h2>
          <p><strong>Estado:</strong> {html_lib.escape(incendio[9])} &nbsp; <span class="badge">{nivel}</span></p>
          <p class="small">{descripcion}</p>
          <p class="small"><strong>Hora pico prevista:</strong> {html_lib.escape(estrategia['hora_pico'])} · <strong>Riesgo pico:</strong> {estrategia['riesgo_pico']}</p>
        </div>

        <div class="section">
          <h2>Condiciones ambientales</h2>
          <table class="table">
            <tr><th>Parámetro</th><th>Valor</th></tr>
            <tr><td>Viento</td><td>{condiciones['viento']} km/h</td></tr>
            <tr><td>Humedad relativa</td><td>{condiciones['humedad']}%</td></tr>
            <tr><td>Temperatura</td><td>{condiciones.get('temperatura', 'n/d')}°C</td></tr>
            <tr><td>Pendiente</td><td>{condiciones['pendiente']}%</td></tr>
            <tr><td>Vegetación dominante</td><td>{html_lib.escape(condiciones['vegetacion'])}</td></tr>
            <tr><td>Topografía</td><td>{html_lib.escape(topografia_texto)}</td></tr>
          </table>
          <p class="small"><strong>Patrón horario:</strong> {html_lib.escape(analisis_horario['etapa'])} · {html_lib.escape(analisis_horario['descripcion'])}</p>
        </div>

        <div class="section">
          <h2>Pronóstico meteorológico 24 hs (cada 3 hs)</h2>
          <table class="table">
            <tr><th>Hora</th><th>Viento</th><th>Rachas</th><th>Dirección</th><th>Humedad</th><th>Temperatura</th><th>Severidad</th></tr>
            {filas_pronostico}
          </table>
        </div>

        <div class="section">
          <h2>Estrategias y tácticas para bomberos</h2>
          <p><strong>Visión operativa:</strong> {html_lib.escape(estrategia['recomendacion_general'])}</p>
          <p><strong>Línea de defensa:</strong> {html_lib.escape(estrategia['linea_defensa'])}</p>
          <ul>{filas_acciones}</ul>
          <p class="small"><strong>Observación:</strong> {html_lib.escape(estrategia['observaciones'])}</p>
        </div>
      </div>
    </body>
    </html>
    '''
    return html_text


def _generar_pdf(incendio, riesgo, nivel, condiciones, pronostico, estrategia, pdf_path):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor('#0e4785'), leading=26)
    subtitle_style = ParagraphStyle('SubStyle', parent=styles['BodyText'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#4a5a6a'))
    body_style = ParagraphStyle('BodyStyle', parent=styles['BodyText'], fontName='Helvetica', fontSize=10, leading=14)
    section_style = ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=13, textColor=colors.HexColor('#0e4785'))

    topografia_texto = _topografia_descripcion(condiciones['pendiente'])
    elements = []
    elements.append(Paragraph('SIFO - Informe operativo de incendio', title_style))
    elements.append(Paragraph(f'{incendio[3] or "Incendio"} · {incendio[4] or "Provincia"} · {incendio[5] or "Localidad"}', subtitle_style))
    elements.append(Spacer(1, 10))

    info = [
        ['Campo', 'Valor'],
        ['Fecha', incendio[1]],
        ['Hora', incendio[2]],
        ['Coordenadas', f'{incendio[6]:.5f}, {incendio[7]:.5f}'],
        ['Estado', incendio[9]],
        ['Riesgo', f'{riesgo} / 10 ({nivel})'],
        ['Viento', f"{condiciones['viento']} km/h"],
        ['Humedad', f"{condiciones['humedad']}%"],
        ['Temperatura', f"{condiciones.get('temperatura', 'n/d')}°C"],
        ['Pendiente', f"{condiciones['pendiente']}%"],
        ['Vegetación', condiciones['vegetacion']],
        ['Topografía', topografia_texto],
    ]

    table = Table(info, colWidths=[60 * mm, 100 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0e4785')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dfeaf7')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7faff')]),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    analisis_horario = _analisis_horario(incendio)
    elements.append(Paragraph(f"Patrón horario: {analisis_horario['etapa']}", section_style))
    elements.append(Paragraph(analisis_horario['descripcion'], body_style))
    elements.append(Paragraph('Pronóstico meteorológico 24 hs (cada 3 hs)', section_style))
    forecast_rows = [['Hora', 'Viento', 'Rachas', 'Dir', 'Humedad', 'Temp', 'Severidad']]
    for item in pronostico:
        forecast_rows.append([
            item['hora'],
            f"{item['viento_kmh']} km/h",
            f"{item['rafagas']} km/h",
            f"{item['direccion']}°",
            f"{item['humedad']}%",
            f"{item['temperatura']}°C",
            item['severidad'],
        ])
    forecast_table = Table(forecast_rows, colWidths=[22 * mm, 18 * mm, 18 * mm, 16 * mm, 18 * mm, 18 * mm, 22 * mm])
    forecast_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf4ff')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dfeaf7')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7faff')]),
    ]))
    elements.append(forecast_table)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph('Estrategias y tácticas para bomberos', section_style))
    elements.append(Paragraph(f"Hora pico prevista: {estrategia['hora_pico']} · Riesgo pico: {estrategia['riesgo_pico']}", body_style))
    elements.append(Paragraph(estrategia['recomendacion_general'], body_style))
    for accion in estrategia['acciones']:
        elements.append(Paragraph(f'- {accion}', body_style))
    elements.append(Paragraph(f"Línea de defensa: {estrategia['linea_defensa']}", body_style))
    elements.append(Paragraph(f"Observación: {estrategia['observaciones']}", body_style))

    elements.append(PageBreak())
    elements.append(Paragraph('Resumen de simulación y riesgo', section_style))
    elements.append(Paragraph('Estimación del comportamiento del incendio según condiciones meteorológicas, topografía y combustible.', body_style))
    for item in pronostico:
        elements.append(Paragraph(f"{item['hora']} - Viento {item['viento_kmh']} km/h, hum. {item['humedad']}%, temp. {item['temperatura']}°C, severidad {item['severidad']} con propagación estimada {item['propagacion_m']} m.", body_style))

    drawing = Drawing(400, 140)
    chart = VerticalBarChart()
    chart.x = 40
    chart.y = 25
    chart.height = 85
    chart.width = 250
    chart.data = [[it['indice'] * 10 for it in pronostico]]
    chart.categoryAxis.categoryNames = [it['hora'] for it in pronostico]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.bars[0].fillColor = colors.HexColor('#ff7a59')
    drawing.add(chart)
    elements.append(drawing)

    doc = SimpleDocTemplate(pdf_path, pagesize=A4, title='Informe SIFO', author='SIFO', subject='Análisis de incendio')
    doc.build(elements)


def generar_informe_incendio(id_incendio):
    crear_carpetas()
    incendio = obtener_incendio_por_id(id_incendio)

    if incendio is None:
        print('Incendio inexistente.')
        return None

    riesgo, nivel, condiciones = _riesgo_incendio(incendio)
    condiciones['temperatura'] = 28
    pronostico = _pronostico_24hs(incendio)
    estrategia = _estrategias_tacticas(pronostico, condiciones)
    nombre = _sanear_nombre(incendio[3] or f'Incendio {incendio[0]}')

    html_path = os.path.join(INFORMES_DIR, f'{nombre}.html')
    pdf_path = os.path.join(INFORMES_DIR, f'{nombre}.pdf')

    analisis_horario = _analisis_horario(incendio)

    with open(html_path, 'w', encoding='utf-8') as archivo:
        archivo.write(_generar_html_dashboard(incendio, riesgo, nivel, condiciones, pronostico, estrategia, analisis_horario))

    _generar_pdf(incendio, riesgo, nivel, condiciones, pronostico, estrategia, pdf_path)

    print('===================================')
    print('Informe generado correctamente')
    print(f'HTML: {html_path}')
    print(f'PDF:  {pdf_path}')
    print('===================================')
    return {'html': html_path, 'pdf': pdf_path}
