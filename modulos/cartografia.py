from config import NETWORK_TYPE
from modulos.utilidades import escribir_log


def _import_osmnx():
    try:
        import osmnx as ox
        return ox
    except ImportError as exc:
        raise ImportError(
            "El módulo osmnx no está instalado. Instale `pip install osmnx` "
            "para usar la red vial y la generación de KML."
        ) from exc


def obtener_red_vial(latitud, longitud, radio):

    escribir_log("Descargando red vial desde OpenStreetMap...")

    try:
        ox = _import_osmnx()
    except ImportError as exc:
        escribir_log(str(exc))
        print(str(exc))
        return []

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

    if tipo in ["motorway", "trunk"]:
        return "ruta"

    if tipo == "primary":
        return "primaria"

    if tipo == "secondary":
        return "secundaria"

    if tipo in ["tertiary", "track", "service", "unclassified", "residential", "living_street", "road"]:
        return "camino"

    if tipo in ["path", "footway", "cycleway"]:
        return "sendero"

    return "otro"