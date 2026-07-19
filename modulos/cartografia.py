import osmnx as ox


def obtener_red_vial(latitud, longitud, radio=10000):

    grafo = ox.graph_from_point(

        (latitud, longitud),

        dist=radio,

        network_type="all"

    )

    nodos, aristas = ox.graph_to_gdfs(grafo)

    return aristas