import simplekml


def estilo_incendio():

    estilo = simplekml.Style()

    estilo.iconstyle.icon.href = \
        "http://maps.google.com/mapfiles/kml/shapes/firedept.png"

    estilo.iconstyle.scale = 1.5

    return estilo


def estilo_ruta():

    estilo = simplekml.Style()

    estilo.linestyle.color = simplekml.Color.red

    estilo.linestyle.width = 4

    return estilo


def estilo_camino():

    estilo = simplekml.Style()

    estilo.linestyle.color = simplekml.Color.orange

    estilo.linestyle.width = 2

    return estilo


def estilo_sendero():

    estilo = simplekml.Style()

    estilo.linestyle.color = simplekml.Color.gray

    estilo.linestyle.width = 1

    return estilo