import os
from datetime import datetime
from io import BytesIO

from config import LOG_DIR
from modulos.utilidades import escribir_log


def _generar_estrategia_periodo(meteo_periodo, topografia, combustible):
    estrategias = []

    temp = meteo_periodo.get("temperatura")
    humedad = meteo_periodo.get("humedad")
    viento = meteo_periodo.get("viento") or 0
    categoria_viento = meteo_periodo.get("categoria_viento", "")
    is_day = bool(meteo_periodo.get("is_day") in (1, True, "1", "true", "True"))

    if viento >= 40 or categoria_viento == "Extremo":
        estrategias.append("🚨 VIENTOS EXTREMOS: Mantener perímetro defensivo. Evaluar evacuación de personal.")
        estrategias.append("Operaciones limitadas a zonas periféricas seguras.")
    elif viento >= 25 or categoria_viento == "Alto":
        estrategias.append("⚠️ VIENTOS ALTOS: Ataque defensivo desde la periferia.")
        estrategias.append("Mantener líneas de contención externas reforzadas.")
    elif viento >= 10 or categoria_viento == "Moderado":
        estrategias.append("✓ Condiciones moderadas: Ataque hacia el interior es viable.")
        estrategias.append("Aprovechar para estabilizar frentes activos.")
    else:
        estrategias.append("✓ Vientos bajos: Operaciones de contención más seguras.")
        estrategias.append("Concentrar recursos en zonas de mayor combustible.")

    if humedad is not None:
        if humedad < 25:
            estrategias.append("🔥 HUMEDAD MUY BAJA: Combustible muy seco. MÁXIMA ALERTA.")
            estrategias.append("Posible aceleración rápida del fuego si la pendiente y el viento favorecen el avance.")
        elif humedad < 35:
            estrategias.append("🔴 Humedad baja: Propagación rápida. Acelerar cortafuegos.")
        elif humedad < 50:
            estrategias.append("🟡 Humedad moderada: Combustible parcialmente seco. Control gradual.")
        elif humedad < 65:
            estrategias.append("🟢 Humedad relativa acceptable: Propagación más lenta.")
        else:
            estrategias.append("🟢 Humedad alta: Condiciones favorables para contención.")

    if temp is not None and temp > 30:
        estrategias.append(f"🌡️ Temperatura alta ({temp}°C): Mayor velocidad de propagación esperada.")
    elif temp is not None and temp < 5:
        if is_day:
            estrategias.append(f"❄️ Temperatura baja ({temp}°C): La intensidad superficial cae, pero el riesgo sigue presente si el combustible está muy seco.")
        else:
            estrategias.append(f"❄️ Temperatura baja nocturna ({temp}°C): la propagación superficial puede reducirse, pero la pendiente y el combustible seco pueden mantener un avance peligroso hacia abajo por vientos nocturnos descendentes.")

    pendiente = topografia.get("maxima_pendiente_pct") or 0
    if pendiente > 20:
        if is_day:
            estrategias.append("⛰️ Terreno muy pendiente: El fuego se acelera en sentido ascendente por los vientos térmicos y el calor del sol.")
            estrategias.append("Proteger zonas altas prioritariamente.")
        else:
            estrategias.append("⛰️ Terreno muy pendiente: por la noche, los vientos fríos de ladera pueden empujar el frente hacia zonas más bajas con rapidez.")
            estrategias.append("Reforzar vigilancia en cotas inferiores y accesos de evacuación.")
    elif pendiente > 10:
        estrategias.append("Terreno con pendiente: Considerar comportamiento acelerado.")

    combustible_tipo = combustible.get("tipo_combustible", "Desconocido")
    if combustible_tipo == "Bosque":
        estrategias.append("🌲 Combustible tipo BOSQUE: Alta intensidad esperada. Máxima movilización.")
    elif combustible_tipo == "Matorral":
        estrategias.append("🌳 Combustible tipo MATORRAL: Propagación rápida. Líneas defensivas mecanizadas.")
    elif combustible_tipo in ("Pastizal", "Agrícola"):
        estrategias.append("🌾 Combustible ligero: Propagación muy rápida en sentido del viento.")
        estrategias.append("Prioridad: cortafuegos y quemas de contención.")

    return estrategias


