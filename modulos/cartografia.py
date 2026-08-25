try:
    import osmnx as ox
except ImportError:
    ox = None

from config import NETWORK_TYPE
from modulos.utilidades import escribir_log


def obtener_red_vial(latitud, longitud, radio):

    if ox is None:
        escribir_log(
            "OSMnx no está instalado; la capa de red vial será omitida."
        )
        return []

    escribir_log("Descargando red vial desde OpenStreetMap...")

    grafo = ox.graph_from_point(
        (latitud, longitud),
        dist=radio,
        network_type=NETWORK_TYPE
    )

    escribir_log("Convirtiendo datos...")

    _, aristas = ox.graph_to_gdfs(grafo)

    caminos = []

    for _, fila in aristas.iterrows():

        if fila.geometry.geom_type != "LineString":
            continue

        highway = fila.get("highway", "desconocido")
        nombre = fila.get("name", "Sin nombre")

        coordenadas = []

        for x, y in fila.geometry.coords:
            coordenadas.append((x, y))

        caminos.append({
            "nombre": nombre,
            "tipo": highway,
            "coordenadas": coordenadas
        })

    escribir_log(f"{len(caminos)} caminos procesados.")

    return caminos

def clasificar_camino(tipo):

    if isinstance(tipo, list):
        tipo = tipo[0]

    if tipo in ["motorway", "trunk", "primary"]:
        return "ruta"

    if tipo in ["secondary", "tertiary"]:
        return "camino"

    if tipo in ["track", "service", "unclassified"]:
        return "rural"

    if tipo in ["path", "footway", "cycleway"]:
        return "sendero"

    return "otro"