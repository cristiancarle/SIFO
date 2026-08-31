from config import ICONO_INCENDIO


def _require_simplekml():
    try:
        import simplekml
        return simplekml
    except ImportError as exc:
        raise ImportError(
            "El paquete 'simplekml' no está instalado. Instale `pip install simplekml` "
            "para usar las funciones de estilo KML."
        ) from exc


def estilo_incendio():

    simplekml = _require_simplekml()
    s = simplekml.Style()

    s.iconstyle.icon.href = ICONO_INCENDIO
    s.iconstyle.scale = 1.4

    return s


def estilo_ruta():

    simplekml = _require_simplekml()
    s = simplekml.Style()

    s.linestyle.width = 4
    s.linestyle.color = simplekml.Color.red

    return s


def estilo_primaria():

    simplekml = _require_simplekml()
    s = simplekml.Style()

    s.linestyle.width = 4
    s.linestyle.color = simplekml.Color.blue

    return s


def estilo_secundaria():

    simplekml = _require_simplekml()
    s = simplekml.Style()

    s.linestyle.width = 3
    s.linestyle.color = simplekml.Color.yellow

    return s


def estilo_camino():

    simplekml = _require_simplekml()
    s = simplekml.Style()

    s.linestyle.width = 2
    s.linestyle.color = simplekml.Color.orange

    return s


def estilo_sendero():

    simplekml = _require_simplekml()
    s = simplekml.Style()

    s.linestyle.width = 1
    s.linestyle.color = simplekml.Color.gray

    return s


def estilo_viento():

    simplekml = _require_simplekml()
    s = simplekml.Style()

    s.linestyle.width = 4
    s.linestyle.color = simplekml.Color.blue

    return s


def estilo_carrera_primaria():

    simplekml = _require_simplekml()
    s = simplekml.Style()

    s.linestyle.width = 5
    s.linestyle.color = simplekml.Color.red

    return s


def estilo_carrera_secundaria():

    simplekml = _require_simplekml()
    s = simplekml.Style()

    s.linestyle.width = 3
    s.linestyle.color = simplekml.Color.orange

    return s


def estilo_progresion():

    simplekml = _require_simplekml()
    s = simplekml.Style()

    s.linestyle.width = 2
    s.linestyle.color = simplekml.Color.orange
    s.polystyle.color = simplekml.Color.changealphaint(120, simplekml.Color.orange)
    s.polystyle.fill = 1

    return s


def estilo_poligono_riesgo(nivel_riesgo='Moderado'):

    simplekml = _require_simplekml()
    s = simplekml.Style()

    mapa_colores = {
        'Bajo': simplekml.Color.green,
        'Moderado': simplekml.Color.yellow,
        'Alto': simplekml.Color.orange,
        'Extremo': simplekml.Color.red,
    }

    color_base = mapa_colores.get(nivel_riesgo, simplekml.Color.orange)
    s.linestyle.width = 2
    s.linestyle.color = simplekml.Color.black
    s.polystyle.color = simplekml.Color.changealphaint(110, color_base)
    s.polystyle.fill = 1

    return s
