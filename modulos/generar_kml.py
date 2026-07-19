import simplekml
import sqlite3
import os

DB = "datos/incendios.db"


def generar_kml(id_incendio):

    conexion = sqlite3.connect(DB)
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            nombre_incendio,
            latitud,
            longitud,
            descripcion
        FROM incendios
        WHERE id = ?
    """, (id_incendio,))

    dato = cursor.fetchone()

    conexion.close()

    if dato is None:
        print("Incendio inexistente.")
        return

    nombre = dato[0]
    latitud = dato[1]
    longitud = dato[2]
    descripcion = dato[3]

    kml = simplekml.Kml()

    pnt = kml.newpoint(
        name=nombre,
        coords=[(longitud, latitud)]
    )

    pnt.description = descripcion

    pnt.style.iconstyle.icon.href = \
        "http://maps.google.com/mapfiles/kml/shapes/firedept.png"

    if not os.path.exists("kml"):
        os.mkdir("kml")

    archivo = f"kml/{nombre}.kml"

    kml.save(archivo)

    print()
    print("====================================")
    print("KML generado correctamente")
    print(archivo)
    print("====================================")