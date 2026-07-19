from modulos.database import (
    crear_base_datos,
    registrar_incendio,
    listar_incendios,
    obtener_incendios
)

from modulos.generar_kml import generar_kml
from modulos.utilidades import crear_carpetas


# =====================================================
# MENÚ
# =====================================================

def mostrar_menu():

    print("\n" + "=" * 60)
    print("            S I F O")
    print("Sistema Inteligente para Incendios Forestales")
    print("=" * 60)
    print("1 - Registrar incendio")
    print("2 - Listar incendios")
    print("3 - Generar mapa KML")
    print("4 - Salir")
    print("=" * 60)


# =====================================================
# REGISTRAR
# =====================================================

def opcion_registrar():

    print("\nREGISTRO DE INCENDIO")
    print("-" * 40)

    fecha = input("Fecha (dd/mm/aaaa): ")
    hora = input("Hora (hh:mm): ")
    nombre = input("Nombre del incendio: ")
    provincia = input("Provincia: ")
    localidad = input("Localidad: ")

    try:
        latitud = float(input("Latitud: "))
        longitud = float(input("Longitud: "))
    except ValueError:
        print("\nLas coordenadas no son válidas.")
        return

    descripcion = input("Descripción: ")

    registrar_incendio(
        fecha,
        hora,
        nombre,
        provincia,
        localidad,
        latitud,
        longitud,
        descripcion
    )

    print("\n✅ Incendio registrado correctamente.")


# =====================================================
# LISTAR
# =====================================================

def opcion_listar():

    incendios = listar_incendios()

    if len(incendios) == 0:

        print("\nNo existen incendios registrados.")
        return

    print("\nLISTADO DE INCENDIOS")
    print("=" * 70)

    for incendio in incendios:

        print(f"ID: {incendio[0]}")
        print(f"Fecha: {incendio[1]}")
        print(f"Hora: {incendio[2]}")
        print(f"Nombre: {incendio[3]}")
        print(f"Provincia: {incendio[4]}")
        print(f"Localidad: {incendio[5]}")
        print(f"Latitud: {incendio[6]}")
        print(f"Longitud: {incendio[7]}")
        print(f"Descripción: {incendio[8]}")
        print(f"Estado: {incendio[9]}")
        print(f"Radio de análisis: {incendio[10]} m")
        print("-" * 70)


# =====================================================
# GENERAR KML
# =====================================================

def opcion_generar_kml():

    incendios = obtener_incendios()

    if len(incendios) == 0:

        print("\nNo existen incendios registrados.")
        return

    print("\nINCENDIOS DISPONIBLES")
    print("=" * 60)

    for incendio in incendios:

        print(
            f"{incendio[0]} - {incendio[1]} | "
            f"{incendio[2]} | {incendio[3]}"
        )

    try:

        id_incendio = int(
            input("\nSeleccione el ID del incendio: ")
        )

    except ValueError:

        print("ID inválido.")
        return

    generar_kml(id_incendio)


# =====================================================
# MAIN
# =====================================================

def main():

    crear_carpetas()

    crear_base_datos()

    while True:

        mostrar_menu()

        opcion = input("Seleccione una opción: ")

        if opcion == "1":

            opcion_registrar()

        elif opcion == "2":

            opcion_listar()

        elif opcion == "3":

            opcion_generar_kml()

        elif opcion == "4":

            print("\nGracias por utilizar SIFO.")
            break

        else:

            print("\nOpción incorrecta.")


# =====================================================
# INICIO
# =====================================================

if __name__ == "__main__":
    main()