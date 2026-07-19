import simplekml
from config import ICONO_INCENDIO


def estilo_incendio():

    s = simplekml.Style()

    s.iconstyle.icon.href = ICONO_INCENDIO
    s.iconstyle.scale = 1.4

    return s


def estilo_ruta():

    s = simplekml.Style()

    s.linestyle.width = 4
    s.linestyle.color = simplekml.Color.red

    return s


def estilo_camino():

    s = simplekml.Style()

    s.linestyle.width = 2
    s.linestyle.color = simplekml.Color.orange

    return s


def estilo_sendero():

    s = simplekml.Style()

    s.linestyle.width = 1
    s.linestyle.color = simplekml.Color.gray

    return s