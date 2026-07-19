import osmnx as ox

from config import NETWORK_TYPE
from modulos.utilidades import escribir_log


def obtener_red_vial(latitud, longitud, radio):

    escribir_log("Descargando red vial...")

    grafo = ox.graph_from_point(

        (latitud, longitud),

        dist=radio,

        network_type=NETWORK_TYPE

    )

    escribir_log("Convirtiendo grafo...")

    _, aristas = ox.graph_to_gdfs(grafo)

    escribir_log(f"{len(aristas)} segmentos encontrados.")

    return aristas