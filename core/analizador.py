from modulos.database import obtener_incendio_por_id
from modulos.cartografia import obtener_red_vial
from providers.openmeteo import obtener_meteorologia
from config import RADIO_ANALISIS


def analizar_incendio(id_incendio):

    incendio = obtener_incendio_por_id(id_incendio)

    if incendio is None:
        return None

    datos = {
        "id": incendio[0],
        "fecha": incendio[1],
        "hora": incendio[2],
        "nombre": incendio[3],
        "provincia": incendio[4],
        "localidad": incendio[5],
        "latitud": incendio[6],
        "longitud": incendio[7],
        "descripcion": incendio[8]
    }

    print("Obteniendo meteorología...")

    meteo = obtener_meteorologia(
        datos["latitud"],
        datos["longitud"]
    )

    print("Descargando red vial...")

    caminos = obtener_red_vial(
        datos["latitud"],
        datos["longitud"],
        RADIO_ANALISIS
    )

    analisis = {

        "incendio": datos,

        "meteorologia": meteo,

        "red_vial": caminos

    }

    return analisis