def generar_informe_pdf(analisis, pronostico_24h):
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError:
        mensaje = "El paquete 'reportlab' no está instalado. Instale `pip install reportlab` para generar PDFs."
        escribir_log(mensaje)
        print(mensaje)
        return None

    incendio = analisis["incendio"]
    meteo = analisis["meteorologia"]
    topografia = analisis["topografia"]
    combustible = analisis["combustible"]
    fecha_confeccion = datetime.now().strftime("%d/%m/%Y %H:%M")

    os.makedirs(LOG_DIR, exist_ok=True)
    nombre_archivo = f"Informe_24h_{incendio['nombre']}.pdf"
    ruta_pdf = os.path.join(LOG_DIR, nombre_archivo)

    doc = SimpleDocTemplate(ruta_pdf, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []

    estilos = getSampleStyleSheet()
    titulo_estilo = ParagraphStyle(
        'TituloCustom',
        parent=estilos['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#CC0000'),
        spaceAfter=12,
        alignment=TA_CENTER
    )

    subtitulo_estilo = ParagraphStyle(
        'SubtituloCustom',
        parent=estilos['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        spaceAfter=8
    )

    story.append(Paragraph(f"INFORME DE ANÁLISIS - 24 HORAS", titulo_estilo))
    story.append(Paragraph(f"{incendio['nombre']} | {incendio['localidad']}, {incendio['provincia']}", estilos['Normal']))
    story.append(Paragraph(f"Fecha de confección: {fecha_confeccion}", estilos['Normal']))
    story.append(Paragraph(f"Coordenadas: {incendio['latitud']}, {incendio['longitud']}", estilos['Normal']))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("📊 TABLA DE METEOROLOGÍA - PRÓXIMAS 24 HORAS", subtitulo_estilo))

    datos_tabla = [[
        "Hora",
        "Temp (°C)",
        "Humedad (%)",
        "Viento (km/h)",
        "Dirección",
        "Categoría"
    ]]

    for dato in pronostico_24h:
        hora = dato.get("hora", "N/A")
        if isinstance(hora, str) and "T" in hora:
            hora = hora.split("T")[1][:5]

        temp = f"{dato.get('temperatura', 'N/A')}" if dato.get('temperatura') is not None else "N/A"
        humedad = f"{dato.get('humedad', 'N/A')}" if dato.get('humedad') is not None else "N/A"
        viento = f"{dato.get('viento', 'N/A')}" if dato.get('viento') is not None else "N/A"
        direccion = dato.get('direccion_cardinal', 'N/A')
        categoria = dato.get('categoria_viento', 'N/A')

        datos_tabla.append([hora, temp, humedad, viento, direccion, categoria])

    tabla = Table(datos_tabla, colWidths=[1*inch, 1*inch, 1.2*inch, 1.2*inch, 1*inch, 1*inch])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CC0000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f0f0')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
    ]))

    story.append(tabla)
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("🎯 ANÁLISIS Y ESTRATEGIAS DE ATAQUE - CADA 3 HORAS", subtitulo_estilo))

    for idx, dato in enumerate(pronostico_24h):
        hora = dato.get("hora", "N/A")
        if isinstance(hora, str) and "T" in hora:
            hora = hora.split("T")[1][:5]

        estrategias = _generar_estrategia_periodo(dato, topografia, combustible)

        story.append(Paragraph(f"⏰ {hora} - Próximas 3 horas", estilos['Heading3']))

        for estrategia in estrategias:
            story.append(Paragraph(f"• {estrategia}", estilos['Normal']))

        story.append(Spacer(1, 0.1*inch))

        if (idx + 1) % 4 == 0 and idx < len(pronostico_24h) - 1:
            story.append(PageBreak())

    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("📋 OBSERVACIONES FINALES", subtitulo_estilo))
    story.append(Paragraph(
        "Las recomendaciones se basan en datos de meteorología en tiempo real y análisis de topografía y combustible. "
        "Deben ser validadas constantemente en campo y ajustadas según el comportamiento real del incendio.",
        estilos['Normal']
    ))
    story.append(Paragraph(
        "Priorice siempre la seguridad del personal y la población cercana.",
        estilos['Normal']
    ))

    doc.build(story)

    escribir_log(f"Informe PDF generado: {ruta_pdf}")
    print(f"\n✅ Informe PDF generado: {ruta_pdf}")

    return ruta_pdf
