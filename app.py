from modulos.database import (
    crear_base_datos,
    registrar_incendio,
    listar_incendios,
    obtener_incendios
)

from modulos.generar_kml import generar_kml


def mostrar_menu():
    print("\n" + "=" * 60)
    print("           S I F O")
    print("Sistema Inteligente para Incendios Forestales")
    print("=" * 60)
    print("1 - Registrar Incendio")
    print("2 - Listar Incendios")
    print("3 - Generar KML")
    print("4 - Salir")
    print("=" * 60)


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
        print("\nError: La latitud y longitud deben ser numéricas.")
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


def opcion_listar():

    incendios = listar_incendios()

    if len(incendios) == 0:
        print("\nNo existen incendios registrados.")
        return

    print("\nLISTADO DE INCENDIOS")
    print("=" * 60)

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
        print(f"Radio análisis: {incendio[10]} metros")
        print("-" * 60)


def opcion_generar_kml():

    incendios = obtener_incendios()

    if len(incendios) == 0:
        print("\nNo existen incendios registrados.")
        return

    print("\nINCENDIOS DISPONIBLES")
    print("=" * 60)

    for incendio in incendios:
        print(f"{incendio[0]} - {incendio[1]} ({incendio[2]})")

    print()

    try:
        id_incendio = int(input("Seleccione el ID del incendio: "))
    except ValueError:
        print("ID inválido.")
        return

    generar_kml(id_incendio)


def main():

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


if __name__ == "__main__":
    main()