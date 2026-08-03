def generar_informe(analisis):
    incendio = analisis["incendio"]
    meteo = analisis["meteorologia"]
    topografia = analisis["topografia"]
    combustible = analisis["combustible"]
    red_vial = analisis["red_vial"]

    lineas = []
    lineas.append("INFORME DE ANÁLISIS DE INCIDENTE")
    lineas.append("===============================")
    lineas.append(f"Nombre: {incendio['nombre']}")
    lineas.append(f"Fecha: {incendio['fecha']} {incendio['hora']}")
    lineas.append(f"Ubicación: {incendio['localidad']}, {incendio['provincia']}")
    lineas.append(f"Coordenadas: {incendio['latitud']}, {incendio['longitud']}")
    lineas.append("")

    lineas.append("Resumen meteorológico:")
    lineas.append(f"- Temperatura: {meteo.get('temperatura', 'N/A')} °C")
    lineas.append(f"- Humedad relativa: {meteo.get('humedad', 'N/A')} %")
    viento = meteo.get('viento')
    if viento is not None:
        lineas.append(
            f"- Viento: {viento} km/h, {meteo.get('categoria_viento', 'N/A')} "
            f"({meteo.get('direccion_cardinal', 'N/A')} {meteo.get('flecha_viento', '')})"
        )
    else:
        lineas.append("- Viento: N/A")
    lineas.append("")

    lineas.append("Resumen topográfico:")
    lineas.append(f"- Elevación aproximada: {topografia.get('elevacion', 'N/A')} m")
    lineas.append(
        f"- Tipo de terreno: {topografia.get('tipo_terreno', 'N/A')} "
        f"(pendiente máxima estimada: {topografia.get('maxima_pendiente_pct', 'N/A')}%)"
    )
    if topografia.get('pendiente_direccion_cardinal'):
        lineas.append(
            f"- Dirección de pendiente más fuerte: {topografia.get('pendiente_direccion_cardinal')} "
            f"({topografia.get('pendiente_direccion', 'N/A')}°)"
        )
    lineas.append("")

    lineas.append("Pronóstico en las próximas 24 horas:")
    lineas.append(f"- {analisis.get('pronostico_24h', 'No disponible')}")
    lineas.append("")

    lineas.append("Resumen de combustible:")
    lineas.append(f"- Tipo dominante: {combustible.get('tipo_combustible', 'N/A')}")
    lineas.append(f"- Descripción: {combustible.get('descripcion', 'N/A')}")
    lineas.append(f"- Elementos clasificados: {combustible.get('cantidad_elementos', 0)}")
    lineas.append("")

    lineas.append("Red vial detectada:")
    lineas.append(f"- Segmentos de vía descargados: {len(red_vial)}")
    tipos_vias = set()
    for item in red_vial:
        tipo = item.get('tipo')
        if isinstance(tipo, list):
            tipo = ",".join(tipo)
        if tipo:
            tipos_vias.add(tipo)

    if tipos_vias:
        lineas.append(f"- Tipos de vías presentes: {', '.join(sorted(tipos_vias))}")
    lineas.append("")

    lineas.append("Estrategias de trabajo sugeridas:")
    estrategias = []

    if meteo.get('categoria_viento') in ('Alto', 'Extremo') or (meteo.get('viento') or 0) >= 25:
        estrategias.append(
            "Priorizar el ataque defensivo desde la periferia y mantener líneas de contención externas debido a vientos fuertes."
        )
    else:
        estrategias.append(
            "Aprovechar condiciones de viento moderado para un ataque directo hacia el interior y estabilizar la línea de fuego."
        )

    if meteo.get('humedad') is not None and meteo['humedad'] < 30:
        estrategias.append(
            "La humedad es baja; el combustible está seco. Reduzca las operaciones en zona de riesgo y priorice cortafuegos y control de combustibles."
        )
    elif meteo.get('humedad') is not None and meteo['humedad'] < 50:
        estrategias.append(
            "La humedad es moderada. Mantenga vigilancia sobre chispas y puntos calientes, especialmente en áreas de vegetación densa."
        )
    else:
        estrategias.append(
            "La humedad es alta, lo que reduce la propagación rápida, pero siga controlando el combustible cercano al perímetro."
        )

    if combustible.get('tipo_combustible') in ('Bosque', 'Matorral'):
        estrategias.append(
            "La vegetación es densa o de matorral; utilice líneas de defensa mecanizadas y priorice la evacuación de áreas cercanas."
        )
    elif combustible.get('tipo_combustible') in ('Pastizal', 'Agrícola'):
        estrategias.append(
            "El combustible es ligero. Mantenga zonas limpias de material inflamable y use quemas de contención controladas cuando sea seguro."
        )
    else:
        estrategias.append(
            "No se identificó un combustible dominante claro. Combine observación de terreno con medidas de contención estándar."
        )

    if topografia.get('maxima_pendiente_pct') is not None and topografia['maxima_pendiente_pct'] > 15:
        estrategias.append(
            "El terreno es empinado. Evite operaciones de interior en pendientes pronunciadas y favorezca el trabajo desde la base y barreras naturales."
        )
    else:
        estrategias.append(
            "El terreno es relativamente accesible, por lo que el trabajo de campo puede apoyarse con rutas existentes."
        )

    if len(red_vial) > 0:
        estrategias.append(
            "Use la red vial disponible para establecer accesos y rutas de escape. Priorice caminos de mayor categoría para transporte de recursos."
        )
    else:
        estrategias.append(
            "No se detectaron vías cercanas; prepare rutas de acceso alternas y puntos de evacuación seguros."
        )

    for estrategia in estrategias:
        lineas.append(f"- {estrategia}")

    lineas.append("")
    lineas.append("Observaciones:")
    lineas.append("- Las recomendaciones se basan en datos públicos y deben ser validadas con inspección de campo.")
    lineas.append("- Priorice siempre la seguridad del personal y de la población cercana.")

    return "\n".join(lineas)
