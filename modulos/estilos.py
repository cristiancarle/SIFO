from config import ICONO_INCENDIO


def estilo_incendio():

    return {
        "id": "incendio",
        "icon_href": ICONO_INCENDIO,
        "icon_scale": "1.4"
    }


def estilo_ruta():

    return {
        "id": "ruta",
        "line_color": "ff0000ff",
        "line_width": "4"
    }


def estilo_camino():

    return {
        "id": "camino",
        "line_color": "ff00a5ff",
        "line_width": "2"
    }


def estilo_sendero():

    return {
        "id": "sendero",
        "line_color": "ff808080",
        "line_width": "1"
    }


def estilo_simulacion():

    return {
        "id": "simulacion",
        "line_color": "ff00ffff",
        "line_width": "2",
        "poly_color": "2800ccff"
    }


def estilo_viento():

    return {
        "id": "viento",
        "line_color": "ffff0000",
        "line_width": "5"
    }


def estilo_carrera_primaria():

    return {
        "id": "carrera_primaria",
        "line_color": "ff4444ff",
        "line_width": "4"
    }


def estilo_carrera_secundaria():

    return {
        "id": "carrera_secundaria",
        "line_color": "ffff6600",
        "line_width": "3"
    }


def estilos_heatmap():

    return [
        {
            "id": "heatmap_critico",
            "line_color": "ff0033ff",
            "line_width": "1.5",
            "poly_color": "d00000ff"
        },
        {
            "id": "heatmap_alto",
            "line_color": "ff0066ff",
            "line_width": "1.5",
            "poly_color": "a0146eff"
        },
        {
            "id": "heatmap_medio",
            "line_color": "ff00b4ff",
            "line_width": "1.5",
            "poly_color": "7828b4ff"
        },
        {
            "id": "heatmap_bajo",
            "line_color": "ff00ffff",
            "line_width": "1.5",
            "poly_color": "5040ffff"
        }
    ]